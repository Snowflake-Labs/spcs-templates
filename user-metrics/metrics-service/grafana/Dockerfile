# Use the official Grafana image as the base image
FROM grafana/grafana:9.5.5

# Copy the configuration file
COPY ./grafana/grafana.ini /etc/grafana/grafana.ini

# Copy the data sources file
COPY ./grafana/datasources.yaml /etc/grafana/provisioning/datasources/datasources.yaml

# Copy the dashboards folder
COPY ./grafana/dashboards /etc/grafana/provisioning/dashboards
