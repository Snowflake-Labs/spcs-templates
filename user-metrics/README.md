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

Create database, schema, stage and image repository that defined in
`metrics_service_setup.sql` file.

Once the image repository created execute the following command:

```commandline
make build-all REPO=$SPCS_IMAGE_REPOSITORY
```

The command above will build and push all containers to the SPCS image repository
and create `metrics-service.yml` file.

Then, start the service using the following SQL:
```commandline

create service test01
in compute pool VASHAH_POOL
from specification '
    INSERT_CONTENT_OF `metrics-service.yml` FILE
';

```
