# User Metrics from Snowflake Open Source Images 

In this example we will see how to consume user metrics from open source images that are maintained by Snowflake.

- The Open Source images are available at [dockerhub](https://hub.docker.com/u/snowflakedb)
- There are three Open Source images that we maintain all of them have to be used in union to visualize metrics.
- The First image is [spcs-otel](https://hub.docker.com/r/snowflakedb/spcs-oss-otel)
    - This image is built from the [otel collector](https://github.com/open-telemetry/opentelemetry-collector-contrib) open source repository.
    - We added a new plugin to this image to discover metric endpoints per compute pool.
    - We are in the process of open sourcing the code for this custom discovery plugin [here](https://github.com/prometheus/prometheus/pull/13252).
    - This image is used for discovering metric endpoints and scraping them.
- The Second image is [spcs-prometheus](https://hub.docker.com/r/snowflakedb/spcs-oss-prometheus)
    - This image is built from the open source prometheus image [prometheus](https://hub.docker.com/r/prom/prometheus).
    - We added custom configuration to the open source image that can be found [here](prometheus/prometheus.yml).
    - This image is used to store the scraped metrics in database.
- The Third image is [spcs-grafana](https://hub.docker.com/r/snowflakedb/spcs-oss-grafana)
    - This image is built from the open source grafana image [grafana](https://hub.docker.com/r/grafana/grafana).
    - We added custom configuration to the open source image that can be found [here](grafana/grafana.ini).
    - This configuration also provides default dashboards for customers.
    - This image is used to visualize the metrics from the database.
    - Also included the Dockerfiles that we used to generate the images.


## How to use these images

- Download the three open source images from here [dockerhub](https://hub.docker.com/u/snowflakedb).
- Upload these images to Snowflake Image Registry [upload](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/tutorial-1#build-an-image-and-upload).
- Assuming the images are uploaded to repository location (tutorial_db/data_schema/tutorial_repository)
- Create a service as follows:
    ```
    CREATE SERVICE USERMETRICS
    in compute pool METRICS_POOL
    from specification '
    spec:
    container:
    - name: otel
        image: /tutorial_db/data_schema/tutorial_repository/spcs-oss-otel:latest
    - name: prometheus
        image: /tutorial_db/data_schema/tutorial_repository/spcs-oss-prometheus:latest
    - name: grafana
        image: /tutorial_db/data_schema/tutorial_repository/spcs-oss-grafana:latest
    endpoints:
    - name: grafana-ui
        port: 3000
        public: true
    ';
    ```
- This will create a service that has three containers, otel container scrapes the metrics and writes to prometheus database hosted in another container, grafana container visualizes the metrics from prometheus db and exposes them on a public endpoint.
- Execute the command to get the endpoint of the service.
    ```
    SHOW ENDPOINTS IN SERVICE USERMETRICS;
    // endpoint: bb4-tt001030-sfengineering-snowflake.temptest2.dev-snowflakecomputing.app
    ```
- Open the endpoint in a browser to visualize metrics on grafana