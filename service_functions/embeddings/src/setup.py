import os.path
import random
import time
from pathlib import Path

import click
# Import Snowflake modules
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from utils import init_logger, load_toml_config, get_snowpark_session

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


def render_sql_file(input_filepath, context):
    template_full_path = Path(input_filepath)
    templates_dir = str(template_full_path.parent)
    template_filename = str(template_full_path.name)
    file_loader = FileSystemLoader(templates_dir)
    env = Environment(loader=file_loader)
    template = env.get_template(template_filename)

    rendered_filepath = template_full_path.parent.parent.joinpath('output').joinpath(template_filename).with_suffix('')
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
        logger.error(f"Error: {e}", e)


def create_and_populate_table(session, full_table_name, recreate: bool = True,
                              num_rows: int = 100000, batch_size=50000):
    words = get_words(words_file)
    overwrite = recreate
    num_batches = num_rows // batch_size + 1
    logger.info(f"Creating table: {full_table_name}, with # of rows: {num_rows}")
    for batch_idx in range(0, num_batches):
        rows = []
        for row_idx in range(batch_idx * batch_size, min(num_rows, (batch_idx + 1) * batch_size)):
            rows.append({"ID": f"{row_idx}", "TEXT": get_random_phrase(words, max_len=3)})

        df = pd.DataFrame(rows)
        if len(df) > 0:
            session.write_pandas(df, full_table_name, auto_create_table=True, overwrite=overwrite)
            logger.info(f"Table: {full_table_name}, finished batch: {batch_idx}x{batch_size}")
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


def _render_setup_resources_sql(filename, config, setup_steps_config):
    setup_resources_context = {
        'COMPUTE_POOL_NAME': config['compute_pool_name'],
        'COMPUTE_POOL_INSTANCES': config['compute_pool_nodes'],
        'COMPUTE_POOL_TYPE': config['compute_pool_type'],
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'STAGE_NAME': config['stage_name'],
        'IMAGE_REPOSITORY': config['image_repository'],
        'RECREATE_COMPUTE_POOL': setup_steps_config['recreate_compute_pool'],
    }
    filepath = Path(__file__).parent.parent.joinpath('sql').joinpath('input').joinpath(filename)
    return render_sql_file(filepath, setup_resources_context)


def _render_eai(filename, config):
    setup_eai_context = {
        'ROLE': config['role'],
        'DATABASE': config['database'],
        'SCHEMA': config['schema'],
        'EAI_NAME': config['eai_name'],
    }
    input_filepath = Path(__file__).parent.parent.joinpath('sql').joinpath('input').joinpath(filename)
    return render_sql_file(input_filepath, setup_eai_context)


def _render_start_service(filename, config):
    setup_eai_context = {
        'SERVICE_NAME': config['service_name'],
        'COMPUTE_POOL_NAME': config['compute_pool_name'],
        'SERVICE_IMAGE': config['service_image'],
        'NUM_GPUS': config['service_instances'],
        'SERVICE_NUM_INSTANCES': config['service_instances'],
        'MAX_BATCH_SIZE': 1024,
    }
    filepath = Path(__file__).parent.parent.joinpath('sql').joinpath('input').joinpath(filename)
    return render_sql_file(filepath, setup_eai_context)


def _render_start_service_embeddings_warmup(filename, config):
    setup_eai_context = {
        'SERVICE_FUNCTION_NAME': config['service_function_name'],
    }
    filepath = Path(__file__).parent.parent.joinpath('sql').joinpath('input').joinpath(filename)
    return render_sql_file(filepath, setup_eai_context)


def _get_image_repository(session, database: str, schema: str, image_repo: str):
    session.sql(f'USE  {database}.{schema}').collect()
    image_repo = image_repo.upper()
    resp = session.sql(f"show image repositories like '{image_repo}';").collect()
    for row in resp:
        if row.name == image_repo:
            return row
    raise Exception(f"repository {image_repo} not found in {database}.{schema}")


