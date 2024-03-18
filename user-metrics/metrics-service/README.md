# Metrics Service

Metrics Service is SPCS service that provides dashboards for observing compute pool, service and job metrics.
The purpose of the service is to allow users to run simple observability stack. Users
can use this repository as initial template to implement different use cases.

The metrics stack consist of the following containers:
* **Otel collector** [Otel Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib).
* **Metadata Service**. Simple http metadata service that provides a list of compute pool endpoints. 
If new compute pool is added, metadata service will discover all node that belong to it.
* **Prometheus**. Prometheus framework that is mostly used to store metrics.
* **Grafana**. Predefined dashboards that show compute pool, service and job metrics. 

Metrics services consists of several containers defined above.
Containers can be built manually from this repository, or one can use
containers from the dockerhub: TODO: https://hub.docker.com/u/snowflakedb.

### Deploying metrics service

Follow [Tutorial](../tutorial-1/README.md) to deploy this metrics service.
