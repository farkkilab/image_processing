# Instructions to run this script when processing multiple images in one folder:
# conda env create -n ashlar -f ashlar.yml # only when no environment installed
# conda activate ashlar
# python ashlar_workflow.py -c 42

# If you find bugs, contact Ziqi <ziqi.kang@helsinki.fi>. :]
# This script is based on Ada's script <ada.junquera-mencia@helsinki.fi>. 

import os
import argparse
import multiprocessing
from re import search
from os import listdir
import re

my_path = "./raw/Batch_D"
output_path = "./registration/Batch_D"
subfolders = [f.path for f in os.scandir(my_path) if f.is_dir()]
file_type = 'rcpnl'  # 'nd2' 'rcpnl'

illumination = 'Y'  # 'N'
illumination_folder = "./illumination/Batch_D/"

# Helper function for natural alphanumeric sorting
def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', filename)]

def ashlar_call(files_to_stitch, output_path2, flat_field_file=None, dark_field_file=None):
    cmd = f"ashlar {files_to_stitch} -o \"{output_path2}\" --pyramid --filter-sigma 1 -m 30"
    if flat_field_file and dark_field_file:
        cmd += f" --ffp {flat_field_file} --dfp {dark_field_file}"
    print(cmd)
    os.system(cmd)

# (1) Updated function to get and sort files by alphanumeric order
def get_file_list(folder):
    files = [f for f in listdir(folder) if search(file_type, f)]
    sorted_files = sorted(files, key=natural_sort_key)
    files_to_stitch = " ".join([os.path.join(folder, file) for file in sorted_files])
    print("Files to stitch:", files_to_stitch)
    return files_to_stitch

# (2) Unified function to get files to stitch and illumination files if needed
def get_all_file_list(folder, illu_folder=None):
    files_to_stitch = get_file_list(folder)
    
    # Only get illumination files if an illumination folder is provided
    if illu_folder:
        illu_files = sorted([f for f in listdir(illu_folder)], key=natural_sort_key)
        flat_field = " ".join([os.path.join(illu_folder, f) for f in illu_files if "-ffp" in f])
        dark_field = " ".join([os.path.join(illu_folder, f) for f in illu_files if "-dfp" in f])
        print("Flat field files:", flat_field)
        print("Dark field files:", dark_field)
        return files_to_stitch, flat_field, dark_field
    else:
        return files_to_stitch, None, None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', '-c', type=int)
    args = parser.parse_args()
    print("Subfolders are:", subfolders)

    num_process = args.threads
    pool = multiprocessing.Pool(processes=num_process)

    tasks = []
    for subfolder in subfolders:
        # Get the files to stitch and illumination files (if needed)
        illumination_folder_path = os.path.join(illumination_folder, subfolder.split(os.sep)[-1]) if illumination == "Y" else None
        files_to_stitch, flat_field, dark_field = get_all_file_list(subfolder, illumination_folder_path)
        
        # Prepare arguments based on the presence of illumination correction files
        output_file_path = os.path.join(output_path, subfolder.split(os.sep)[-1] + ".ome.tif")
        if illumination == "Y" and flat_field and dark_field:
            tasks.append((files_to_stitch, output_file_path, flat_field, dark_field))
        else:
            tasks.append((files_to_stitch, output_file_path))

    # Execute the tasks in parallel
    if illumination == "Y":
        pool.starmap(lambda f, o, ff, df: ashlar_call(f, o, ff, df), tasks)
    else:
        pool.starmap(lambda f, o: ashlar_call(f, o), tasks)
    
    pool.close()
    pool.join()