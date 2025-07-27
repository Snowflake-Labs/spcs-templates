# Introduction
After completing the [common setup](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/tutorials/common-setup), you are ready to create a service. In this tutorial, you will create one service (named echo_service_with_cors) that exposes an endpoint to respond to CORS requests. Then you will create a service locally to send CORS requests to the endpoint using **PAT token authentication**: 

**1. /healthcheck:** this method should respond with "I'm ready!"

**2. /echo:** this method should echo back the message that is sent in the request body.

<br>

At a high-level, this tutorial contains the following steps:

1. Download the service code for this tutorial.

2. Build a Docker image for Snowpark Container Services, and upload the image to a repository in your account.

3. Create the service by providing the service specification file and the compute pool in which to run the service.

4. Configure PAT token authentication

5. Send CORS requests from localhost using PAT tokens

<br>

# 1: Download the service code
1. Code (a Python application) is provided to create the CORS services.

2. Download the code from this repo under /cors_app.

<br>

# 2: Build an image and upload
Build an image for the linux/amd64 platform that Snowpark Container Services supports, and then upload the image to the image repository in your account (see Common Setup).

You will need information about the repository (the repository URL and the registry hostname) before you can build and upload the image. For more information, see Registry and Repositories.

**Get information about the repository**

1. To get the repository URL, execute the SHOW IMAGE REPOSITORIES SQL command.
```
SHOW IMAGE REPOSITORIES;
```
The repository_url column in the output provides the URL. An example is shown:
```
<orgname>-<acctname>.registry.snowflakecomputing.com/tutorial_db/data_schema/tutorial_repository
```
The host name in the repository URL is the registry host name. An example is shown:
```
<orgname>-<acctname>.registry.snowflakecomputing.com
```

**Build image and upload it to the repository**

1. Open a terminal window, and change to the directory /cors_app.

2. To build a Docker image, execute the following docker build command using the Docker CLI. Note the command specifies current working directory (.) as the PATH for files to use for building the image.
```
docker build --rm --platform linux/amd64 -t <repository_url>/<image_name> .
```
For image_name, use cors_image:latest.
**Example**
```
docker build --rm --platform linux/amd64 -t myorg-myacct.registry.snowflakecomputing.com/tutorial_db/data_schema/tutorial_repository/cors_image:latest .
```
3. Upload the image to the repository in your Snowflake account. In order for Docker to upload an image on your behalf to your repository, you must first authenticate Docker with the registry.

To authenticate Docker with the image registry, execute the following command.
```
docker login <registry_hostname> -u <username>
```
For username, specify your Snowflake username. Docker will prompt you for your password.

To upload the image execute the following command:
```
docker push <repository_url>/<image_name>
```
**Example**
```
docker push myorg-myacct.registry.snowflakecomputing.com/tutorial_db/data_schema/tutorial_repository/cors_image:latest
```

<br>

# 3: Create the service
In this section you create a service and also create a service function to communicate with the service.

To create a service, you need the following:

A [compute pool](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/working-with-compute-pool). Snowflake runs your service in the specified compute pool. You created a compute pool as part of the common setup.

A [service specification](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/specification-reference). This specification provides Snowflake with the information needed to configure and run your service. For more information, see [Snowpark Container Services: Working with services](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/working-with-services). In this tutorial, you provide the specification inline, in CREATE SERVICE command. You can also save the specification to a file in your Snowflake stage and provide file information in the CREATE SERVICE command as shown in Tutorial 2.

A service function is one of the methods available to communicate with your service. A service function is a user-defined function (UDF) that you associate with the service endpoint. When the service function is executed, it sends a request to the service endpoint and receives a response.

