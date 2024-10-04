import os
import tempfile
import time
import uuid

import pandas as pd
from pandas import DataFrame
from utils import init_logger, load_toml_config, get_compute_pool_type

from feature_extractor import InputRow, ModelConfiguration, extract_embeddings

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


def process_df(df, filename, batch_size, model_configuration: ModelConfiguration):
    rows = [InputRow(idx=row['ID'], text=row['TRANSFORMED_TEXT']) for _, row in df.iterrows()]
    num_batches = len(rows) // batch_size + 1
    output_rows = []
    logger.info(f"file: {filename} has {num_batches} batches with batch_size: {batch_size}")
    for i in range(0, num_batches):
        logger.info(f"processing file:{filename}, batch {i}")
        batch_rows = rows[i * batch_size:(i + 1) * batch_size]
        output_rows += extract_embeddings(batch_rows, batch_size, model_configuration)
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
                 model_configuration: ModelConfiguration):
    filepath, size, hash, date = stage_file_metadata
    filename = os.path.basename(filepath)
    download_file(cur, filepath, dest_dir)
    local_file_dest = os.path.join(dest_dir, filename)
    df = pd.read_parquet(local_file_dest)
    output_rows = process_df(df, filename, batch_size, model_configuration)
    output_df = pd.DataFrame([row.__dict__ for row in output_rows])
    output_dir = os.path.join(dest_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    write_output_to_stage(cur, output_dir, f"output_{filename}", output_df, stage_output_path)


def execute(job_id: str,
            batch_size: int,
            stage_name: str,
            stage_data_path: str,
            stage_output_path: str,
            model_configuration: ModelConfiguration):
    stage_full_data_path = f"{stage_name}/{stage_data_path}"
    stage_full_output_path = f"{stage_name}/{stage_output_path}"
    logger.info(f"starting job: {job_id}, stage_data: {stage_full_data_path}, stage_output: {stage_full_output_path}")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"LIST @{stage_full_data_path}")
        files = cur.fetchall()
        world_size = get_world_size()
        rank = get_rank()
        logger.info(f"Processing {len(files)} files, world_size: {world_size}, rank: {rank}")
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx in range(rank, len(files), world_size):
                process_file(cur, tmpdir, files[idx], stage_full_output_path, batch_size, model_configuration)


def get_job_name():
    return os.environ.get('SNOWFLAKE_SERVICE_NAME', str(uuid.uuid4()).split('-')[0])


def main():
    start_time = time.time()
    rank = get_rank()
    world_size = get_world_size()
    job_id = f"{get_job_name()}-{world_size}-{rank}"
    config = load_toml_config()
    model_configuration = ModelConfiguration(model_name=config['general']['model_name'],
                                             tokenizer_name=config['general']['tokenizer_name'])
    stage_name = config['job']['stage_name']
    stage_data_path = config['job']['stage_data_path']
    stage_output_path = config['job']['stage_output_path']
    batch_size = config["compute_pool"][get_compute_pool_type()]['batch_size']

    execute(job_id, batch_size, stage_name, stage_data_path, stage_output_path, model_configuration)
    total_time = time.time() - start_time
    logger.info(f"Finished processing, waiting, time: {total_time}")
    time.sleep(1000000)


if __name__ == "__main__":
    main()
