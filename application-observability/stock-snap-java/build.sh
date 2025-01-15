#!/bin/bash

# This script builds a Docker image for the Stock Snap Service and pushes it to a specified repository.
# Usage: bash build.sh <repository_url> <docker_tag> <snowflake_username>
# Arguments:
#   repository_url: The URL of the Docker repository where the image will be pushed.
#   docker_tag: The tag to be used for the Docker image.
#   snowflake_username: The Snowflake username for Docker login.

# Helper function to display usage information
usage() {
    echo "Usage: $0 <repository_url> <docker_tag> <snowflake_username>"
    exit 1
}

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

# Assign arguments to variables
REPOSITORY_URL=$1
DOCKER_TAG=$2
SNOWFLAKE_USERNAME=$3

# Build jar with dependencies
mvn clean package

# Login to Docker repository
docker login $REPOSITORY_URL -u $SNOWFLAKE_USERNAME

# Build and push the Docker image
docker build --rm --platform linux/amd64 -t $REPOSITORY_URL/stock-snap-java:$DOCKER_TAG -f ./Dockerfile .
docker push $REPOSITORY_URL/stock-snap-java:$DOCKER_TAG