1. Verify that the compute pool is ready and that you are in the right context to create the service.

  a. Previously you set the context in the [Common Setup](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/tutorials/common-setup.html#label-snowpark-containers-common-setup-create-objects) step. To ensure you are in the right context for the SQL statements in this step, execute the following:
  ```
  USE ROLE test_role;
  USE DATABASE tutorial_db;
  USE SCHEMA data_schema;
  USE WAREHOUSE tutorial_warehouse;
  ```
  b. To ensure the compute pool you created in the common setup is ready, execute DESCRIBE COMPUTE POOL, and verify that the state is ACTIVE or IDLE. If the state is STARTING, you need to wait until the state changes to either ACTIVE or IDLE.
  ```
  DESCRIBE COMPUTE POOL tutorial_compute_pool;
  ```

2. To create the echo_service_with_cors service with corsSettings that allows localhost, execute the following command using test_role:
```
USE ROLE test_role;
CREATE SERVICE echo_service_with_cors
  IN COMPUTE POOL tutorial_compute_pool
  EXTERNAL_ACCESS_INTEGRATIONS = (allow_cors_requester_integration)
  FROM SPECIFICATION $$
    spec:
      containers:
      - name: echo
        image: /tutorial_db/data_schema/tutorial_repository/cors_image:latest
        env:
          SERVER_PORT: 8000
          CHARACTER_NAME: Bob
        readinessProbe:
          port: 8000
          path: /healthcheck
      endpoints:
      - name: echoendpoint
        port: 8000
        public: true
        corsSettings:
          Access-Control-Allow-Origin:
          - http://localhost:8888
          Access-Control-Allow-Methods:
          - POST
          - GET
          Access-Control-Allow-Headers:
          - Authorization
          - Content-Type
          - Origin
          - Vary
          - Custom-Header-A
          Access-Control-Expose-Headers:
          - Custom-Header-X
      $$
   MIN_INSTANCES=1
   MAX_INSTANCES=1;
```
<pre>
<b>Note</b>
If a service with that name already exists, use the DROP SERVICE command to delete the previously created service, and then create this service.
</pre>


3. Execute the following SQL commands to get detailed information about the service you just created. For more information, see Snowpark Container Services: Working with services.

To list services in your account, execute the SHOW SERVICES command:
```
SHOW SERVICES;
```
To get information about your service including the service status, execute the DESCRIBE SERVICE command.
```
DESC SERVICE echo_service_with_cors;
```
Verify the status column shows the service status as RUNNING; if the status is PENDING, it indicates the service is still starting. To investigate why the service is not RUNNING, execute the SHOW SERVICE CONTAINERS IN SERVICE command and review the status of individual containers:
```
SHOW SERVICE CONTAINERS IN SERVICE echo_service_with_cors;
```
Verify that you can access the endpoint by hitting the endpoint in the browser:
**Example**
```
https://ftwoqas5-myorg-myacct.snowflakecomputing.app/healthcheck
```

# 4: Configure PAT token authentication
Configure a PAT token for the user by following the [PAT token guide](https://docs.snowflake.com/LIMITEDACCESS/programmatic-access-tokens)

# 5: Run the service locally

## Option 1: Using Docker (Recommended)
In the cors_app folder, execute:
```
cd cors_app
docker build -t cors-app .
docker run -p 8888:8888 cors-app
```

Access the endpoint at http://localhost:8888/ui in a web browser. This causes the service to execute the ui() function (see echo_service.py).

# 6: Send CORS requests to the endpoint

The simplified interface now provides **2 main functionalities** using PAT token authentication:

  **a. Making a GET request** - Test CORS GET requests with PAT token authentication
  
  **b. Making a POST request** - Test CORS POST requests with PAT token authentication

Simply input the endpoint URL and your PAT token. The interface will:
- Use Bearer authentication with your PAT token
- Send custom headers to test CORS configuration
- Validate Access-Control-Allow-Headers and Access-Control-Expose-Headers

The simplified UI eliminates the complexity of key pair authentication and JWT token exchange, making it easier to test CORS functionality with just PAT tokens.

**Testing endpoints:**
- GET: Test against `/healthcheck` or other GET endpoints
- POST: Test against `/echo` endpoint with custom payloads

Both functionalities validate CORS headers as an example of proper CORS implementation. 

