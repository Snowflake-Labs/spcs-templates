
USE ROLE ACCOUNTADMIN;
USE AIVANOUDB.PUBLIC;
USE ROLE SYSADMIN;

CREATE OR REPLACE STAGE demo_stage_v2  encryption = (type = 'SNOWFLAKE_SSE');