# SPCS Service to visualize metrics on Grafana

This is a SPCS service that provides dashboards for observing compute pool, service and job metrics.
The purpose of the service is to allow users to run simple observability stack. Users
can use this repository as initial template to implement different use cases.

The metrics stack consist of the following containers:
* **[Metrics Discovery service](https://github.com/Snowflake-Labs/spcs-templates/tree/main/user-metrics/mdservice):** An HTTP service that discovers the metrics endpoints for the available compute pools.

* **[Otel collector](https://github.com/open-telemetry/opentelemetry-collector-contrib):** An OpenTelemetry (OTel) collector that pulls node metrics from compute pools discovered by the metrics discovery service and exports to prometheus.

* **[Prometheus](https://github.com/prometheus/prometheus):** A data store for metrics that the service uses to store compute pool metrics.

* **[Grafana](https://github.com/grafana/grafana):** A dashboard tool that pulls data from Prometheus and provides a way to visualize the data.


# Deploying metrics service

1. Containers can be built manually from this repository, or one can use containers from the [dockerhub](https://hub.docker.com/u/snowflakedb)

2. Follow [Tutorial](../tutorial%20-%20visualize_metrics_using_grafana/README.md) to deploy this metrics service.
