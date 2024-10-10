import os
import tempfile
import time
import uuid
import click

import pandas as pd
from pandas import DataFrame
from spcs_utils import init_logger, load_toml_config, get_compute_pool_type, get_connection, InputRow, \
    ModelConfiguration

from feature_extractor import extract_embeddings
from classifier import run_classifier

logger = init_logger("EmbeddingsJobMain")


def download_file(cur, stage_source_file, local_dest_dir):
    cur.execute(f"""
    GET @{stage_source_file} 
    file://{local_dest_dir}
    """)


def get_rank():
    if 'HOSTNAME' not in os.environ:
        return 0
    prefix = 'statefulset-'
    hostname = os.environ['HOSTNAME']
    try:
        return int(hostname[len(prefix):])
    except:
        logger.warn(f"incorrect hostname: {hostname}, using rank 0")
        return 0


def get_world_size():
    if 'WORLD_SIZE' not in os.environ:
        return 1
    return int(os.environ['WORLD_SIZE'])


def process_df(df, filename, batch_size, model_configuration: ModelConfiguration, task: str):
    rows = [InputRow(idx=row['ID'], text=row['TEXT']) for _, row in df.iterrows()]
    num_batches = len(rows) // batch_size + 1
    output_rows = []
    logger.info(f"file: {filename} has {num_batches} batches with batch_size: {batch_size}")
    for i in range(0, num_batches):
        logger.info(f"processing file:{filename}, batch {i}")
        batch_rows = rows[i * batch_size:(i + 1) * batch_size]
        if task == 'extract_embeddings':
            output_rows += extract_embeddings(batch_rows, batch_size, model_configuration)
        else:
            output_rows += run_classifier(batch_rows, batch_size, model_configuration)
    return output_rows


def write_output_to_stage(cur, local_dir, filename, df: DataFrame, stage_path):
    local_file = os.path.join(local_dir, filename)
    df.to_parquet(path=local_file)
    sql = f"PUT file://{local_file} @{stage_path}"
    result = cur.execute(sql)
    logger.debug(f"query:{sql}, result: {result}")


def process_file(cur,
                 dest_dir: str,
                 stage_file_metadata,
                 stage_output_path: str,
                 batch_size: int,
                 model_configuration: ModelConfiguration,
                 task: str):
    filepath, size, hash, date = stage_file_metadata
    filename = os.path.basename(filepath)
    download_file(cur, filepath, dest_dir)
    local_file_dest = os.path.join(dest_dir, filename)
    df = pd.read_parquet(local_file_dest)
    output_rows = process_df(df, filename, batch_size, model_configuration, task)
    output_df = pd.DataFrame([row.__dict__ for row in output_rows])
    output_dir = os.path.join(dest_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    write_output_to_stage(cur, output_dir, f"output_{filename}", output_df, stage_output_path)


def create_pd_dataset(cur,
                      dest_dir: str,
                      stage_files_metadata):
    local_files = []
    for stage_file_metadata in stage_files_metadata:
        filepath, size, hash, date = stage_file_metadata
        filename = os.path.basename(filepath)
        download_file(cur, filepath, dest_dir)
        local_file_dest = os.path.join(dest_dir, filename)
        local_files.append(local_file_dest)
    df = pd.concat([pd.read_parquet(file) for file in local_files])
    return df


def get_local_batches(df, batch_size: int, rank: int, world_size: int):
    pointer = 0
    while pointer < len(df):
        yield df.iloc[pointer + rank * batch_size: pointer + (rank + 1) * batch_size]
        pointer += world_size * batch_size


def process_batch(cur,
                  dest_dir: str,
                  df,
                  batch_id,
                  rank,
                  stage_output_path: str,
                  batch_size: int,
                  model_configuration: ModelConfiguration,
                  task: str):
    output_rows = process_df(df, 'test', batch_size, model_configuration, task)
    output_df = pd.DataFrame([row.__dict__ for row in output_rows])
    output_dir = os.path.join(dest_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    write_output_to_stage(cur, output_dir, f"output_{rank}_{batch_id}", output_df, stage_output_path)


def execute(job_id: str,
            batch_size: int,
            stage_name: str,
            stage_data_path: str,
            stage_output_path: str,
            model_configuration: ModelConfiguration,
            snowflake_creds_config,
            task: str):
    stage_full_data_path = f"{stage_name}/{stage_data_path}/"
    stage_full_output_path = f"{stage_name}/{stage_output_path}"
    logger.info(f"starting job: {job_id}, stage_data: {stage_full_data_path}, stage_output: {stage_full_output_path}")
    with get_connection(snowflake_creds_config) as conn:
        cur = conn.cursor()
        cur.execute(f"LIST @{stage_full_data_path}")
        files = cur.fetchall()
        world_size = get_world_size()
        rank = get_rank()
        logger.info(f"Processing {len(files)} files, world_size: {world_size}, rank: {rank}")
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx in range(rank, len(files), world_size):
                process_file(cur, tmpdir, files[idx], stage_full_output_path, batch_size, model_configuration, task)


def get_job_name():
    return os.environ.get('SNOWFLAKE_SERVICE_NAME', str(uuid.uuid4()).split('-')[0])


@click.command()
@click.option('--task', help="task to execute")
def main(task: str):
    start_time = time.time()
    rank = get_rank()
    world_size = get_world_size()
    job_id = f"{get_job_name()}-{world_size}-{rank}"
    config = load_toml_config()
    model_configuration = ModelConfiguration(classifier_model_name=config['general']['classifier_model_name'],
                                             embedding_model_name=config['general']['embedding_model_name'],
                                             embedding_tokenizer_name=config['general']['embedding_tokenizer_name'])
    stage_name = config['job']['stage_name']
    stage_data_path = config['job']['stage_data_path']
    stage_output_path = config['job']['stage_output_path']
    batch_size = config["compute_pool"][get_compute_pool_type()]['batch_size']

    snowflake_creds_config = config['snowflake']['credentials']
    execute(job_id, batch_size, stage_name, stage_data_path, stage_output_path, model_configuration,
            snowflake_creds_config, task)
    total_time = time.time() - start_time
    logger.info(f"Finished processing, waiting, time: {total_time}")
    time.sleep(1000000)


if __name__ == "__main__":
    main()
