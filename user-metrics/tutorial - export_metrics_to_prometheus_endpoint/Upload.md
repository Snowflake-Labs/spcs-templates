# 1: Upload service images to a repository

In this step you do two things:
* Pull the open source OTel collector image and upload to a repository to your Snowflake account.
* Create an OTel configuration and upload it to an internal stage in your Snowflake account. This configuration directs OTel to create a pipeline that polls tutorial_compute_pool for metrics and to make the collected metrics available in prometheus-compatible format on port 9001.

## 1a: Pull the OTel image and upload it to a repository
In this step, you pull the open source OTel collector image from GitHub, tag it, and upload it to the [image repository](https://docs.snowflake.com/developer-guide/snowpark-container-services/working-with-registry-repository) in your account (that you created as part of [Common Setup](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/common-setup)).

You will need information about the repository in your account (the repository URL and the registry hostname) before you can build and upload the image.

1. Make sure you have the URL of the repository where you want to upload the images. To get this URL, you can execute the [SHOW IMAGE REPOSITORIES](https://docs.snowflake.com/sql-reference/sql/show-image-repositories)  command, using SnowSQL or the Snowsight web interface. The command returns the repository URL, which includes the organization name and the account name.

2. Open a terminal window, and change to the directory of your choice.

3. Pull in the OpenTelemetry Collector Docker image:
```commandline
docker pull --platform linux/amd64 docker.io/otel/opentelemetry-collector-contrib:0.91.0
```

4. Tag the image.
```commandline
docker tag docker.io/otel/opentelemetry-collector-contrib:0.91.0 <repository_url>/otel:0.91.0
```
Example

```commandline
docker tag docker.io/otel/opentelemetry-collector-contrib:0.91.0 myorg-myacct.registry.snowflakecomputing.com/tutorial_db/data_schema/tutorial_repository/otel:0.91.0
```

5. Upload the image to the repository in your Snowflake account. For Docker to upload an image on your behalf to your repository, you must first authenticate Docker with Snowflake.
    * To authenticate Docker with the Snowflake registry, execute the following command:
    * The <registry_hostname> is the hostname part of the repository URL. For example, myorg-myacct.registry.snowflakecomputing.com.
    * The <username> is your Snowflake username. Docker will prompt you for your password.
    ```commandline
    docker login <registry_hostname> -u <username>
    ```  
    * To upload the image, execute the following command:
    ```commandline
    docker push <repository_url>/<image_name>
    ```
    Example

    ```commandline
    docker push myorg-myacct.registry.snowflakecomputing.com/tutorial_db/data_schema/tutorial_repository/otel:0.91.0
    ```

6. Call the [SYSTEM$REGISTRY_LIST_IMAGES](https://docs.snowflake.com/sql-reference/functions/system_registry_list_images) function to verify that the image is present in the repository.
    ```commandline
    SELECT SYSTEM$REGISTRY_LIST_IMAGES( '/tutorial_db/data_schema/tutorial_repository' );
    ```


## 1b: Create an OTel configuration and upload it to an internal stage
This OTel collector configuration identifies the compute pool where to read metrics from and exposes them on an endpoint. The configuration settings are defined in YAML and are read by the OTel service to configure its behavior. For more information about how compute pool metrics are exposed, see [Overview](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview#label-spcs-compute-pool-metrics-overview).

1. Save the following configuration to a file named otel_config_prometheus.yaml on your local computer.
```commandline
receivers:
 prometheus:
   config:
     scrape_configs:
       - job_name: "spcs-compute-pool"
         scrape_interval: 10s
         dns_sd_configs:
           - names:
             - metrics.tutorial_compute_pool.snowflakecomputing.internal
             type: 'A'
             port: 9001
             refresh_interval: 30s
         metrics_path: /metrics

exporters:
 prometheus:
   endpoint: "0.0.0.0:9001"
   resource_to_telemetry_conversion:
     enabled: true

service:
  pipelines:
   metrics/1:
     receivers: [prometheus]
     processors: []
     exporters: [prometheus]
```
This OTel configuration defines a pipeline with one receiver and one exporter:

* Receiver: This configuration directs the OTel collector to poll http://metrics.tutorial_compute_pool.snowflakecomputing.internal:9001/metrics for metrics in Prometheus format every 10 seconds (scrape_interval), resolving DNS every 30 seconds (refresh_interval) for any changes in compute pool nodes or any node IP address changes.

    In dns_sd_configs, name is the domain name of the compute pool. The OTel service uses it to find IP addresses of nodes in the compute pool. For more information, see [Overview](https://docs.snowflake.com/LIMITEDACCESS/snowpark-container-services/compute-pool-metrics-overview#label-spcs-compute-pool-metrics-overview).

* Exporter: This configuration directs the collector to make the collected metrics available on port 9001 (to be exposed as an endpoint in the service specification in the next section), also using the Prometheus format (see [Prometheus exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusexporter#prometheus-exporter)).

This configuration makes the OTel image a web service listening on port 9001, where metrics can be queried from. In the next section, the Snowpark Container Services service you create exposes this port as a public endpoint to allow requests to the service from the public web.

You will upload this configuration file to a Snowflake stage, and then the Service will mount that stage for the OTel service code to read.

```commandline
Note

This OTel collector configuration has been tested against version 0.91.0, as specified when pulling the container image. If you’re using a different version, the configuration might require changes.
```

2. Upload the Otel collector configuration to the internal stage (configs) you created in your Snowflake account using one of the following methods:
    * **The Snowsight web interface:** For instructions, see [Choosing an internal stage for local files](https://docs.snowflake.com/user-guide/data-load-local-file-system-create-stage).
    * **The SnowSQL:**  Execute the following [PUT](https://docs.snowflake.com/sql-reference/sql/put) command:
    ```commandline
    PUT file://<file-path>[/\]otel_config_prometheus.yaml @configs
      AUTO_COMPRESS=FALSE
      OVERWRITE=TRUE;
    ```
    For example:
    * Linux or macOS
    ```commandline
    PUT file:///tmp/otel_config_prometheus.yaml @configs
      AUTO_COMPRESS=FALSE
      OVERWRITE=TRUE;
    ```
    * Windows
    ```commandline
    PUT file://C:\temp\otel_config_prometheus.yaml @configs
      AUTO_COMPRESS=FALSE
      OVERWRITE=TRUE;
    ```
    * You can also specify a relative path.
    ```commandline
    PUT file://./otel_config_prometheus.yaml @configs
      AUTO_COMPRESS=FALSE
      OVERWRITE=TRUE;
    ```
    The command sets OVERWRITE=TRUE so that you can upload the file again, if needed (for example, if you fixed an error in your specification file). If the PUT command is executed successfully, information about the uploaded file is printed out.

3. Verify the configuration file exists on the stage:
```commandline
LIST @configs;
```