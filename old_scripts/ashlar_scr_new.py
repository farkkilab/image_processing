
print("executed")
import os
from re import search

from os import listdir
from os.path import isfile, join
my_path = r"E:\2023-04-12_Mariana_validation\stitching"
output_path = r"E:\2023-04-12_Mariana_validation\stitching"
subfolders = [ f.path for f in os.scandir(my_path) if f.is_dir() ]

print(subfolders)

for subfolder in subfolders:
    file_path = os.path.join(output_path, subfolder)
    command = 'cd \"'+ file_path +"\""
    print(command)
    os.system(command)
    files_to_stitch=" "
    print(subfolder)
    #get standard name
    name = subfolder.split(os.sep)[-1]
    file_name = name + ".ome.tiff"
    print(file_name)
    #add name to output path
    output_path2 = os.path.join(output_path, file_name)
    #print(output_path)
    #get files and format them
    files = [f for f in listdir(subfolder) if search('rcpnl', f)]
    print(files)
    for file in files:
        print(file)
        files_to_stitch= files_to_stitch + subfolder+ os.sep + file + " "
        

    print(files_to_stitch)
    files_to_stitch = files_to_stitch.rstrip() 
    cmd= "ashlar {} -o\"{}\" --pyramid --filter-sigma 1 -m 30".format(files_to_stitch,output_path2)
    print(cmd)
    os.system(cmd)



