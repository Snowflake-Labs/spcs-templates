-- Create test database
CREATE DATABASE IF NOT EXISTS TESTDB;
USE DATABASE TESTDB;
-- Create schema
CREATE SCHEMA IF NOT EXISTS TESTSCHEMA;
USE SCHEMA TESTSCHEMA;
-- Create image repo
CREATE IMAGE REPOSITORY TESTREPO;
-- Use show image repositories to retrieve repo url:
SHOW IMAGE REPOSITORIES;
-- Create stage for storing metrics
CREATE STAGE METRICS ENCRYPTION = (type = 'SNOWFLAKE_SSE');
-- Create service
