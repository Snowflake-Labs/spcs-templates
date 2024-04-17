# Introduction

In this tutorial, you create a service to consume the [metrics provided by Snowflake for compute pools](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview) in your account, and export to your datadog to visualize the metrics.

Code to create the service is provided on [GitHub](https://github.com/Snowflake-Labs/spcs-templates/tree/main/user-metrics/metrics-service-datadog). You clone the repository and upload the images to a repository in your Snowflake account.

This service is made up of the following [Docker images](https://hub.docker.com/u/snowflakedb):

* **[Metrics Discovery service](https://github.com/Snowflake-Labs/spcs-templates/tree/main/user-metrics/mdservice) (spcs-oss-mdservice):** An HTTP service that discovers the metrics endpoints for the available compute pools.

* **[Otel collector](https://github.com/open-telemetry/opentelemetry-collector-contrib)(spcs-oss-otel-datadog):** An OpenTelemetry (OTel) collector that pulls node metrics from compute pools discovered by the metrics discovery service and exports to datadog.

These containers work together as follows:

1. The OTEL collector container accesses metrics from compute pool nodes and exports to datadog. The container does the following:
    * Communicates with the metrics discovery services container to obtain the DNS names of the available compute pools.
    * Retrieves the SRV records for each available compute pool to find the metric publishers for the nodes.
    * Uses the node IPs from these SRV records to access the metrics from the individual nodes in each compute pool.
    * Exports the metrics to datadog.

For more information, see [Metrics Overview](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview).

In this tutorial, you will do the following in this tutorial:

1. **Set up the prerequisites:**  For this tutorial, you will need a compute pool to collect metrics. You will create a compute pool and start a service (echo_service, which is provided in Tutorial 1).

2. **Create the datadog metrics service:** Follow instructions in this tutorial to create this service.

3. **Review the metrics:** Go to your datadog account and view the metrics.
