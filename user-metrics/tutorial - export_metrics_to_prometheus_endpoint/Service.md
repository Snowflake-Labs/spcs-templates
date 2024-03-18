# 2: Create a service

1. To create the service, execute the following CREATE SERVICE command using SnowSQL or the Snowsight web interface. Make sure you use the test_role to execute the [CREATE SERVICE](https://docs.snowflake.com/sql-reference/sql/create-service) command.

```commandline
USE TUTORIAL_DB.DATA_SCHEMA;

CREATE SERVICE OTEL_PROM_METRICS
IN COMPUTE POOL TUTORIAL_COMPUTE_POOL
FROM SPECIFICATION '
  spec:
    containers:
    - name: main
      image: /tutorial_db/data_schema/tutorial_repository/otel:0.91.0
      volumeMounts:
      - name: otel-configs
        mountPath: /var/spcs
      args:
      - "--config=/var/spcs/otel_config_prometheus.yaml"
    endpoints:
    - name: http
      port: 9001
      public: true
    volume:
    - name: otel-configs
      source: "@configs"
';
```

The specification defines one container that runs the OTel collector image. When the container runs, the following happens:
  * Snowflake mounts the internal stage @configs inside the container (see the volume and volumeMount sections).
  * The --config parameter causes the container to read the OTel collector configuration file to set up the metrics pipeline, identifying the compute pool to scrape the metrics from and a port (9001) where to make the metrics available (see OTel configuration in the preceding section).

This service specification exposes one public endpoint listening on port 9001. This allows requests from the public web for the metrics.

2. Make sure the service is running. Execute the following SQL commands to get detailed information about the service you just created. For more information, see [Working with services](https://docs.snowflake.com/developer-guide/snowpark-container-services/working-with-services).
    * To list services in your account, execute the [SHOW SERVICES](https://docs.snowflake.com/sql-reference/sql/show-services) command:
    ```commandline
    SHOW SERVICES;
    ```
    * To get the status of your service, call the system function [SYSTEM$GET_SERVICE_STATUS](https://docs.snowflake.com/sql-reference/functions/system_get_service_status):
    ```commandline
    SELECT SYSTEM$GET_SERVICE_STATUS('OTEL_PROM_METRICS');
    ```
    * To get service logs from the container, call the system function [SYSTEM$GET_SERVICE_LOGS](https://docs.snowflake.com/sql-reference/functions/system_get_service_logs).
    ```commandline
    SELECT SYSTEM$GET_SERVICE_LOGS('TUTORIAL_DB.DATA_SCHEMA.OTEL_PROM_METRICS', 0, 'main');
    ```

Now you have a Snowpark Container Services service running (using the open source OTel collector image). The collector is scraping the specified compute pool metrics every 10 seconds. You can access the metrics by sending requests to the public endpoint that the service exposes.