# Prerequisites

## Prerequisites common to Tutorials 1 and 2
You need a compute pool with a service running to get any metrics. To set up this service, you will follow the You need a compute pool with a service running to get any metrics. To set up this service, you follow the instructions in [Tutorial 1](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/tutorial-1) to create a simple “echo” service with modification. In the current implementation, the metrics_visualizer service you create in this tutorial can access only the compute pools whose owner role is the same as the owner role of the service. So you need to make sure to create the compute pool using the test_role as described:

1. Complete [Common Setup for Snowpark Container Services Tutorials](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/common-setup) with the following modifications to the Create Snowflake objects step.
    * Don’t use the ACCOUNTADMIN role to create the compute pool named tutorial_compute_pool. Instead, grant test_role the privilege to create a compute pool.
    ```commandline
    USE ROLE ACCOUNTADMIN;
    GRANT CREATE COMPUTE POOL ON ACCOUNT TO ROLE test_role;
    USE ROLE test_role;
    ```
    * Continue with the steps in the Common Setup and create the compute pool as part of the script that is executed using the test_role:
    ```commandline
    CREATE COMPUTE POOL tutorial_compute_pool
      MIN_NODES = 1
      MAX_NODES = 1
      INSTANCE_FAMILY = CPU_X64_XS;
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