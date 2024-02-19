# Instructions to run this script
# conda env create -n stardist -f stardistpy.yml # only when no environment installed
# conda activate stardist
# python stardist_segmentation.py

# There are 4 registered models for 'StarDist2D':
# StarDist2D.from_pretrained() to check all models

# Name                  Alias(es)
# ────                  ─────────
# '2D_versatile_fluo'   'Versatile (fluorescent nuclei)'
# '2D_versatile_he'     'Versatile (H&E nuclei)'
# '2D_paper_dsb2018'    'DSB 2018 (from StarDist 2D paper)'
# '2D_demo'             None

# If you find bugs, contact Ziqi <ziqi.kang@helsinki.fi>. :]
# This script is based on Ada's script <ada.junquera-mencia@helsinki.fi>. 


import math
import tifffile
import os
import math
from stardist.data import test_image_nuclei_2d
from stardist.plot import render_label
from csbdeep.utils import normalize
import matplotlib.pyplot as plt
from stardist.models import StarDist2D

# input path must only have the images to segment
# output path should be an empty folder
INPUT_PATH = "P://afarkkilab//Projects//NKI//Whole_slides_validation_MHCII_Ada//Test//images"
OUTPUT_PATH = "/stardist_output/"
x = 8 # x number of tiles
y = 8 # y number of tiles
arr = os.listdir(INPUT_PATH)
model_name = '2D_versatile_fluo'

if __name__ == '__main__':
 
    model = StarDist2D.from_pretrained(model_name)
    print("Image list: {}".format(arr)) # verify you only have the desired images here

    while True:
        a = input("Do you want to proceed? [y/n]")
        if a=="y":
            for image in arr:
                image_name = image
                sep = '.'
                imageid = image_name.split(sep, 1)[0]
                IMAGE_PATH = os.path.join(INPUT_PATH, image_name)
                print("reading image {}".format(IMAGE_PATH))

                img = tifffile.imread(IMAGE_PATH)
                img = img[0]
                print("Image has a shape of {}".format(img.shape))

                labels, _ = model.predict_instances(normalize(img), n_tiles=(x, y))
                labels = labels.astype("int32")
                output_name = OUTPUT_PATH + imageid + "_labels" + ".ome.tiff"
                tifffile.imsave(output_name, labels)
                print("Finish image {}".format(IMAGE_PATH))
            continue
        elif a=="n":
            break
        else:
            print("Enter either [y/n]")