# Introduction

In this tutorial, you create a service (metrics_visualizer) to consume the [metrics provided by Snowflake for compute pools](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview) in your account, and present the data using a Grafana dashboard to visualize the metrics.

```commandline
Consider the code provided for this tutorial as a template to build an initial metrics service that you can customize it for different use cases.
```

Code to create the service is provided on [GitHub](https://github.com/Snowflake-Labs/spcs-templates/tree/main/user-metrics). You clone the repository and upload the images to a repository in your Snowflake account.

This service is made up of the following [Docker images](https://hub.docker.com/u/snowflakedb):

* **Metrics Discovery service (spcs-oss-mdservice):** An HTTP service that discovers the metrics endpoints for the available compute pools.

* **Otel collector (spcs-oss-otel-prometheus):** An OpenTelemetry (OTel) collector that pulls node metrics from compute pools discovered by the metrics discovery service and exports to prometheus.

* **Prometheus (spcs-oss-prometheus):** A data store for metrics that the service uses to store compute pool metrics.

* **Grafana (spcs-oss-grafana):** A dashboard tool that pulls data from Prometheus and provides a way to visualize the data.

These containers work together as follows:

1. The OTEL collector container accesses metrics from compute pool nodes and saves it to the Prometheus database. The container does the following:
    * Communicates with the metrics discovery services container to obtain the DNS names of the available compute pools.
    * Retrieves the SRV records for each available compute pool to find the metric publishers for the nodes.
    * Uses the node IPs from these SRV records to access the metrics from the individual nodes in each compute pool.
    * Writes the metrics data to the Prometheus database.
2. The Grafana container then reads the metrics from the Prometheus database and creates the visualization.

For more information, see [Metrics Overview](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview).

In this tutorial, you will do the following in this tutorial:

1. **Set up the prerequisites:**  For this tutorial, you will need a compute pool to collect metrics. You will create a compute pool and start a service (echo_service, which is provided in Tutorial 1).

2. **Create the metrics visualizer service:** Follow instructions in this tutorial to create this service.

3. **Review the metrics:** Use the public endpoint exposed by the metrics visualizer service (Grafana) to review the metrics.
