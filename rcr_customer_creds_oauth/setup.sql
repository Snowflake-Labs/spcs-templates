-- rcr_customer_creds_oauth : setup.sql
-- Complete setup in one script.  Run as ACCOUNTADMIN.
--
-- Two pauses are required — marked with ▶▶ STOP — because each depends on
-- information that only exists after the previous phase completes:
--
--   Phase 1  Create all objects including the service.
--            → copy the endpoint URL from SHOW ENDPOINTS
--   Phase 2  Create the OAuth integration using that URL.
--            → copy OAUTH_CLIENT_ID + OAUTH_CLIENT_SECRET from the result
--   Phase 3  Write real credentials into the secret, restart the service.
--
-- What this demonstrates
-- ──────────────────────
-- service_owner_role has NO SELECT on finance_data.  The service cannot query
-- the table on its own.  A user who logs in via Snowflake OAuth (interactive
-- browser flow) and has FINANCE_ROLE can query it — the service runs the query
-- on their behalf using their access token.

USE ROLE ACCOUNTADMIN;

-- ── Names — edit here if you want different identifiers ───────────────────────
SET DB                   = 'rcr_oauth_db';
SET SCH                  = 'rcr_oauth';
SET WAREHOUSE            = 'rcr_oauth_wh';
SET COMPUTE_POOL         = 'rcr_oauth_pool';
SET SERVICE_OWNER_ROLE   = 'rcr_oauth_service_owner';
SET FINANCE_ROLE         = 'rcr_oauth_finance';
SET NETWORK_RULE         = 'rcr_oauth_pool_rule';
SET NETWORK_POLICY       = 'rcr_oauth_policy';
SET SECURITY_INTEGRATION = 'rcr_oauth_integration';

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 1 — Infrastructure, table, and service
-- ══════════════════════════════════════════════════════════════════════════════

-- ── Roles ─────────────────────────────────────────────────────────────────────
CREATE ROLE IF NOT EXISTS IDENTIFIER($SERVICE_OWNER_ROLE);
CREATE ROLE IF NOT EXISTS IDENTIFIER($FINANCE_ROLE);

-- ── Database / schema ─────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS IDENTIFIER($DB);
USE DATABASE IDENTIFIER($DB);
CREATE SCHEMA IF NOT EXISTS IDENTIFIER($SCH);

-- ── Warehouse + compute pool ──────────────────────────────────────────────────
CREATE WAREHOUSE IF NOT EXISTS IDENTIFIER($WAREHOUSE)
    WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;

CREATE COMPUTE POOL IF NOT EXISTS IDENTIFIER($COMPUTE_POOL)
    MIN_NODES = 1 MAX_NODES = 1 INSTANCE_FAMILY = CPU_X64_XS AUTO_SUSPEND_SECS = 3600;

-- ── Finance table ─────────────────────────────────────────────────────────────
-- SELECT is granted to finance_role only.
-- service_owner_role intentionally receives no SELECT — that is the point.
USE SCHEMA IDENTIFIER($SCH);

CREATE OR REPLACE TABLE finance_data (
    id     NUMBER AUTOINCREMENT,
    region STRING,
    metric STRING,
    amount NUMBER(18,2)
);

INSERT INTO finance_data (region, metric, amount) VALUES
    ('NA',   'Q1 revenue',  1820000.00),
    ('EMEA', 'Q1 revenue',   955000.00),
    ('APAC', 'Q1 revenue',   612300.00),
    ('NA',   'Q1 expenses',  740400.00),
    ('EMEA', 'Q1 expenses',  318900.00);

GRANT SELECT ON TABLE finance_data TO ROLE IDENTIFIER($FINANCE_ROLE);

-- ── Grants to service_owner_role ──────────────────────────────────────────────
GRANT USAGE ON DATABASE     IDENTIFIER($DB)          TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
GRANT USAGE ON SCHEMA       IDENTIFIER($SCH)         TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
GRANT USAGE ON WAREHOUSE    IDENTIFIER($WAREHOUSE)   TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
GRANT USAGE ON COMPUTE POOL IDENTIFIER($COMPUTE_POOL) TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);

-- CALLER grants scope what the service may do on behalf of the OAuth user.
-- Effective privilege = user's grants ∩ service's CALLER grants.
-- service_owner_role still cannot access finance_data directly.
GRANT CALLER USAGE  ON DATABASE  IDENTIFIER($DB)        TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
GRANT CALLER USAGE  ON SCHEMA    IDENTIFIER($SCH)       TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
GRANT CALLER USAGE  ON WAREHOUSE IDENTIFIER($WAREHOUSE) TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
GRANT CALLER SELECT ON TABLE     finance_data           TO ROLE IDENTIFIER($SERVICE_OWNER_ROLE);

-- ── Network rule + policy ─────────────────────────────────────────────────────
-- Allows Snowflake to accept auth requests originating from the compute pool
-- when enableCustomCredentials is set to true.
CREATE NETWORK RULE IF NOT EXISTS IDENTIFIER($NETWORK_RULE)
    TYPE = COMPUTE_POOL MODE = INGRESS VALUE_LIST = ($COMPUTE_POOL);

CREATE NETWORK POLICY IF NOT EXISTS IDENTIFIER($NETWORK_POLICY)
    ALLOWED_NETWORK_RULE_LIST = ($NETWORK_RULE);

-- ── Grant your user FINANCE_ROLE ─────────────────────────────────────────────
-- Without this you will get an access-denied error after OAuth login.
-- Uncomment and replace YOUR_SNOWFLAKE_USERNAME:
-- GRANT ROLE IDENTIFIER($FINANCE_ROLE) TO USER <YOUR_SNOWFLAKE_USERNAME>;

