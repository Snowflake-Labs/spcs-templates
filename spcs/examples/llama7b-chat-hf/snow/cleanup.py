#!/usr/bin/env python3

import click

from logger import log
from snow import get_snowflake_connection, SnowHandler

IMG_TAG: str = "llm-base"
BASE_IMAGE: str = f"public.ecr.aws/h9k5u5w6/aivanou-pub01:{IMG_TAG}"
PROJECT_NAME: str = "llama2-hf-chat"
COMPUTE_POOL_INSTANCE: str = "GPU_3"


@click.command()
@click.option("--account", required=True, type=str, help="Snowflake account")
@click.option("--username", required=True, type=str, help="Snowflake username")
@click.option("--password", required=True, type=str, help="Snowflake password")
@click.option("--db", required=True, type=str, help="Snowflake database")
@click.option("--schema", required=True, type=str, help="Snowflake schema")
@click.option("--compute-pool", required=True, type=str, help="SPCS Compute Pool")
@click.option("--service-name", required=True, type=str, help="SPCS Service Name")
def cleanup(account: str, username: str, password: str,
            db: str, schema: str, compute_pool: str, service_name: str) -> None:
    log.info("===============================")
    log.info("Account: %s", account)
    log.info("Username: %s", username)
    log.info("Password: %s", password)
    log.info("Database: %s", db)
    log.info("Schema: %s", schema)
    log.info("Compute Pool: %s", compute_pool)
    log.info("Service Name: %s", service_name)
    log.info("===============================")

    with get_snowflake_connection(account, username, password, db, schema) as ctx:
        handler = SnowHandler(ctx)
        log.info("Dropping service")
        handler.drop_service(db, schema, service_name)
        log.info("Dropping compute pool")
        handler.drop_compute_pool(compute_pool)
