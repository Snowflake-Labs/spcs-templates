#!/usr/bin/env python3

from pathlib import Path

import click

from logger import log
from snow import get_snowflake_connection, SnowHandler
from utils import get_hf_token, generate_spcs_spec, upload_image

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
@click.option("--repo-name", required=True, type=str, help="SPCS Repository name")
@click.option("--stage-name", required=True, type=str, help="Snowflake Stage name")
@click.option("--hf-token", required=False, type=str, help="Huggingface token")
def run_setup(account: str, username: str, password: str,
              db: str, schema: str, compute_pool: str, service_name: str,
              repo_name: str, stage_name: str, hf_token: str) -> None:
    log.info("===============================")
    log.info("Account: %s", account)
    log.info("Username: %s", username)
    log.info("Password: %s", password)
    log.info("Database: %s", db)
    log.info("Schema: %s", schema)
    log.info("Compute Pool: %s", compute_pool)
    log.info("Service Name: %s", service_name)
    log.info("Repository Name: %s", repo_name)
    log.info("Stage Name: %s", stage_name)
    log.info("HF Token: %s", hf_token)
    log.info("===============================")

    with get_snowflake_connection(account, username, password, db, schema) as ctx:
        handler = SnowHandler(ctx)
        log.info("Checking database")
        handler.create_database(db)
        log.info("Checking schema")
        handler.create_schema(db, schema)
        log.info(f"Creating compute pool: {compute_pool}")
        handler.create_compute_pool(compute_pool, "GPU_3")
        log.info("Creating repository")
        handler.create_repository(db, schema, repo_name)
        log.info("Getting repository")
        repo = handler.get_repository(db, schema, repo_name)
        if repo is None:
            raise Exception(f"Repository: {db}.{schema}.{repo_name} not found")
        log.info(f"Uploading image to: {repo.repository_url}")
        image = upload_image(BASE_IMAGE, repo.repository_url, username, password)
        log.info(f"Waiting for compute pool: {compute_pool}")
        handler.wait_for_compute_pool(compute_pool)
        log.info(f"Generating service spec")
        hf_token = get_hf_token(hf_token)
        spec_local_file = generate_spcs_spec(Path("./spcs_spec.yaml.j2"), image, hf_token)
        log.info(f"Creating stage to upload spcs spec")
        handler.create_stage(db, schema, stage_name)
        log.info(f"Uploading spcs spec")
        stage_path = handler.upload_service_spec(db, schema, stage_name, spec_local_file)
        log.info(f"Creating service")
        handler.create_service(compute_pool, stage_path, db, schema, service_name)
        log.info(f"Waiting for service to be ready")
        service = handler.wait_for_service(db, schema, service_name)
        log.info(f"Created service: {service}")
        result = handler.stream_service_logs(db, schema,
                                             service_name, '0',
                                             'model-worker', 'Uvicorn running')
        if not result:
            raise Exception("Something went wrong, `model-worker` did not start properly")
        service = handler.get_service(db, schema, service_name)
        service_endpoint = service.endpoints['service']
        log.info(f"Created service: {db}.{schema}.{service_name}")
        log.info(f"Created compute pool: {compute_pool}")
        log.info(
            f"Your services is ready!!! Access it via: https://{service_endpoint} "
            f"Use {username}/{password} to log in")
