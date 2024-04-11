# SPCS Service to export metrics on Datadog

This is a sample SPCS service that exports metrics to your datadog account.

The metrics stack consist of the following containers:
* **[Metrics Discovery service](https://github.com/Snowflake-Labs/spcs-templates/tree/main/user-metrics/mdservice):** An HTTP service that discovers the metrics endpoints for the available compute pools.

* **[Otel collector](https://github.com/open-telemetry/opentelemetry-collector-contrib):** An OpenTelemetry (OTel) collector that pulls node metrics from compute pools discovered by the metrics discovery service and exports to datadog.

# Deploying metrics service

1. Containers can be built manually from this repository, or one can use containers from the [dockerhub](https://hub.docker.com/u/snowflakedb)

2. Follow [Tutorial](../tutorial%20-%20export_metrics_to_datadog/) to deploy this metrics service.
