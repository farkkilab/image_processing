
"""
=====================================================
 End-to-End Filter Image Script and Quantification Tool
=====================================================
Run with quantification
This script performs two main steps:

1. **Filtering (White Tophat)**: Enhances small bright structures by removing smooth background.Runs per marker/channel using a user-supplied JSON dictionary.
2. **Quantification**:  Computes per-cell mean intensities (and shape features) for each marker. Uses pre-computed cell masks.

-----------------------------------------------------
 Input / Output Structure
-----------------------------------------------------

Raw images:
    <tif_dir>/*.tif or *.tiff
    (multi-channel TIFFs; use 'key' = channel index, 0-based)

Filtered images (produced here):
    <tif_dir>/<MARKER>/<SLIDE>.ome_<MARKER>_tophat.tif
    Raw images will NOT be modified, instead they will be separately stored

Masks:
    <mask_dir>/<SLIDE>.tif or <SLIDE>.tiff
    (integer-labeled masks, one cell per label)

Outputs (quantification):
    <output_dir>/<SLIDE>.csv
    (merged intensities across all markers for each cell)

-----------------------------------------------------
 Parameters
-----------------------------------------------------
- `markers`: JSON string mapping marker names to channel indices.
   Example: '{"Ki67":7,"DNA1":1,"CD3":4}'
- `size`:    Disk radius (px) for white tophat. Default = 10.
- `workers`: Number of parallel jobs for filtering. Default = 0 (sequential).

-----------------------------------------------------
 Usage Examples
-----------------------------------------------------

# Run full pipeline (filter all markers, then quantify)
# - Step 1: Apply white tophat filtering to all raw TIFFs
# - Step 2: Quantify per-cell mean intensities using masks
# - Output: One CSV per slide in /path/to/csv_out
python filter_image_script.py pipeline \
    --tif_dir /path/to/raw_tifs \
    --markers '{"Ki67":7,"DNA1":1,"CD3":4}' \
    --size 10 --workers 8 \
    --mask_dir /path/to/masks \
    --output_dir /path/to/csv_out

# Filter all markers only
# - Saves filtered TIFFs into subfolders /path/to/raw_tifs/<MARKER>/
python filter_image_script.py filter \
    --tif_dir /path/to/raw_tifs \
    --markers '{"Ki67":7,"DNA1":1,"CD3":4}' \
    --size 10 --workers 8

# Quantify only (skip filtering; assumes filtered images already exist)
# - Exports one CSV per slide into /path/to/csv_out
python filter_image_script.py quantify \
    --tif_dir /path/to/raw_tifs \
    --mask_dir /path/to/masks \
    --output_dir /path/to/csv_out
"""

import os
import re
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import tifffile
from skimage.io import imread, imsave
from skimage.morphology import white_tophat, disk
from skimage.measure import regionprops


# -----------------------------
# Filtering (white tophat)
# -----------------------------

def process_image(filename: str,
                  base_path: str,
                  output_folder: str,
                  marker_name: str,
                  key: int,
                  size: int = 10) -> str:
    """
    Process a single TIFF image by applying white tophat filtering.
    """
    try:
        if not filename.lower().endswith((".tif", ".tiff")):
            return f"SKIP: {filename} (not TIFF)"

        input_path = os.path.join(base_path, filename)
        try:
            image = imread(input_path, key=key)
        except Exception as e:
            return f"❌ {filename} - imread failed: {e}"

        selem = disk(size)
        filtered = white_tophat(image, selem)

        # Output naming compatible with quantifier regex:
        # <SLIDE>.ome_<MARKER>_tophat.tif
        base, _ext = os.path.splitext(os.path.basename(filename))
        new_filename = f"{base}.ome_{marker_name}_tophat.tif"
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, new_filename)

        imsave(output_path, filtered.astype(np.uint16))
        return f"✅ {filename} -> {output_path}"
    except Exception as e:
        return f"❌ {filename} crashed: {e}"


def run_filter_for_marker(tif_dir: str, marker: str, key: int, size: int, workers: int = 0) -> None:
    """
    Run white tophat filtering over all TIFFs in `tif_dir` for one marker/channel.
    Outputs to: <tif_dir>/<MARKER>/<SLIDE>.ome_<MARKER>_tophat.tif
    """
    input_dir = Path(tif_dir)
    output_dir = input_dir / marker
    files = [f for f in os.listdir(input_dir) if f.lower().endswith((".tif", ".tiff"))]

    if not files:
        print(f"[filter:{marker}] No TIFF files found to process.")
        return

    print(f"[filter:{marker}] key={key} size={size}  n_files={len(files)}")
    if workers and workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [
                ex.submit(process_image, f, str(input_dir), str(output_dir), marker, key, size)
                for f in files
            ]
            for fut in as_completed(futures):
                print(fut.result())
    else:
        for f in files:
            msg = process_image(f, str(input_dir), str(output_dir), marker, key, size)
            print(msg)


def run_filter_all(tif_dir: str, markers: Dict[str, int], size: int, workers: int) -> None:
    """
    Filter ALL markers in the provided dictionary.
    """
    for marker, key in markers.items():
        run_filter_for_marker(tif_dir, marker, int(key), size, workers)


# -----------------------------
# Quantification
# -----------------------------

def extract_slide_and_marker(filename: str) -> Tuple[str, str]:
    """
    Parse filenames like <SLIDE>.ome_<MARKER>_tophat.tif
    Returns (SLIDE, MARKER) or (None, None) if no match.
    """
    match = re.match(r"(.+?)\.ome_(.+?)_tophat\.tif$", filename)
    if match:
        return match.group(1), match.group(2)
    return None, None


