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


## Additional prerequisites for this tutorial

1. Inorder to export metrics to datadog.
  * Firstly you need to have a datadog account. 
  * Generate API Key following this datadog [tutorial](https://docs.datadoghq.com/account_management/api-app-keys/#add-an-api-key-or-client-token). This api key is needed to export the metrics.
  * Get the metrics site from the following [location](https://docs.datadoghq.com/getting_started/site/). In this case (us5.datadoghq.com)

  Lets store these values as secrets and pass them to the otel config via environment variables.

```commandline
CREATE OR REPLACE SECRET DATADOG_METRICS_SITE
    TYPE = GENERIC_STRING
    SECRET_STRING = 'us5.datadoghq.com';
    
CREATE OR REPLACE SECRET DATADOG_METRICS_KEY
    TYPE = GENERIC_STRING
    SECRET_STRING = 'YYYYYYYYYYY';
```

2. For the data to be exported out of spcs, we need an external access integration allowing traffic to datadog.
The endpoint value will be obtained from the following [location](https://docs.datadoghq.com/getting_started/site/) and api prefix should be added to it. In this case (api.us5.datadoghq.com)

```commandline
USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS NETWORK_RULES_DB;
USE DATABASE NETWORK_RULES_DB;

CREATE OR REPLACE NETWORK RULE DATADOG_NETWORK_RULE
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('api.us5.datadoghq.com');
  
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION DATADOG_API_ACCESS_INTEGRATION
  ALLOWED_NETWORK_RULES = (DATADOG_NETWORK_RULE)
  ENABLED = true;
  
GRANT USAGE ON INTEGRATION DATADOG_API_ACCESS_INTEGRATION TO ROLE TEST_ROLE;
```