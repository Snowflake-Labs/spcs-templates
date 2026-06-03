-- rcr_customer_creds : create_service.sql
-- Creates the SPCS service that runs the Gradio UI. Run after setup.sql and after
-- you have built and pushed your image. Replace <repository_url> with the value
-- shown by SHOW IMAGE REPOSITORIES from setup.sql.
--
-- Note: the YAML inside $$ ... $$ is literal -- Snowflake does NOT expand the
-- SET variables below into the spec. If you change the database/schema/secret
-- names above, also edit the matching `snowflakeSecret:` and env values inline
-- in the spec below.

USE ROLE ACCOUNTADMIN;

-- Keep these in sync with setup.sql.
SET DB                  = 'app_db';
SET SCH                 = 'rcr';
SET COMPUTE_POOL        = 'app_compute_pool';
SET SERVICE_OWNER_ROLE  = 'service_owner_role';

USE ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
USE DATABASE IDENTIFIER($DB);
USE SCHEMA   IDENTIFIER($SCH);

CREATE SERVICE rcr_customer_creds_app
    IN COMPUTE POOL IDENTIFIER($COMPUTE_POOL)
    FROM SPECIFICATION $$
spec:
  containers:
    - name: ui
      image: <repository_url>/rcr-customer-creds:dev
      env:
        SERVER_PORT: "8080"
        DATABASE: APP_DB
        SCHEMA: RCR
        WAREHOUSE: APP_WH
        TABLE: TEAM_DATA
        FINANCE_ROLE: FINANCE_ROLE
        MARKETING_ROLE: MARKETING_ROLE
      secrets:
        - snowflakeSecret: app_db.rcr.finance_pat_secret
          secretKeyRef: username
          envVarName: FINANCE_USER
        - snowflakeSecret: app_db.rcr.finance_pat_secret
          secretKeyRef: password
          envVarName: FINANCE_PAT
        - snowflakeSecret: app_db.rcr.marketing_pat_secret
          secretKeyRef: username
          envVarName: MARKETING_USER
        - snowflakeSecret: app_db.rcr.marketing_pat_secret
          secretKeyRef: password
          envVarName: MARKETING_PAT
      readinessProbe:
        port: 8080
        path: /
  endpoints:
    - name: app
      port: 8080
      public: true
capabilities:
  securityContext:
    enableCustomCredentials: true
$$
    MIN_INSTANCES = 1
    MAX_INSTANCES = 1;

SHOW ENDPOINTS IN SERVICE rcr_customer_creds_app;
CALL SYSTEM$GET_SERVICE_STATUS('rcr_customer_creds_app');
