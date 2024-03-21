# Metrics Service

Metrics Service is SPCS service that exports metrics to your datadog account.

The metrics stack consist of the following containers:
* **Otel collector** [Otel Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib).
* **Metadata Service**. Simple http metadata service that provides a list of compute pool endpoints. 
If new compute pool is added, metadata service will discover all node that belong to it.

Metrics services consists of two containers defined above.
Containers can be built manually from this repository, or one can use
containers from the dockerhub: TODO: https://hub.docker.com/u/snowflakedb.

### Deploying metrics service

Follow [Tutorial](../tutorial%20-%20export_metrics_to_datadog/README.md) to deploy this metrics service.
