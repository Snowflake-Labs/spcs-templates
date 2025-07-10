-- Run these first
-- https://github.com/Snowflake-Labs/sfguide-getting-started-with-cortex-analyst/blob/main/create_snowflake_objects.sql
-- https://github.com/Snowflake-Labs/sfguide-getting-started-with-cortex-analyst/blob/main/load_data.sql
-- https://github.com/Snowflake-Labs/sfguide-getting-started-with-cortex-analyst/blob/main/cortex_search_create.sql


USE ROLE accountadmin;
CREATE ROLE service_user_role;

CREATE DATABASE IF NOT EXISTS app_db;
GRANT OWNERSHIP ON DATABASE app_db TO ROLE service_user_role COPY CURRENT GRANTS;

GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO ROLE service_user_role;
CREATE COMPUTE POOL app_compute_pool
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = CPU_XS
  AUTO_SUSPEND_SECS = 3600;

GRANT USAGE, MONITOR ON COMPUTE POOL app_compute_pool TO ROLE service_user_role;
GRANT OWNERSHIP ON SCHEMA app_db.public TO ROLE service_user_role;
GRANT CREATE NETWORK RULE ON SCHEMA app_db.public TO ROLE accountadmin;  

CREATE OR REPLACE NETWORK RULE app_db.public.dependencies_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('pypi.python.org', 'pypi.org', 'cdn.pypi.org','pythonhosted.org', 'files.pythonhosted.org', 'github.com', 'githubusercontent.com');

CREATE EXTERNAL ACCESS INTEGRATION dependencies_access_integration
  ALLOWED_NETWORK_RULES = (app_db.public.dependencies_network_rule)
  ENABLED = true;

GRANT USAGE ON INTEGRATION dependencies_access_integration TO ROLE service_user_role;

-- Grant restricted caller privileges to service_user_role 
GRANT CALLER USAGE ON DATABASE cortex_analyst_demo TO ROLE service_user_role;
GRANT INHERITED CALLER USAGE ON ALL SCHEMAS IN DATABASE cortex_analyst_demo TO ROLE service_user_role;
GRANT INHERITED CALLER USAGE,READ ON ALL STAGES IN SCHEMA cortex_analyst_demo.revenue_timeseries TO ROLE service_user_role;
GRANT INHERITED CALLER SELECT ON ALL TABLES IN DATABASE cortex_analyst_demo TO ROLE service_user_role;
GRANT CALLER USAGE ON CORTEX SEARCH SERVICE cortex_analyst_demo.revenue_timeseries.product_line_search_service TO ROLE service_user_role;
GRANT CALLER USAGE ON DATABASE snowflake TO ROLE service_user_role;
GRANT INHERITED CALLER USAGE ON ALL SCHEMAS IN DATABASE snowflake TO ROLE service_user_role;
GRANT INHERITED CALLER USAGE ON ALL FUNCTIONS IN DATABASE snowflake TO ROLE service_user_role;


USE ROLE service_user_role;
USE DATABASE app_db;

CREATE IMAGE REPOSITORY IF NOT EXISTS repo;
SHOW IMAGE REPOSITORIES IN SCHEMA app_db.public;
SHOW IMAGES IN IMAGE REPOSITORY app_db.public.repo;

CREATE SERVICE analyst_ui
  IN COMPUTE POOL app_compute_pool
  FROM SPECIFICATION $$
    spec:
      containers:
      - name: ui
        image: <registry>/<repo>/<image>:<version>
        readinessProbe:
          port: 8080
          path: /healthcheck
      endpoints:
      - name: chat
        port: 8080
        public: true
    capabilities:
      securityContext:
        executeAsCaller: true
      $$
   MIN_INSTANCES=1
   MAX_INSTANCES=1;