def build_and_upload_service_image(image_repo_url: str, image_repo_name: str, image_name: str, user: str,
                                   password: str, database: str, schema: str):
    os.system(f"docker login {image_repo_url} -u {user} -p {password}")
    build_image_cmd = f"""
docker build 
--platform linux/amd64 
-t {image_repo_url}/{image_name} 
-f./Dockerfile.service . 
    """.replace("\n", " ")
    os.system(build_image_cmd)

    upload_image_cmd = f"docker push {image_repo_url}/{image_name}"
    os.system(upload_image_cmd)
    return f"/{database}/{schema}/{image_repo_name}/{image_name}"


def _get_or_rebuild_image(session, config, setup_steps_config):
    if setup_steps_config['rebuild_image']:
        service_image_name = 'embeddings_service:01'
        image_repo_row = _get_image_repository(session, config['database'], config['schema'],
                                               config['image_repository'])
        image_path = build_and_upload_service_image(image_repo_row.repository_url, image_repo_row.name,
                                                    service_image_name, config['user'],
                                                    config['password'], config['database'], config['schema'])
        return image_path
    elif 'service_image' in config:
        return config['service_image']
    else:
        return None


def execute(config, setup_steps_config):
    database, schema, stage_name, image_repository = config['database'], config['schema'], config['stage_name'], config[
        'image_repository']
    table = 'DUMMY_TEXT_DATA_V1_3000000'
    service_image_name = 'embeddings_service:01'
    warehouse = config['warehouse']
    with get_snowpark_session(config) as session:
        session.sql(f'USE WAREHOUSE {warehouse}').collect()
        session.sql(f'USE  {database}.{schema}').collect()
        # setup resources
        logger.info("Creating resources")
        setup_resources_sql_filepath = _render_setup_resources_sql("setup_resources.sql.j2", config, setup_steps_config)
        execute_sql_file(session, setup_resources_sql_filepath)

        if setup_steps_config['recreate_table']:
            create_and_populate_table(session, table, num_rows=1000000)

        if setup_steps_config['recreate_eai']:
            eai_name = config['eai_name']
            logger.info(f'Creating external integration resource: {eai_name}')
            # setup EAI
            setup_resources_sql_filepath = _render_eai("setup_eai.sql.j2", config)
            execute_sql_file(session, setup_resources_sql_filepath)

        config['service_image'] = _get_or_rebuild_image(session, config, setup_steps_config)

        if setup_steps_config['recreate_service']:
            if setup_steps_config['service_image'] is None:
                raise ValueError(
                    f"No image found. Either specify rebuild_image=true in config file, or specify service_image in config file")
            logger.info(f"Creating SPCS service: {config['service_name']}")
            # create Service
            setup_resources_sql_filepath = _render_start_service("start_service.sql.j2", config)
            execute_sql_file(session, setup_resources_sql_filepath)
        config['service_function_name'] = f"{config['service_name']}_FN"

        logger.info(f"Waiting for compute pool {config['compute_pool_name']} to start")
        wait_for_compute_pool(session, config['compute_pool_name'])

        logger.info(f"Waiting for service {config['service_name']} to start")
        wait_for_service(session, config['service_name'])

        if setup_steps_config['run_warmup']:
            # run Service function warmup
            logger.info(f"Running service function: {config['service_function_name']} on test data")
            setup_resources_sql_filepath = _render_start_service_embeddings_warmup(
                "start_service_embeddings_warmup.sql.j2", config)
            execute_sql_file(session, setup_resources_sql_filepath)


@click.command()
@click.option('--password', help="Snowflake password")
@click.option('--host', default="snowflakecomputing.com", help="Snowflake host")
def main(password: str, host: str):
    config = load_toml_config()
    setup_steps_config = config['setup']['steps']
    snowflake_config = config['snowflake']['credentials']
    snowflake_config['password'] = password
    snowflake_config['host'] = host

    execute(snowflake_config, setup_steps_config)


if __name__ == "__main__":
    logger.info(f"starting setup, pid: {os.getpid()}")
    main()