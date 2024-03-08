# 3: Use the service (access your compute pool metrics)

To send requests to the service for the compute pool metrics, you need the ingress URL of the public endpoint the service exposes.

1. To get a list of endpoints that the service exposes, execute the [SHOW ENDPOINTS](https://docs.snowflake.com/sql-reference/sql/show-endpoints) command. In the response, the ingress_url column provides the URL.

```commandline
SHOW ENDPOINTS IN SERVICE TUTORIAL_DB.DATA_SCHEMA.OTEL_PROM_METRICS;
```

2. Append /metrics to the endpoint URL, and paste it in the web browser. You can review the compute pool metrics in the browser.