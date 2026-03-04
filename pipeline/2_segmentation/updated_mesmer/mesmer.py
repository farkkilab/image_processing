import os
import tifffile
import zarr
import numpy as np
import cv2
import gc
import time
import subprocess
import shutil
import tensorflow as tf
from pathlib import Path
from dask.diagnostics import ProgressBar
from tqdm import tqdm

# DeepCell & DeepTile Imports
from deepcell.applications import Mesmer
from deeptile import load, lift
from deeptile.extensions import stitch

# --- 1. Environment & Setup ---
os.environ.update({"DEEPCELL_ACCESS_TOKEN": "YOURTOKEN"})

# Configure GPU growth to prevent memory errors
physical_devices = tf.config.experimental.list_physical_devices('GPU')
for device in physical_devices:
    tf.config.experimental.set_memory_growth(device, True)

def run_ome_conversion(input_tif, final_ome_tif):
    """Calls external OME tools to create a QuPath-optimized pyramid."""
    temp_zarr = str(Path(input_tif).with_suffix('')) + "_zarr_temp"
    
    try:
        print(f"--- Generating Pyramid (Zarr) ---")
        subprocess.run([
            "bioformats2raw",
            "--resolutions", "5",
            "--downsample-type", "SIMPLE", 
            "--compression", "zlib",
            "--series", "0",
            "--tile_width", "512",
            "--tile_height", "512",
            "--overwrite",
            input_tif,
            temp_zarr
        ], check=True)

        print(f"--- Transcoding to OME-TIFF ---")
        subprocess.run([
            "raw2ometiff",
            "--compression", "zlib",
            temp_zarr,
            final_ome_tif
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
        raise
    finally:
        # Cleanup temp Zarr if it exists
        if os.path.exists(temp_zarr):
            shutil.rmtree(temp_zarr)
        # Only delete the flat temp TIFF if the final file exists
        if os.path.exists(final_ome_tif) and os.path.exists(input_tif):
            os.remove(input_tif)

# --- 2. Helper Functions ---

def apply_preprocessing(image, gamma=1.5, sigma=1.0, strength=1.5):
    """Gamma correction and unsharp mask to boost nuclear signal."""
    # Normalize to 0-1
    img_float = (image - image.min()) / (image.max() - image.min())
    # Gamma
    gamma_corr = np.power(img_float, 1/gamma)
    # Convert back to uint16
    img_u16 = (gamma_corr * 65535).astype(np.uint16)
    # Unsharp Mask
    blurred = cv2.GaussianBlur(img_u16.astype(np.float32), (0, 0), sigma)
    sharpened = cv2.addWeighted(img_u16.astype(np.float32), 1 + strength, blurred, -strength, 0)
    return np.clip(sharpened, 0, 65535).astype(np.uint16)

class TileProcessor:
    """Stateful processor to handle Mesmer inference and tqdm updates."""
    def __init__(self, app, total_tiles, mpp):
        self.app, self.mpp, self.pbar = app, mpp, tqdm(total=total_tiles, desc="Tiles")
    
    def process(self, tile):
        tile_arr = np.array(tile)
        h, w = tile_arr.shape
        
        # Pad to multiple of 256 (Mesmer's native window)
        new_h = int(np.ceil(h / 256) * 256)
        new_w = int(np.ceil(w / 256) * 256)
        
        if new_h != h or new_w != w:
            tile_arr = np.pad(tile_arr, ((0, new_h - h), (0, new_w - w)), mode='constant')

        if np.mean(tile_arr) < 600: # TODO: Change filtering of background tiles
            res = np.zeros(tile_arr.shape, dtype=np.uint32)
        else:
            input_data = np.stack([tile_arr, tile_arr], axis=-1).astype(np.float32) / 65535.0
            preds = self.app.predict(input_data[None, ...], image_mpp=self.mpp, compartment='nuclear')
            res = preds[0, ..., 0].astype(np.uint32)
        
        self.pbar.update(1)
        
        # Crop back to original tile size
        return res[:h, :w]

# --- 3. Main Loop ---

def main():
    input_dir, output_dir = '/notebooks/tif/', '/notebooks/seg/'
    image_mpp = 0.325 # TODO: Set your actual resolution here
    os.makedirs(output_dir, exist_ok=True)
    
    print("Loading Mesmer...")
    app = Mesmer()

    for fname in [f for f in os.listdir(input_dir) if f.endswith(".tif")]:
        start_time = time.time()
        img_path = os.path.join(input_dir, fname)
        
        # Load Raw Channel (handles multi-channel or 2D)
        with tifffile.TiffFile(img_path) as tif:
            data = zarr.open(tif.aszarr(), mode='r')
            raw = data[0] if isinstance(data, zarr.Group) else data
            # Logic for channel extraction (assumes channel 0 is nuclear)
            nuc = raw[0, :, :] if raw.ndim == 3 else raw[:]

        print(f"Processing {fname} ({nuc.shape})")
        proc = apply_preprocessing(nuc)

        # Setup DeepTile
        dt = load(proc)
        tiled = dt.get_tiles(tile_size=(1024, 1024), overlap=(0.1, 0.1))
        
        # Inference
        proc_obj = TileProcessor(app, len(tiled.flat), image_mpp)
        @lift
        def run_mesmer(tile): return proc_obj.process(tile)
        
        masks = run_mesmer(tiled)
        proc_obj.pbar.close()

        # Stitch and Save
        print("Stitching...")
        final_mask = np.array(stitch.stitch_masks(masks)).astype(np.uint32) 

        # Verify the type in your logs
        print(f"Final Mask Data Type: {final_mask.dtype}")
        
        # Save Pipeline
        # Strip all extensions to get a clean ID
        image_id = fname.split('.')[0] 
        temp_path = Path(output_dir) / f"{image_id}_flat.tif"
        final_path = Path(output_dir) / f"{image_id}.ome.tif"

        # Save tiled flat TIFF
        tifffile.imwrite(
            str(temp_path), 
            final_mask, 
            tile=(512, 512), 
            compression='deflate',
            metadata={
                'PhysicalSizeX': image_mpp, 
                'PhysicalSizeY': image_mpp, 
                'PhysicalSizeXUnit': 'µm',
                'PhysicalSizeYUnit': 'µm',
                # Define axes explicitly to avoid confusion
                'axes': 'YX',
                # Name the channel
                'Channel': {
                    'Name': 'Nuclei Labels',
                    # This is a signed 32-bit int: (Alpha=255, R=0, G=255, B=255)
                    'Color': -16711681 
                }
            }
        )

        # Convert to OME-TIFF Pyramid
        run_ome_conversion(str(temp_path), str(final_path))
        
        print(f"✅ Saved to {final_path} in {(time.time()-start_time)/60:.1f}m")
        gc.collect()

if __name__ == "__main__":
    main()