
USE ROLE ACCOUNTADMIN;
USE AIVANOUDB.PUBLIC;

CREATE OR REPLACE NETWORK RULE EMBEDDINGS_RULE
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('0.0.0.0:443','0.0.0.0:80');


CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION hf_access_eai
  ALLOWED_NETWORK_RULES = (EMBEDDINGS_RULE)
  ENABLED = true;

GRANT USAGE ON INTEGRATION HF_EAI TO ROLE SYSADMIN;
USE ROLE SYSADMIN;