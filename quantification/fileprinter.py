# Instructions to run this on one sample:
# conda env create -n quant -f quantification.yml
# conda activate quant
# python quantification.py -M /data/s3segmenter_output/Sample_01/cellMask.tif -in /data/raw/scset/Sample_01.ome.tif -o /data/projects/casado/scset/quantification/ -ch /data/projects/casado/scset/channel_names.csv -c 46 
# If it fails blame <julia.casado@helsinki.fi>
import os
import argparse
from pathlib import Path
import csv
import time
import skimage.io
import pandas as pd
import numpy as np
import skimage.measure as measure
import multiprocessing as mp
import tifffile

dir2 = '/media/junqmada/tsclient/E/Ada/quantification/masks3'
dir1 = '/media/junqmada/tsclient/E/Ada/quantification/images3'
global iPath
global mPath
ips =[]
mps =[]
global CHANNEL_PROPS
CHANNEL_PROPS=['mean_intensity']
global MORPH_PROPS
MORPH_PROPS=['label','centroid','area','eccentricity']
global IMAGEPATH
global CURRENT_MASK
global CHANNELS

for filename in os.listdir(dir1):
	if filename.endswith(".tif"):
		iPath = os.path.join(dir1, filename)
		ips.append(iPath)	

for maskname in os.listdir(dir2):
	if maskname.endswith(".tif"):
		mPath = os.path.join(dir2, maskname)
		mps.append(mPath)

for i in range(len(ips)):	
	maskPaths = sorted(mps)[i]
	imagePath = ips[i]
	print(imagePath,maskPaths)
