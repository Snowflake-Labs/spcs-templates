# Snowpark Container Services(SPCS) - service functions examples

The project contains examples of implementing model inference SPCS service that processes data from Snowflake table.
The service implements two endpoints:

* `POST /classify_texts` CPU text emotion classification
* `POST /extract_embeddings` GPU extracting text embeddings

## Prerequisites

* Make sure that you have docker installed, at least `27.0.3` version. Docker
  Install: https://docs.docker.com/engine/install/
* Make sure that you created the following Snowflake resources:
    * User
    * Role
    * Warehouse
    * Database
    * Schema

## Setup

The project setup does the following actions:

* Setup of necessary permissions to run the model inference
* Setup of Compute Pool, Image repository, Image and Service.
* Create a dummy table that will be used for testing
* Run service function on test data


1. Create Database, Table and Warehouse.
2. Modify `sql/permissions.sql` to use your own ROLE, USER, Database, Table and Warehouse.
3. Make sure that user contains permissions specified in `sql/permissions.sql` file.
4. Modify `config.toml` and fill in `<<YOUR_*>>` fields
5. Run `pip install -r requirements_setup.txt`
6. Make sure that you have `docker` installed
7. Run `python ./src/setup.py --password '<<YOUR_PASSWORD>>` to start a setup
