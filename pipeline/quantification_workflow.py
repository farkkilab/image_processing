# Instructions to run this script when processing multiple images in one folder:
# conda env create -n quant -f quantification.yml # only when no environment installed
# conda activate quant
# python quantification_loop.py -o <output dir> -ch <channel dir> -c 46

# If you find bugs, contact Ziqi <ziqi.kang@helsinki.fi>. :]
# This script is based on Julia's script <julia.casado@helsinki.fi>. 

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
from functools import partial

dir2 = 'C://Users//Public//Farkkila_lab_datasets//Ada_dataset//quantification_sample//masks' # replace it with your own mask dir
dir1 = 'C://Users//Public//Farkkila_lab_datasets//Ada_dataset//quantification_sample//image' # replace it with your own image dir

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
        if filename.endswith(".tif") or filename.endswith(".tiff"):
                iPath = os.path.join(dir1, filename)
                ips.append(iPath)
        
for maskname in os.listdir(dir2):
        if maskname.endswith(".tif") or maskname.endswith(".tiff"):
                mPath = os.path.join(dir2, maskname)
                mps.append(mPath)

def channelQuantification(channelNamesFile, maskPaths, imagePath, channel):
	channel_image_loaded = tifffile.imread(imagePath, key = channel)
	print("channelQuantification step, channel names file is {}, read in channel {}".format(channelNamesFile, channel))

	mask_loaded = tifffile.imread(maskPaths)
	if channel == 0:
		props = MORPH_PROPS + CHANNEL_PROPS
	else:
		props = CHANNEL_PROPS
	properties = measure.regionprops_table(mask_loaded, channel_image_loaded, properties=props)
	result = pd.DataFrame(properties)
	result.rename(columns={'mean_intensity':checkChannelNames(channelNamesFile)[channel], 'label':'ID', 'centroid-0':'X Position', 'centroid-1':'Y Position', 'area':'Area', 'eccentricity':'Eccentricity'},inplace=True)

	return result

def imageQuantification(masks_loaded,threads):
	mask_names = list(masks_loaded.keys())
	result = {m_name: [] for m_name in mask_names}
	pool = mp.Pool(threads)
	print('Length of channels: {}'.format(len(checkChannelNames(args.channelNamesFile))))

	res = pool.map(partial(channelQuantification, args.channelNamesFile, maskPaths, imagePath), 
		range(len(checkChannelNames(args.channelNamesFile))))
	pool.close()
	pool.join()

	result[mask_names[0]] = pd.concat(res,axis=1)
		
	#Iterate through number of masks to extract single cell data
	if len(mask_names) > 1:
		print('THIS PRINT SHOULD NOT SHOW')
		for mask in range(len(mask_names)):
			CURRENT_MASK = masks_loaded[mask_names[mask]] 
				# New pool for each time we modify the global variable: 'CURRENT_MASK'
			pool = mp.Pool(threads)
			res = pool.map(partial(channelQuantification, args.channelNamesFile, maskPaths, imagePath), 
		  range(len(checkChannelNames(args.channelNamesFile))))
			pool.close()
			pool.join()
			result[mask] = pd.concat(res)
			#Concatenate all data from all masks to return
		merged_data = pd.concat([result[mask] for mask in mask_names],axis=1)
	else:
		merged_data = result[mask_names[0]]
	return merged_data

def checkChannelNames(channel_names):
	channel_names_loaded = pd.read_csv(channel_names, header = None)
	channel_names_loaded.columns = ["marker"]
	channel_names_loaded_list = list(channel_names_loaded.marker)
		
	channel_names_loaded_checked = []
	for idx,val in enumerate(channel_names_loaded_list):
		if channel_names_loaded_list.count(val) > 1:
			channel_names_loaded_checked.append(val + "_"+ str(channel_names_loaded_list[:idx].count(val) + 1))
		else:
			channel_names_loaded_checked.append(val)
		
	channel_names_loaded, channel_names_loaded_list = None, None
	return channel_names_loaded_checked

if __name__ == '__main__':

	parser = argparse.ArgumentParser()
	parser.add_argument('--channelNamesFile','-ch')
	parser.add_argument('--outputFolder','-o')
	parser.add_argument('--threads','-c',type=int)
	args = parser.parse_args() 
	# print(args.channelNamesFile)

	t = time.time()
	CHANNELS = checkChannelNames(args.channelNamesFile)
	print('Channels are {}'.format(CHANNELS))

	for i in range(len(ips)):	
		maskPaths = [sorted(mps)[i]]
		imagePath = ips[i]
		print('imagePath is {}'.format(imagePath))

		masks_loaded = {}
		for m in maskPaths:
			print('maskpath is {}'.format(m))
			m_full_name = os.path.basename(m)
			m_name = m_full_name.split('.')[0]
			print('m name is {}'.format(m_name))
			masks_loaded.update({str(m_name):skimage.io.imread(m,plugin='tifffile')})
		CURRENT_MASK = masks_loaded[list(masks_loaded.keys())[0]] # load first mask to run by default unless there are more
		print('Current mask is {}'.format(CURRENT_MASK))

		IMAGEPATH = imagePath
		scdata = imageQuantification(masks_loaded, args.threads)
		output = Path(args.outputFolder)
		im_full_name = os.path.basename(imagePath)
		print(imagePath)

		im_name = im_full_name.split('.')[0]
		scdata.to_csv(str(Path(os.path.join(str(args.outputFolder),str(im_name+".csv")))),index=False)
		print('Sample {} quantified in {:.2f} seconds'.format(im_name, time.time() - t))

	#EOF
