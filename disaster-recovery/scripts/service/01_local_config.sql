/*
 * service/01_local_config.sql
 * Creates secrets and external access integration. One-time setup needed in 
 * BOTH primary and secondary before deploying the service. These objects are NOT 
 * replicated - each target has its own config.
 */

CREATE DATABASE IF NOT EXISTS {{ local.database }};
CREATE SCHEMA IF NOT EXISTS {{ local.database }}.{{ local.schema }};

USE DATABASE {{ local.database }};
USE SCHEMA {{ local.schema }};

-- Region-specific API
CREATE OR REPLACE SECRET API_KEY_SECRET
    TYPE = GENERIC_STRING
    SECRET_STRING = '{{ secrets.api_key }}'
    COMMENT = 'API key for {{ external.api_host }}';

CREATE OR REPLACE NETWORK RULE EXTERNAL_API_RULE
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('{{ external.api_host }}:443')
    COMMENT = 'Allow egress to {{ external.api_host }}';

-- Region-specific S3 bucket
CREATE OR REPLACE SECRET AWS_ACCESS_KEY_ID
    TYPE = GENERIC_STRING
    SECRET_STRING = '{{ secrets.aws_access_key_id }}'
    COMMENT = 'AWS access key ID for S3 bucket {{ external.s3_bucket }}';

CREATE OR REPLACE SECRET AWS_SECRET_ACCESS_KEY
    TYPE = GENERIC_STRING
    SECRET_STRING = '{{ secrets.aws_secret_access_key }}'
    COMMENT = 'AWS secret access key for S3 bucket {{ external.s3_bucket }}';

CREATE OR REPLACE NETWORK RULE S3_NETWORK_RULE
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('{{ external.s3_host }}:443')
    COMMENT = 'Allow egress to S3 {{ external.s3_bucket }}';

-- External access for both
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION EXTERNAL_ACCESS
    ALLOWED_NETWORK_RULES = (
        {{ local.database }}.{{ local.schema }}.EXTERNAL_API_RULE,
        {{ local.database }}.{{ local.schema }}.S3_NETWORK_RULE
    )
    ALLOWED_AUTHENTICATION_SECRETS = (
        {{ local.database }}.{{ local.schema }}.API_KEY_SECRET,
        {{ local.database }}.{{ local.schema }}.AWS_ACCESS_KEY_ID,
        {{ local.database }}.{{ local.schema }}.AWS_SECRET_ACCESS_KEY
    )
    ENABLED = TRUE
    COMMENT = 'External access for API and S3';

-- Verify
SHOW SECRETS IN SCHEMA {{ local.database }}.{{ local.schema }};
SHOW NETWORK RULES IN SCHEMA {{ local.database }}.{{ local.schema }};
SHOW EXTERNAL ACCESS INTEGRATIONS LIKE 'EXTERNAL_ACCESS%';
