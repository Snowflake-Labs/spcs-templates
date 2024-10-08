


ALTER COMPUTE POOL IF EXISTS EMB_COMPUTE_POOL STOP ALL;
DROP COMPUTE POOL IF EXISTS EMB_COMPUTE_POOL;

CREATE COMPUTE POOL EMB_COMPUTE_POOL
  MIN_NODES=1
  MAX_NODES=1
  instance_family=GPU_NV_S
  auto_suspend_secs = 200;



CREATE DATABASE IF NOT EXISTS AIVANOUDB;
USE DATABASE AIVANOUDB;
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

CREATE OR REPLACE FILE FORMAT embedding_parquet_format TYPE = parquet;
CREATE OR REPLACE STAGE EMBED_STAGE FILE_FORMAT = embedding_parquet_format;

CREATE IMAGE REPOSITORY IF NOT EXISTS embeddings_repo;