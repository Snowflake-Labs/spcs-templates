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

You now have a sample service (Echo service) running in a compute pool (tutorial_compute_pool). Proceed with creating to create the visualization service to access the metrics published by the compute pool.