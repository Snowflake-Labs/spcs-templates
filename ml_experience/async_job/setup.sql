USE ROLE CONTAINER_USER_ROLE;
USE DATABASE TEXT_ANALYSIS_DB;
USE SCHEMA PUBLIC;

-- Create a warehouse
CREATE OR REPLACE WAREHOUSE XSMALL WITH
  WAREHOUSE_SIZE='X-SMALL';

-- Create compute pool
CREATE COMPUTE POOL IF NOT EXISTS CPU_S
  MIN_NODES = 1
  MAX_NODES = 4
  INSTANCE_FAMILY = CPU_X64_S
  AUTO_SUSPEND_SECS = 300
  AUTO_RESUME = TRUE

CREATE OR REPLACE IMAGE REPOSITORY IMAGE_REPO;

-- Image build and publish => run on CLI

-- docker build --platform=linux/amd64 -t local/spcs-text-analysis:latest .
-- docker tag local/spcs-text-analysis:latest REGISTRY/REPO/TEXT_ANALYSIS_IMAGE:TEXT_ANALYSIS_IMAGE_VERSION
-- docker push REGISTRY/REPO/TEXT_ANALYSIS_IMAGE:TEXT_ANALYSIS_IMAGE_VERSION

-- Execute syncrhonous summarization task
EXECUTE JOB SERVICE IN COMPUTE POOL CPU_S
  NAME=summarization_job_sync
  FROM SPECIFICATION $$
  spec:
      container:
      - name: main
        image: REGISTRY/REPO/TEXT_ANALYSIS_IMAGE:TEXT_ANALYSIS_IMAGE_VERSION
        env:
          SNOWFLAKE_WAREHOUSE: XSMALL
        args:
        - "--source_table=google_reviews.google_reviews.sample_reviews"
        - "--source_id_column=REVIEW_HASH"
        - "--source_value_column=REVIEW_TEXT"
        - "--result_table=results"
 $$;

 -- Execute asynchronous summarization and sentiment analysis tasks
EXECUTE JOB SERVICE IN COMPUTE POOL CPU_S
  NAME=summarization_job_async
  ASYNC=TRUE
  FROM SPECIFICATION $$
  spec:
      container:
      - name: main
        image: REGISTRY/REPO/TEXT_ANALYSIS_IMAGE:TEXT_ANALYSIS_IMAGE_VERSION
        env:
          SNOWFLAKE_WAREHOUSE: XSMALL
        args:
        - "--source_table=google_reviews.google_reviews.sample_reviews"
        - "--source_id_column=REVIEW_HASH"
        - "--source_value_column=REVIEW_TEXT"
        - "--result_table=results"
 $$;

EXECUTE JOB SERVICE IN COMPUTE POOL CPU_S
  NAME=sentiment_job_async
  ASYNC=TRUE
  FROM SPECIFICATION $$
  spec:
      container:
      - name: main
        image: REGISTRY/REPO/TEXT_ANALYSIS_IMAGE:TEXT_ANALYSIS_IMAGE_VERSION
        env:
          SNOWFLAKE_WAREHOUSE: XSMALL
        args:
        - "--task=sentiment"
        - "--source_table=google_reviews.google_reviews.sample_reviews"
        - "--source_id_column=REVIEW_HASH"
        - "--source_value_column=REVIEW_TEXT"
        - "--result_table=results"
 $$;
  SELECT SYSTEM$WAIT_FOR_SERVICES(1200, 'summarization_job_async','sentiment_job_async')

-- (Optional: CLI debug commands)
--  snow spcs service logs summarization_job_async --container-name main --instance-id 0