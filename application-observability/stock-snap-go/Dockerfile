FROM alpine

# Set the working directory
WORKDIR /workspace

# Copy application files to the container
COPY app /workspace/
COPY stock-snap.json /workspace/

# Command to run the Go app
CMD ["./app"]