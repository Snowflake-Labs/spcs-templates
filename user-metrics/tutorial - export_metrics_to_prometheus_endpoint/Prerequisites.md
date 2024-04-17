# Prerequisites

You need a compute pool with a service running to get any metrics. To set up this service, you will follow the instructions in [Tutorial 1](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/tutorial-1) instructions to create a simple “echo” service with modification. 
A role can access metrics of a compute pool only if it has one of the following privileges on the compute pool(OWNERSHIP, MONITOR).

1. Complete [Common Setup, Create Snowflake objects](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/common-setup) provided for various tutorials with the following modifications:
    * In the above tutorial we grant USAGE, MONITOR privilege to test_role on compute pool. Hence test_role can view the metrics from tutorial_compute_pool
    ```commandline
    USE ROLE ACCOUNTADMIN;
    GRANT USAGE, MONITOR ON COMPUTE POOL tutorial_compute_pool TO ROLE test_role;
    ```

2. Complete [Tutorial 1](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/tutorial-1).

3. Verify that the Echo service is running.
```commandline
SELECT SYSTEM$GET_SERVICE_STATUS('echo_service', 10);
```

## Additional prerequisites for this tutorial
Create a Snowflake internal stage (named configs). You upload OTel configuration to this stage. When the service runs, Snowflake mounts this stage as a storage volume inside the container. The OTel collector reads the configuration from this volume and sets the pipelines (compute pool to poll for the metrics and the endpoint where to make the metrics available for end users to access).
```commandline
CREATE STAGE CONFIGS
  ENCRYPTION = (type = 'SNOWFLAKE_SSE');
```
Create the stage with ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') to allow attaching this stage as a storage volume on the service.