def load_all_marker_images(base_dir: str) -> Dict[str, Dict[str, str]]:
    """
    Scan per-marker subfolders under base_dir and build:
        { SLIDENAME: { MARKER: image_path } }
    """
    marker_data: Dict[str, Dict[str, str]] = {}

    for marker_folder in os.listdir(base_dir):
        marker_path = os.path.join(base_dir, marker_folder)
        if not os.path.isdir(marker_path):
            continue

        for fname in os.listdir(marker_path):
            if fname.endswith(".tif") and ".ome_" in fname and "_tophat.tif" in fname:
                slide, marker = extract_slide_and_marker(fname)
                if slide and marker:
                    marker_data.setdefault(slide, {})[marker] = os.path.join(marker_path, fname)
    return marker_data


def quantify_slide(slide_name: str,
                   marker_image_paths: Dict[str, str],
                   mask_path: str) -> pd.DataFrame:
    """
    Compute per-cell mean intensity for each marker, using a labeled cell mask.
    """
    print(f"Quantifying {slide_name}...")
    mask = tifffile.imread(mask_path)

    all_data = None
    for i, (marker, img_path) in enumerate(marker_image_paths.items()):
        img = tifffile.imread(img_path)
        props = regionprops(mask, intensity_image=img)

        records = []
        for p in props:
            rec = {
                'CellID': p.label,
                marker: float(p.mean_intensity)
            }
            if i == 0:
                rec.update({
                    'Y_centroid': float(p.centroid[0]),
                    'X_centroid': float(p.centroid[1]),
                    'Area': int(p.area),
                    'Eccentricity': float(p.eccentricity)
                })
            records.append(rec)

        df = pd.DataFrame(records)

        if i == 0:
            all_data = df
        else:
            all_data = pd.merge(all_data, df[['CellID', marker]], on='CellID', how='left')

    return all_data


def run_quantify(tif_base: str, mask_dir: str, output_dir: str) -> None:
    """
    Quantify all slides present under `tif_base` (expects per-marker subfolders).
    """
    os.makedirs(output_dir, exist_ok=True)
    marker_map = load_all_marker_images(tif_base)

    if not marker_map:
        print("No corrected marker images found. Expected: <tif_base>/<MARKER>/<SLIDE>.ome_<MARKER>_tophat.tif")
        return

    for slide, marker_imgs in marker_map.items():
        mask_file_tif = os.path.join(mask_dir, f"{slide}.tif")
        mask_file_tiff = os.path.join(mask_dir, f"{slide}.tiff")
        mask_file = mask_file_tif if os.path.exists(mask_file_tif) else mask_file_tiff

        if not os.path.exists(mask_file):
            print(f"Mask not found for {slide}, skipping.")
            continue

        result_df = quantify_slide(slide, marker_imgs, mask_file)
        out_csv = os.path.join(output_dir, f"{slide}.csv")
        result_df.to_csv(out_csv, index=False)
        print(f"Saved: {out_csv}")


# -----------------------------
# CLI
# -----------------------------

def parse_markers_arg(markers_arg: str) -> Dict[str, int]:
    """
    Parse markers mapping from JSON only.
    Example: '{"Ki67":7,"DNA1":1}'
    """
    try:
        markers = json.loads(markers_arg)
        return {k: int(v) for k, v in markers.items()}
    except Exception as e:
        raise ValueError(f"Invalid markers JSON: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Filter all markers (JSON dict) then quantify."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # filter-all
    p_filter = sub.add_parser("filter", help="Filter ALL markers from a JSON dict")
    p_filter.add_argument("--tif_dir", required=True, help="Folder with raw TIFFs")
    p_filter.add_argument("--markers", required=True,
                          help='Marker→channel dict in JSON, e.g. \'{"Ki67":7,"DNA1":1}\'')
    p_filter.add_argument("--size", type=int, default=10, help="Disk radius (px) for white tophat")
    p_filter.add_argument("--workers", type=int, default=0, help="Parallel workers (0/1 = sequential)")

    # quantify-only
    p_quant = sub.add_parser("quantify", help="Quantify per-cell intensities from corrected TIFFs")
    p_quant.add_argument("--tif_dir", required=True, help="Base folder containing per-marker subfolders")
    p_quant.add_argument("--mask_dir", required=True, help="Folder with per-slide label masks (SLIDE.tif/.tiff)")
    p_quant.add_argument("--output_dir", required=True, help="Where to save CSV results")

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="Run filter (all markers) then quantify")
    p_pipe.add_argument("--tif_dir", required=True, help="Folder with raw TIFFs (input for filtering)")
    p_pipe.add_argument("--markers", required=True,
                        help='Marker→channel dict in JSON, e.g. \'{"Ki67":7,"DNA1":1}\'')
    p_pipe.add_argument("--size", type=int, default=10, help="Disk radius (px) for white tophat")
    p_pipe.add_argument("--workers", type=int, default=0, help="Parallel workers (0/1 = sequential)")
    p_pipe.add_argument("--mask_dir", required=True, help="Folder with per-slide label masks (SLIDE.tif/.tiff)")
    p_pipe.add_argument("--output_dir", required=True, help="Where to save CSV results")

    args = parser.parse_args()

    if args.cmd == "filter":
        markers = parse_markers_arg(args.markers)
        run_filter_all(args.tif_dir, markers, args.size, args.workers)

    elif args.cmd == "quantify":
        run_quantify(args.tif_dir, args.mask_dir, args.output_dir)

    elif args.cmd == "pipeline":
        markers = parse_markers_arg(args.markers)
        run_filter_all(args.tif_dir, markers, args.size, args.workers)
        run_quantify(args.tif_dir, args.mask_dir, args.output_dir)


if __name__ == "__main__":
    main()
