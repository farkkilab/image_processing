# Image_processing

This repository stores in-house tCyCIF image processing scripts for Färkkilä lab.

![Image processing workflow](./image_workflow_new.png)

The Illumination correction picture is from: A BaSiC Tool for Background and Shading Correction of Optical Microscopy Images, by Tingying Peng, Kurt Thorn, Timm Schroeder, Lichao Wang, Fabian J Theis, Carsten Marr*, Nassir Navab*, Nature Communication 8:14836 (2017). [doi: 10.1038/ncomms14836](http://www.nature.com/articles/ncomms14836).

## Preparation

You should have conda installed on you device. Recommend miniconda. Create environment based on the yml files under folder ``envs``.

```
conda env create --name <name_of_your_environment> --file=<xx.yml>

# For example:
conda env create --name quantification --file=quantification.yml
```

You need to prepare conda environments for stitching, segmentation and quantification. Napari tools are recommended to be installed for visualize images.

## Run scripts

### BaSiC - illumination correction

Scripts and docker files are adapted from [https://github.com/labsyspharm/basic-illumination](https://github.com/labsyspharm/basic-illumination). 

* This step should be run on Linux platform.
* Docker should be pre-installed.
* BaSiC works on unstitched raw images (ome.tiff, rcpnl, ...)

```
# file structure
./
├── BaSiC_run.sh
├── Dockerfile
├── illumination # output folder
├── imagej_basic_ashlar_filepattern.py
├── imagej_basic_ashlar.py
└── raw # input folder
```

```
docker build -t my-basic-image # you should have a dockerfile in the current path
docker images # check if your new image is already here

docker run --privileged -it -m 120g --cpus=20 --mount type=bind,source="$(pwd)",target=/data my-basic-image bash # start your docker image
bash <your path> BaSic_run.sh # run bash script to process images
```

### Ashlar

Script: ``./pipeline/ashlar_workflow.py``

Open the script and modify ``my_path``, ``output_path`` and ``file_type`` based on your dataset.

```
conda activate <your_environment_for_ashlar>
python ashlar_workflow.py -c 42 # 42 is the number of threads for parallel computation
```

If you have many cycles then consider decrease the number of threads (minimum 1).

### Segmentation

Script: ``./pipeline/stardist_segmentation.py``

Open the file and modify ``INPUT_PATH``, ``OUTPUT_PATH`` based on your dataset.

```
conda activate <your_environment_for_stardist>
python stardist_segmentation.py
```

Note: We also provide jupyter notebooks if you want to visualize images while running the analysis: ``./pipeline/stardist_segmentation.ipynb``

### Quantification

Script: ``./pipeline/quantification_workflow.py``

Open the file and modify ``dir1``, ``dir2`` based on your dataset.

Besides you should also prepare ``channel.csv`` and create a new folder to store the output.

```
conda activate <your_environment_for_quantification>
python quantification_loop.py -o <output dir> -ch <channel.csv dir> -c 46 # 46 is the number of threads for parallel computation
```

If you have super large image then consider decrease the number of threads (minimum 1).

---

If you have any problem, please contact: [ziqi.kang@helsinki.fi]()
