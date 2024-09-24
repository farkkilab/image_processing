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


my_path = "./raw/Batch_D"
output_path = "./registration/Batch_D"
subfolders = [ f.path for f in os.scandir(my_path) if f.is_dir() ]
file_type = 'rcpnl' # 'nd2' 'rcpnl'

illumination = 'Y' # 'N'
illumination_folder = "./illumination/Batch_D/"


def ashlar_call(files_to_stitch, output_path2):
    cmd= "ashlar {} -o\"{}\" --pyramid --filter-sigma 1 -m 30".format(files_to_stitch, output_path2)
    print(cmd)
    # os.system(cmd)

def ashlar_call_illumination(files_to_stitch, output_path2, flat_field_file, dark_field_file):
    cmd= "ashlar {} -o\"{}\" --pyramid --filter-sigma 1 -m 30 --ffp {} --dfp {}".format(files_to_stitch, output_path2, flat_field_file, dark_field_file)
    print(cmd)
    # os.system(cmd)

def get_file_list(folder): 
    files = [f for f in listdir(folder) if search(file_type, f)]
    files_to_stitch=" "
    for file in files:
        files_to_stitch = files_to_stitch + folder + os.sep + file + " "
    print(files_to_stitch)
    return(files_to_stitch)

def get_all_file_list(folder, illu_folder): 
    files = [f for f in listdir(folder) if search(file_type, f)]
    files_to_stitch=" "
    for file in files:
        files_to_stitch = files_to_stitch + folder + os.sep + file + " "
    
    illu_files = [f for f in listdir(illu_folder)]
    flat_field = " "
    dark_field = " "
    for illu_file in illu_files: 
        if "-ffp" in illu_file:
            flat_field = flat_field + illu_folder + os.sep + illu_file + " "
        elif "-dfp" in illu_file:
            dark_field = dark_field + illu_folder + os.sep + illu_file + " "
    
    print("Files to stitch:", files_to_stitch)
    print("Flat field files:", flat_field)
    print("Dark field files:", dark_field)
    return(files_to_stitch, flat_field, dark_field)


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads','-c',type=int)
    args = parser.parse_args()
    print("Subfolders are:", subfolders)

    if illumination=="Y": 
        for subfolder in subfolders:  
            files_to_stitch, flat_field, dark_field = get_all_file_list(subfolder, 
                                                                                  os.path.join(illumination_folder, 
                                                                                               subfolder.split(os.sep)[-1]))
            ashlar_call_illumination(files_to_stitch, 
                                     os.path.join(output_path, subfolder.split(os.sep)[-1] + ".ome.tiff"), 
                                     flat_field,
                                     dark_field)
    else:
        num_process = args.threads
        pool = multiprocessing.Pool(processes=num_process)
        pool.starmap(ashlar_call, 
                    [(get_file_list(subfolder), 
                    os.path.join(output_path, subfolder.split(os.sep)[-1] + ".ome.tiff")) for subfolder in subfolders])
        pool.close()
        pool.join()






