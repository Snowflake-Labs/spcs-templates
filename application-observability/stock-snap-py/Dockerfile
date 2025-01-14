# Use a slim Python 3.10 base image
ARG BASE_IMAGE=python:3.10-slim-buster
FROM $BASE_IMAGE

# Set the working directory
WORKDIR /workspace

# Install snowflake telemetry python package
ARG VERSION="0.5.0"

# Install necessary tools (curl)
RUN apt-get update && apt-get install -y curl && apt-get clean

# Download the tarball, extract it, and install the package
RUN curl -L "https://github.com/snowflakedb/snowflake-telemetry-python/archive/refs/tags/v${VERSION}.tar.gz" > "snowflake-telemetry-python-${VERSION}.tar.gz" && \
    tar -xvf "snowflake-telemetry-python-${VERSION}.tar.gz" && \
    pip install --upgrade pip && \
    pip install "./snowflake-telemetry-python-${VERSION}"

# Clean up unnecessary files to reduce image size
RUN rm -rf "snowflake-telemetry-python-${VERSION}" "snowflake-telemetry-python-${VERSION}.tar.gz"

RUN pip install snowflake-telemetry-python \
              opentelemetry-exporter-otlp \
              Flask

# Copy application files to the container
COPY app.py /workspace/
COPY stock-snap.json /workspace/

# Command to run the Flask app
CMD ["python3", "app.py"]