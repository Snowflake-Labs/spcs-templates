import os.path
from pathlib import Path
import pandas as pd
import json
import numpy as np
import time
import sys
import cachetools
# Import Snowflake modules
from snowflake.snowpark import Session, DataFrame
from snowflake.snowpark.functions import col, when, try_cast, upper, lit
from snowflake.snowpark.types import StringType, IntegerType, Variant, DecimalType, FloatType, DoubleType
from snowflake.snowpark import Row, Column
import pandas as pd
import math
import click
from utils import init_logger, load_toml_config, get_connection, get_snowpark_session
import random
from jinja2 import Environment, FileSystemLoader

logger = init_logger("setup")

words_file = 'english_words.txt'


def get_words(filename):
    base_dir = Path(__file__).parent.parent
    filepath = str(base_dir.joinpath(filename))
    with open(filepath) as f:
        return [line.strip() for line in f]


def get_random_phrase(words, max_len=50):
    plen = random.randint(1, max_len)
    return " ".join([words[random.randint(0, len(words) - 1)] for i in range(plen)])


def render_sql_file(filepath, context):
    template_full_path = Path(filepath)
    templates_dir = str(template_full_path.parent)
    template_filename = str(template_full_path.name)
    file_loader = FileSystemLoader(templates_dir)
    env = Environment(loader=file_loader)
    template = env.get_template(template_filename)
    rendered_filepath = template_full_path.with_suffix('')
    rendered_content = template.render(context)
    with open(rendered_filepath, 'w') as file:
        file.write(rendered_content)
    return rendered_filepath


def execute_sql_file(session, filepath):
    try:
        with open(filepath, 'r') as file:
            sql_script = file.read()
        sql_statements = sql_script.split(';')

        for statement in sql_statements:
            if statement.strip():
                resp = session.sql(statement).collect()
                logger.info(f"Executed sql statement: {statement}, result: {resp}")

    except Exception as e:
        # check
        logger.error(f"Error: {e}", e)


def create_and_populate_table(session, full_table_name, recreate: bool = True,
                              num_rows: int = 100000, batch_size=1000000):
    words = get_words(words_file)
    overwrite = recreate
    num_batches = num_rows // batch_size + 1
    logger.info(f"Creating table: {full_table_name}, with # of rows: {num_rows}")
    for batch_idx in range(0, num_batches):
        rows = []
        for row_idx in range(batch_idx * batch_size, min(num_rows, (batch_idx + 1) * batch_size)):
            rows.append({"ID": f"{row_idx}", "TEXT": get_random_phrase(words, max_len=3)})
        logger.info(f"Table: {full_table_name}, finished batch: {batch_idx}x{batch_size}")

        df = pd.DataFrame(rows)
        session.write_pandas(df, full_table_name, auto_create_table=True, overwrite=overwrite)
        overwrite = False


def wait_for_compute_pool(session, compute_pool_name: str, timeout=800):
    sql = f"""
describe compute pool {compute_pool_name}    
    """

    start_time = time.time()
    while start_time + timeout > time.time():
        result = session.sql(sql).collect()
        state = result[0]['state'].lower()
        if state not in ['idle', 'active']:
            time.sleep(10)
            continue
        else:
            return
    raise Exception(f"Compute pool {compute_pool_name} did not reach idle or active state")


def _is_container_ready(rows) -> bool:
    for row in rows:
        if row['status'] not in ['READY', 'RUNNING']:
            logger.info(
                f"Container {row['database_name']}.{row['schema_name']}.{row['service_name']}.{row['container_name']} not ready")
            time.sleep(10)
            return False
    return True


def wait_for_service(session, service_name: str, timeout=800):
    sql = f"""
SHOW SERVICE CONTAINERS IN SERVICE {service_name}    
    """

    start_time = time.time()
    while start_time + timeout > time.time():
        rows = session.sql(sql).collect()
        if _is_container_ready(rows):
            logger.info(f"Service {service_name} is ready")
            return
    raise Exception(f"Service {service_name} did not reach idle or active state")


def _render_setup_resources_sql(filename, config):
    setup_resources_context = {
        'COMPUTE_POOL_NAME': config['compute_pool_name'],
        'COMPUTE_POOL_INSTANCES': config['compute_pool_nodes'],
        'COMPUTE_POOL_TYPE': config['compute_pool_type'],
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'STAGE_NAME': config['stage_name'],
        'IMAGE_REPOSITORY': config['image_repository'],
    }
    filepath = Path(__file__).parent.parent.joinpath('sql').joinpath(filename)
    return render_sql_file(filepath, setup_resources_context)


def _render_eai(filename, config):
    setup_eai_context = {
        'ROLE': config['role'],
    }
    filepath = Path(__file__).parent.parent.joinpath('sql').joinpath(filename)
    return render_sql_file(filepath, setup_eai_context)


def _render_start_service(filename, config):
    setup_eai_context = {
        'SERVICE_NAME': config['service_name'],
        'COMPUTE_POOL_NAME': config['compute_pool_name'],
        'SERVICE_IMAGE': config['service_image'],
        'NUM_GPUS': config['service_instances'],
        'SERVICE_NUM_INSTANCES': config['service_instances'],
        'MAX_BATCH_SIZE': 1024,
    }
    filepath = Path(__file__).parent.parent.joinpath('sql').joinpath(filename)
    return render_sql_file(filepath, setup_eai_context)


def execute(config):
    database, schema, stage_name, image_repository = config['database'], config['schema'], config['stage_name'], config[
        'image_repository']
    table = 'DUMMY_TEXT_DATA_V1_3000000'
    warehouse = config['warehouse']
    with get_snowpark_session(config) as session:
        session.sql(f'USE WAREHOUSE {warehouse}').collect()
        session.sql(f'USE  {database}.{schema}').collect()
        create_and_populate_table(session, table, num_rows=3000000)

        # # setup resources
        # setup_resources_sql_filepath = _render_setup_resources_sql("setup_resources.sql.j2", config)
        # execute_sql_file(session, setup_resources_sql_filepath)
        # # setup EAI
        # setup_resources_sql_filepath = _render_eai("setup_eai.sql.j2", config)
        # execute_sql_file(session, setup_resources_sql_filepath)
        # # create Service
        # setup_resources_sql_filepath = _render_start_service("start_service.sql.j2", config)
        # execute_sql_file(session, setup_resources_sql_filepath)
        #
        # logger.info(f"Waiting for compute pool {config['compute_pool_name']} to start")
        # wait_for_compute_pool(session, config['compute_pool_name'])
        #
        # logger.info(f"Waiting for service {config['service_name']} to start")
        # wait_for_service(session, config['service_name'])


@click.command()
@click.option('--password', help="Snowflake password")
@click.option('--host', default="snowflakecomputing.com", help="Snowflake host")
def main(password: str, host: str):
    config = load_toml_config()
    snowflake_config = config['snowflake']['credentials']
    snowflake_config['password'] = password
    snowflake_config['host'] = host
    execute(snowflake_config)


if __name__ == "__main__":
    logger.info(f"starting setup, pid: {os.getpid()}")
    main()
