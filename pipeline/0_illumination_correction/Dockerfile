# Use the Fiji image with OpenJDK 8 as the base image
FROM fiji/fiji:fiji-openjdk-8

ENTRYPOINT []
ENV JVM_OPTS="-Xms50g -Xmx50g"
ENV _JAVA_OPTIONS="-Xms50g -Xmx50g"
ENV JAVA_OPTS="-Xms50g -Xmx50g"

# Download and install the BaSiC plugin for Fiji
RUN wget https://github.com/marrlab/BaSiC/raw/b6943502853c052fd93c6fabc807bc40907e73ce/BaSiCPlugin.zip && \
    unzip BaSiCPlugin.zip && \
    mv BaSiCPlugin/BaSiC_.jar Fiji.app/plugins/ && \
    mv BaSiCPlugin/Dependent/*.jar Fiji.app/jars/ && \
    rm -r BaSiCPlugin.zip BaSiCPlugin __MACOSX && \
    rm Fiji.app/jars/jtransforms-2.4.jar

# Copy all Python scripts to the working directory in the container
COPY --chmod=777 *.py ./
