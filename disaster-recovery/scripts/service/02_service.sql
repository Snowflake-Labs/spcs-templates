/*
 * service/02_service.sql
 * Creates or updates the SPCS service. Runs on BOTH primary and secondary 
 * and can safely be re-run as part of deployment pipeline. Service is manually
 * created in each deployment, not replicated, to allow for regional differences.
 */

-- Drop existing service if any (CREATE OR REPLACE not supported for services)
DROP SERVICE IF EXISTS {{ local.database }}.{{ local.schema }}.{{ service.name }};

-- Create the service in local database, using image from replicated repo
CREATE SERVICE {{ local.database }}.{{ local.schema }}.{{ service.name }}
    IN COMPUTE POOL {{ compute_pool.name }}
    MIN_INSTANCES = {{ service.min_instances }}
    MAX_INSTANCES = {{ service.max_instances }}
    EXTERNAL_ACCESS_INTEGRATIONS = (EXTERNAL_ACCESS)
    FROM SPECIFICATION $$
    spec:
      containers:
        - name: app
          image: {{ service.image }}
          env:
            API_HOST: {{ external.api_host }}
            API_ENDPOINT: {{ external.api_endpoint }}
            S3_BUCKET: {{ external.s3_bucket }}
            S3_HOST: {{ external.s3_host }}
            AWS_REGION: {{ external.aws_region }}
          secrets:
            - snowflakeSecret: {{ local.database }}.{{ local.schema }}.API_KEY_SECRET
              secretKeyRef: secret_string
              envVarName: API_KEY
            - snowflakeSecret: {{ local.database }}.{{ local.schema }}.AWS_ACCESS_KEY_ID
              secretKeyRef: secret_string
              envVarName: AWS_ACCESS_KEY_ID
            - snowflakeSecret: {{ local.database }}.{{ local.schema }}.AWS_SECRET_ACCESS_KEY
              secretKeyRef: secret_string
              envVarName: AWS_SECRET_ACCESS_KEY
      endpoints:
        - name: app
          port: 80
          public: true
    $$;

-- Secondary: suspend service until failover
{% if service.suspended | default(false) %}
ALTER SERVICE {{ local.database }}.{{ local.schema }}.{{ service.name }} SUSPEND;
{% endif %}

-- Verify service status
SHOW SERVICES LIKE '{{ service.name }}';
SELECT SYSTEM$GET_SERVICE_STATUS('{{ local.database }}.{{ local.schema }}.{{ service.name }}');

-- Get the public ingress URL
SHOW ENDPOINTS IN SERVICE {{ local.database }}.{{ local.schema }}.{{ service.name }};
