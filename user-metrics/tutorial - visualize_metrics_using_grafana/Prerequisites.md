# Prerequisites

You need a compute pool with a service running to get any metrics. To set up this service, you will follow the instructions in [Tutorial 1](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/tutorial-1) instructions to create a simple “echo” service with modification. In the current implementation, the metrics_visualizer service you create in this tutorial can see only the compute pools whose owner role is the same as the owner role of the service. So you need to make sure to create the compute pool using the test_role as described:

1. Complete [Common Setup, Create Snowflake objects](https://docs.snowflake.com/developer-guide/snowpark-container-services/tutorials/common-setup) provided for various tutorials with the following modifications:
    * Do not use the ACCOUNTADMIN role to create the compute pool named tutorial_compute_pool. Instead, grant test_role the privilege to create a compute pool.
    ```commandline
    USE ROLE ACCOUNTADMIN;
    GRANT CREATE COMPUTE POOL ON ACCOUNT TO ROLE test_role;
    USE ROLE TEST_ROLE;
    ```
    * Continue with the steps in the Common Setup tutorial and create the compute pool as part of the script that is executed using the test_role:
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

You now have a sample service (Echo service) running in a compute pool (tutorial_compute_pool). Proceed with creating to create the visualization service to access the metrics published by the compute pool.