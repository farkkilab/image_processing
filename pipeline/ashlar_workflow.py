# Instructions to run this script when processing multiple images in one folder:
# conda env create -n ashlar -f ashlar.yml
# conda activate ashlar
# python ashlar_workflow.py -c 42

# If you find bugs, contact Ziqi <ziqi.kang@helsinki.fi>. :]
# This script is based on Ada's script <ada.junquera-mencia@helsinki.fi>. 

import os
import argparse
import multiprocessing
from re import search
from os import listdir
from os.path import isfile, join

my_path = "D://Ada//ada_cell_cycle//batch_3_val"
output_path = "D://Ada//ada_cell_cycle//batch_3_val"
subfolders = [ f.path for f in os.scandir(my_path) if f.is_dir() ]
file_type = 'rcpnl' # or 'nd2'
    
def ashlar_call(files_to_stitch, output_path2):
    cmd= "ashlar {} -o\"{}\" --pyramid --filter-sigma 1 -m 30".format(files_to_stitch, output_path2)
    print(cmd)
    os.system(cmd)

def get_file_list(folder): 
    files = [f for f in listdir(folder) if search(file_type, f)]
    files_to_stitch=" "
    for file in files:
        files_to_stitch = files_to_stitch + folder + os.sep + file + " "
        # files_to_stitch = files_to_stitch.rstrip()
    return(files_to_stitch)

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads','-c',type=int)
    args = parser.parse_args()

    print(subfolders)

    # Number of processes to run in parallel
    num_process = args.threads
    # Create a multiprocessing Pool
    pool = multiprocessing.Pool(processes=num_process)

    # Use the Pool.starmap function to distribute the work among processes
    pool.starmap(ashlar_call, 
                 [(get_file_list(subfolder), 
                   os.path.join(output_path, subfolder.split(os.sep)[-1] + ".ome.tiff")) for subfolder in subfolders]) # FIXME
    
    # Close the Pool to free up resources
    pool.close()
    pool.join()







