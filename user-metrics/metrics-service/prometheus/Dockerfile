# Use the official Prometheus image as the base image
FROM prom/prometheus:latest

# Copy the configuration file
COPY ./prometheus/prometheus.yml /etc/prometheus/prometheus.yml

# Prometheus runs as user `nobody`. This user cannot be used to write files
# to the mounted dirertory
USER 0:0
