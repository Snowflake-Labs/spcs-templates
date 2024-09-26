# 1: Upload service images to a repository

1. Make sure you have the URL of the repository where you want to upload the images. To get this URL, you can execute the [SHOW IMAGE REPOSITORIES](https://docs.snowflake.com/sql-reference/sql/show-image-repositories) command, using SnowSQL CLI or the Snowsight web interface. The command returns the repository URL, including the organization name and the account name.

2. Open a terminal window, and change to the directory of your choice.

3. Clone the GitHub repository.
```commandline
git clone https://github.com/Snowflake-Labs/spcs-templates.git
```

4. Go to [user-metrics/metrics-service-grafana](../metrics-service-grafana/) directory. This directory has source code for the visualization service that you are creating.

5. To enable Docker to upload images on your behalf to your image repository, you must use the docker login command to authenticate to the Snowflake registry:
```commandline
docker login <registry_hostname> -u <username>
```
Note the following:
* The `<registry_hostname>` is the hostname part of the repository URL. For example, myorg-myacct.registry.snowflakecomputing.com.

 * `<username>` is your Snowflake username. Docker will prompt you for your password.

6. Use one of the following options to upload images to your image repository:
    * Option 1: The easiest option is to upload the pre-built [Docker images](https://hub.docker.com/u/snowflakedb) that Snowflake provides on dockerhub.
    ```commandline
    make pull-upload-all SNOW_REPO=<repositry-url>
    ```
    * Option 2: Build all Docker images manually and then upload the images:
    ```commandline
    make build-all SNOW_REPO=<repository-url>
    ```
7. Call the `SYSTEM$REGISTRY_LIST_IMAGES` function to verify that the images are present in the repository.
```commandline
SELECT SYSTEM$REGISTRY_LIST_IMAGES('/tutorial_db/data_schema/tutorial_repository');
```
