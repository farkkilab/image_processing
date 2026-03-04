# 1. Start from your base image
FROM vanvalenlab/deepcell-tf:0.12.10-gpu

# 2. Switch to root to install system software
USER root

# 3. Install Java and download OME tools
RUN apt-get update && apt-get install -y openjdk-11-jre-headless wget unzip && \
    mkdir -p /opt/ome-tools && cd /opt/ome-tools && \
    wget https://github.com/glencoesoftware/bioformats2raw/releases/download/v0.7.0/bioformats2raw-0.7.0.zip && \
    unzip bioformats2raw-0.7.0.zip && \
    wget https://github.com/glencoesoftware/raw2ometiff/releases/download/v0.4.0/raw2ometiff-0.4.0.zip && \
    unzip raw2ometiff-0.4.0.zip && \
    rm *.zip && apt-get clean

# 4. Install your Python packages
# We use --no-cache-dir to keep the image size smaller
RUN pip install --no-cache-dir \
    zarr==2.15.0 \
    deeptile \
    tqdm \
    scikit-image \
    opencv-python-headless

# 5. Add OME tools to the system PATH
ENV PATH="/opt/ome-tools/bioformats2raw-0.7.0/bin:/opt/ome-tools/raw2ometiff-0.4.0/bin:${PATH}"

# 6. Set the default working directory
WORKDIR /notebooks
