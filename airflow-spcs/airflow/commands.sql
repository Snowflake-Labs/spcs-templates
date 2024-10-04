--########################## Initial Setup ##########################

USE ROLE ACCOUNTADMIN;
CREATE ROLE airflow_admin_rl;

CREATE DATABASE IF NOT EXISTS airflow_db;
GRANT OWNERSHIP ON DATABASE airflow_db TO ROLE airflow_admin_rl COPY CURRENT GRANTS;

CREATE OR REPLACE WAREHOUSE airflow_wh WITH
  WAREHOUSE_SIZE='X-SMALL';
GRANT USAGE ON WAREHOUSE airflow_wh TO ROLE airflow_admin_rl;

GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO ROLE airflow_admin_rl;

GRANT ROLE airflow_admin_rl TO USER <user_name>;

--########################## create compute pools ##########################
USE ROLE ACCOUNTADMIN;
-- Compute pool for host Postgres and Redis services
CREATE COMPUTE POOL postgres_redis
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = CPU_X64_S;

-- Compute pool for Airflow Webserver and Scheduler services
CREATE COMPUTE POOL airflow_server
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = CPU_X64_S;

-- Compute pool for Airflow Workers, set max_nodes to 2 for auto scaling
CREATE COMPUTE POOL airflow_workers
  MIN_NODES = 1
  MAX_NODES = 2
  INSTANCE_FAMILY = CPU_X64_S;

-- Grant access on these compute pools to role airflow_admin_rl
GRANT USAGE, MONITOR ON COMPUTE POOL postgres_redis to ROLE airflow_admin_rl;
GRANT USAGE, MONITOR ON COMPUTE POOL airflow_server to ROLE airflow_admin_rl;
GRANT USAGE, MONITOR ON COMPUTE POOL airflow_workers to ROLE airflow_admin_rl;

--########################## create Image Registry and YAML Stage ##########################
USE ROLE airflow_admin_rl;
USE DATABASE airflow_db;
USE WAREHOUSE airflow_wh;

CREATE SCHEMA IF NOT EXISTS airflow_schema;
USE SCHEMA airflow_db.airflow_schema;
CREATE IMAGE REPOSITORY IF NOT EXISTS airflow_repository;
CREATE STAGE IF NOT EXISTS service_spec DIRECTORY = ( ENABLE = true );

--########################## create secrete objects ##########################
USE ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;

CREATE SECRET airflow_fernet_key
    TYPE = password
    username = 'airflow_fernet_key'
    password = '########'
    ;

CREATE SECRET airflow_postgres_pwd
    TYPE = password
    username = 'postgres'
    password = '########'
    ;

CREATE SECRET airflow_redis_pwd
    TYPE = password
    username = 'airflow'
    password = '########'
    ;
--########################## create snowGIT Integration ##########################
USE ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;

--create a secret object to store Github personal access token
CREATE OR REPLACE SECRET git_airflow_secret
  TYPE = password
  USERNAME = '<username>'
  PASSWORD = 'patghp_token'
  ;

GRANT USAGE ON SECRET git_airflow_secret  TO ROLE accountadmin;

USE ROLE accountadmin;
CREATE OR REPLACE API INTEGRATION airflow_git_api_integration
  API_PROVIDER = git_https_api
  API_ALLOWED_PREFIXES = ('https://github.com/my-account')
  ALLOWED_AUTHENTICATION_SECRETS = (airflow_db.airflow_schema.git_airflow_secret)
  ENABLED = TRUE;

GRANT USAGE ON INTEGRATION airflow_git_api_integration TO ROLE airflow_admin_rl;

USE ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;

CREATE OR REPLACE GIT REPOSITORY airflow_dags_repo
  API_INTEGRATION = airflow_git_api_integration
  GIT_CREDENTIALS = airflow_db.airflow_schema.git_airflow_secret
  ORIGIN = 'https://github.com/my-account/repo.git';

SHOW GIT BRANCHES IN airflow_dags_repo;

--we will mount this stage as a volume to the Airflow service. git-sync container copies the DAGs to this stage.
CREATE STAGE IF NOT EXISTS airflow_dags ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

--we will mount this stage as a volume to the Airflow service where it will store task logs. 
CREATE STAGE IF NOT EXISTS airflow_logs ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');


--########################## create external access Integration ##########################
USE ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;

CREATE OR REPLACE NETWORK RULE airflow_spcs_egress_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = (
  'my-account.snowflakecomputing.com',
  'api.slack.com',
  'hooks.slack.com',
  'events.pagerduty.com');

GRANT USAGE ON NETWORK RULE airflow_spcs_egress_rule TO ROLE accountadmin;

USE ROLE accountadmin;
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION airflow_spcs_egress_access_integration
  ALLOWED_NETWORK_RULES = (airflow_db.airflow_schema.airflow_spcs_egress_rule)
  ENABLED = true;

