# 2: Create a service

1. To create the service, execute the following CREATE SERVICE command using SnowSQL or the Snowsight web interface. Make sure you use the test_role to execute the [CREATE SERVICE](https://docs.snowflake.com/sql-reference/sql/create-service) command.

```commandline
USE TUTORIAL_DB.DATA_SCHEMA;

CREATE SERVICE OTEL_DATADOG_METRICS
IN COMPUTE POOL TUTORIAL_COMPUTE_POOL
FROM SPECIFICATION '
  spec:
    containers:
    - name: main
      image: /tutorial_db/data_schema/tutorial_repository/otel:0.91.0
      secrets:
      - snowflakeSecret: DATADOG_METRICS_SITE
        secretKeyRef: SECRET_STRING
        envVarName: DATADOG_METRICS_SITE
      - snowflakeSecret: DATADOG_METRICS_KEY
        secretKeyRef: SECRET_STRING
        envVarName: DATADOG_METRICS_KEY       
      volumeMounts:
      - name: otel-configs
        mountPath: /var/spcs
      args:
      - --config
      - /var/spcs/otel_config_datadog.yaml
    volume:
    - name: otel-configs
      source: "@CONFIGS"
'
EXTERNAL_ACCESS_INTEGRATIONS = (DATADOG_APIS_ACCESS_INTEGRATION)
;
```

The specification defines one container that runs the OTel collector image. When the container runs, the following happens:
  * Snowflake mounts the internal stage @configs inside the container (see the volume and volumeMount sections).
  * The --config parameter causes the container to read the OTel collector configuration file to set up the metrics pipeline, identifying the compute pool to scrape the metrics from and your datadog account where to make the metrics available (see OTel configuration in the preceding section).


# 2: Create a service

The make command in the preceding section also creates a service specification file (metrics-service.yml) in the user-metrics directory. When you execute a CREATE SERVICE statement to create the service, you include the contents of this file inline in that statement.

1. To create the service, execute the following CREATE SERVICE command using SnowSQL CLI or Snowsight web interface.

```commandline
CREATE SERVICE metrics_visualizer
  IN COMPUTE POOL tutorial_compute_pool
  FROM SPECIFICATION $$
    <copy/paste the specification from metrics-service.yml file>
  $$;
```

2. Make sure the service is running. Execute the following SQL commands to get detailed information about the service you just created. For more information, see [Working with services](https://docs.snowflake.com/developer-guide/snowpark-container-services/working-with-services).
    * To list services in your account, execute the [SHOW SERVICES](https://docs.snowflake.com/sql-reference/sql/show-services) command:
    ```commandline
    SHOW SERVICES;
    ```
    * To get the status of your service, call the system function [SYSTEM$GET_SERVICE_STATUS](https://docs.snowflake.com/sql-reference/functions/system_get_service_status):
    ```commandline
    SELECT SYSTEM$GET_SERVICE_STATUS('TUTORIAL_DB.DATA_SCHEMA.OTEL_DATADOG_METRICS');
    ```
    * To get service logs from the container, call the system function [SYSTEM$GET_SERVICE_LOGS](https://docs.snowflake.com/sql-reference/functions/system_get_service_logs).
    ```commandline
    SELECT SYSTEM$GET_SERVICE_LOGS('TUTORIAL_DB.DATA_SCHEMA.OTEL_DATADOG_METRICS', 0, 'main');
    ```

Now you have a Snowpark Container Services service running (using the open source OTel collector image). The collector is scraping the specified compute pool metrics every 10 seconds. These metrics are exported to your datadog account. You can access these metrics by logging to your datadog account under metrics section.