-- ── Image repository ──────────────────────────────────────────────────────────
USE ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
USE DATABASE IDENTIFIER($DB);
USE SCHEMA   IDENTIFIER($SCH);

CREATE IMAGE REPOSITORY IF NOT EXISTS repo;
SHOW IMAGE REPOSITORIES;  -- copy the repository_url for the docker push step

-- ── Placeholder OAuth secret ──────────────────────────────────────────────────
-- Real credentials are written in Phase 3.  Creating the secret here means the
-- service spec only needs to be written once (no ALTER SERVICE with a full spec
-- repeat later).
CREATE SECRET IF NOT EXISTS oauth_client
    TYPE     = password
    USERNAME = 'not-yet-configured'
    PASSWORD = 'not-yet-configured';

-- ── Service ───────────────────────────────────────────────────────────────────
-- Replace <repository_url> with the value from SHOW IMAGE REPOSITORIES above.
-- Everything else is controlled by the mounted secret and env vars.
CREATE SERVICE rcr_oauth_app
    IN COMPUTE POOL IDENTIFIER($COMPUTE_POOL)
    FROM SPECIFICATION $$
spec:
  containers:
    - name: ui
      image: <repository_url>/rcr-customer-creds-oauth:dev
      env:
        SERVER_PORT: "8080"
        DATABASE: RCR_OAUTH_DB
        SCHEMA: RCR_OAUTH
        WAREHOUSE: RCR_OAUTH_WH
        TABLE: FINANCE_DATA
      secrets:
        - snowflakeSecret: rcr_oauth_db.rcr_oauth.oauth_client
          secretKeyRef: username
          envVarName: OAUTH_CLIENT_ID
        - snowflakeSecret: rcr_oauth_db.rcr_oauth.oauth_client
          secretKeyRef: password
          envVarName: OAUTH_CLIENT_SECRET
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

SHOW ENDPOINTS IN SERVICE rcr_oauth_app;

-- ══════════════════════════════════════════════════════════════════════════════
-- ▶▶  STOP.  Copy the ingress_url from SHOW ENDPOINTS above.
--     Set ENDPOINT_URL below, then run Phase 2.
-- ══════════════════════════════════════════════════════════════════════════════

SET ENDPOINT_URL = '<endpoint_url>';  -- ← FILL IN  (e.g. abc123.snowflakecomputing.app)
SET REDIRECT_URI = 'https://' || $ENDPOINT_URL || '/callback';

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 2 — OAuth integration
-- ══════════════════════════════════════════════════════════════════════════════

USE ROLE ACCOUNTADMIN;

-- OAUTH_REDIRECT_URI must exactly match what the app sends.
-- The app reads the Host header on every /login request and constructs
-- https://<host>/callback, so this always equals https://<endpoint>/callback.
-- Note: OAUTH_REDIRECT_URI is required DDL syntax but is only followed by the
-- user's browser during the authorization-code redirect; the container never
-- calls it directly.
CREATE SECURITY INTEGRATION IF NOT EXISTS IDENTIFIER($SECURITY_INTEGRATION)
    TYPE = OAUTH
    OAUTH_CLIENT = CUSTOM
    OAUTH_CLIENT_TYPE = CONFIDENTIAL
    OAUTH_REDIRECT_URI = $REDIRECT_URI
    OAUTH_ISSUE_REFRESH_TOKENS = FALSE
    ENABLED = TRUE;

-- Attach the network policy to the integration, not to individual users.
-- Since any Snowflake user can log in via OAuth here (the set is not fixed in
-- advance), user-level attachment is impractical.  Integration-level attachment
-- restricts which network locations may call POST /oauth/token to exchange
-- authorization codes for tokens — which is exactly the call the container makes
-- from inside the compute pool.
ALTER SECURITY INTEGRATION IDENTIFIER($SECURITY_INTEGRATION)
    SET NETWORK_POLICY = $NETWORK_POLICY;

-- Retrieve the client credentials for the integration just created.
SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS($SECURITY_INTEGRATION);

-- ══════════════════════════════════════════════════════════════════════════════
-- ▶▶  STOP.  From the result above, copy OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET.
--     Set them below, then run Phase 3.
-- ══════════════════════════════════════════════════════════════════════════════

SET OAUTH_CLIENT_ID_VAL     = '<OAUTH_CLIENT_ID>';      -- ← FILL IN
SET OAUTH_CLIENT_SECRET_VAL = '<OAUTH_CLIENT_SECRET>';  -- ← FILL IN

-- ══════════════════════════════════════════════════════════════════════════════
-- PHASE 3 — Write real credentials into the secret, restart service
-- ══════════════════════════════════════════════════════════════════════════════

USE ROLE IDENTIFIER($SERVICE_OWNER_ROLE);
USE DATABASE IDENTIFIER($DB);
USE SCHEMA   IDENTIFIER($SCH);

-- Replace the placeholder values with the real OAuth client credentials.
CREATE OR REPLACE SECRET oauth_client
    TYPE     = password
    USERNAME = $OAUTH_CLIENT_ID_VAL
    PASSWORD = $OAUTH_CLIENT_SECRET_VAL;

-- Secrets are injected as env vars at container start time, so a restart is
-- required to pick up the new values.
ALTER SERVICE rcr_oauth_app SUSPEND;
ALTER SERVICE rcr_oauth_app RESUME;

SHOW ENDPOINTS IN SERVICE rcr_oauth_app;
CALL SYSTEM$GET_SERVICE_STATUS('rcr_oauth_app');