GRANT USAGE ON  INTEGRATION airflow_spcs_egress_access_integration to role airflow_admin_rl;


--######### Upload service specification files to YAML stage ###########
use role airflow_admin_rl;
put file://~/airflow_spcs/redis/redis.yaml @airflow_db.airflow_schema.service_spec AUTO_COMPRESS=FALSE OVERWRITE=TRUE; 
put file://~/airflow_spcs/postgres/postgres.yaml @airflow_db.airflow_schema.service_spec AUTO_COMPRESS=FALSE OVERWRITE=TRUE; 
put file://~/airflow_spcs/airflow/airflow_server.yaml @airflow_db.airflow_schema.service_spec AUTO_COMPRESS=FALSE OVERWRITE=TRUE; 
put file://~/airflow_spcs/airflow/airflow_worker.yaml @airflow_db.airflow_schema.service_spec AUTO_COMPRESS=FALSE OVERWRITE=TRUE; 
--########################## create services ##########################
USE  ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;

--creates Postgres service
CREATE SERVICE postgres_service
  IN COMPUTE POOL postgres_redis
  FROM @service_spec
  SPECIFICATION_FILE='postgres.yaml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1;

--check status of the service
SELECT SYSTEM$GET_SERVICE_STATUS('postgres_service');
--check container logs of the service
CALL SYSTEM$GET_SERVICE_LOGS('postgres_service', '0','postgres');

--creates Redis service
CREATE SERVICE redis_service
  IN COMPUTE POOL postgres_redis
  FROM @service_spec
  SPECIFICATION_FILE='redis.yaml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1;

--check status of the service
SELECT SYSTEM$GET_SERVICE_STATUS('redis_service');
--check container logs of the service
CALL SYSTEM$GET_SERVICE_LOGS('redis_service', '0','redis');

--creates Airflow webserver, Scheduler and Git-Sync services
CREATE SERVICE airflow_service
  IN COMPUTE POOL airflow_server
  FROM @service_spec
  SPECIFICATION_FILE='airflow_server.yaml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1
  EXTERNAL_ACCESS_INTEGRATIONS = (airflow_spcs_egress_access_integration);

--check status of the service
SELECT SYSTEM$GET_SERVICE_STATUS('airflow_service');
--check container logs of the service
CALL SYSTEM$GET_SERVICE_LOGS('airflow_service', '0','webserver');

CALL SYSTEM$GET_SERVICE_LOGS('airflow_service', '0','git-sync');
--creates Airflow Workers service;
CREATE SERVICE airflow_worker
  IN COMPUTE POOL airflow_workers
  FROM @service_spec
  SPECIFICATION_FILE='airflow_worker.yaml'
  MIN_INSTANCES=1
  MAX_INSTANCES=2
  EXTERNAL_ACCESS_INTEGRATIONS = (airflow_spcs_egress_access_integration);

--check status of the service
SELECT SYSTEM$GET_SERVICE_STATUS('airflow_worker');
--check container logs of the service
CALL SYSTEM$GET_SERVICE_LOGS('airflow_worker', '0','worker');
CALL SYSTEM$GET_SERVICE_LOGS('airflow_worker', '1','worker');


USE  ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;
--########################## Altering service ##########################
ALTER SERVICE airflow_worker FROM @service_spec SPECIFICATION_FILE='airflow_worker.yaml';
describe service postgres_services; 

--########################## Get Service End point ##########################

show endpoints in service airflow_service;

--########################## Grant access to service End point ##########################

USE  ROLE airflow_admin_rl;
USE SCHEMA airflow_db.airflow_schema;
GRANT SERVICE ROLE airflow_service!ALL_ENDPOINTS_USAGE TO ROLE <role-name>;

--########################## Create a Snapshot ##########################

CREATE SNAPSHOT postres_data_snapshot
  FROM SERVICE postgres_services
  VOLUME "pgdata"
  INSTANCE 0
  COMMENT='new snapshot';

SHOW SNAPSHOTS;
describe snapshot postres_data_snapshot;
--########################## clean up ##########################
USE ROLE airflow_admin_rl;
ALTER COMPUTE POOL postgres_redis STOP ALL;
ALTER COMPUTE POOL airflow_server STOP ALL;
ALTER COMPUTE POOL airflow_workers STOP ALL;

DROP COMPUTE POOL postgres_redis;
DROP COMPUTE POOL airflow_server;
DROP COMPUTE POOL airflow_workers;

DROP IMAGE REPOSITORY airflow_repository;
DROP GIT REPOSITORY airflow_dags_repo;
DROP STAGE service_spec;
DROP STAGE airflow_logs;
DROP STAGE airflow_dags;

--#########################################################################

