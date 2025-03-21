#!/opt/conda/bin/python3

import os
import click
import toml
import tempfile
from typing import List, Dict
import pandas as pd
from snowflake.snowpark import Session
from audio2text.models import openai_whisper
from audio2text.utils import (
    init_logger,
    load_audio,
    list_files,
    download_file_from_stage,
    get_batch_iterator,
    get_job_name,
    get_rank,
    get_world_size,
)


logger = init_logger(__name__)


def create_session() -> Session:
    with open("/snowflake/session/token", "r") as f:
        token = f.read()
    snowflake_warehouse = os.getenv("SNOWFLAKE_QUERY_WAREHOUSE")

    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "host": os.getenv("SNOWFLAKE_HOST"),
        "authenticator": "oauth",
        "token": token,
        "warehouse": snowflake_warehouse,
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "client_session_keep_alive": True,
    }

    return Session.builder.configs(connection_parameters).create()


def upload_parquet_to_stage(
    session: Session,
    local_dir: str,
    stage_output_path: str,
    output_files: List[str],
    output_transcriptions: List[str],
    batch_number: int,
):
    output_df = pd.DataFrame(
        {"files": output_files, "transcriptions": output_transcriptions}
    )
    output_file = f"output_file_{batch_number}.parquet"
    parquet_file = os.path.join(local_dir, output_file)
    output_df.to_parquet(parquet_file, engine="pyarrow")
    put_command = f"PUT 'file://{os.path.abspath(parquet_file)}' '@{stage_output_path}' OVERWRITE=TRUE"
    result = session.sql(put_command).collect()
    logger.info(f"Uploaded {parquet_file} to @{stage_output_path}, result: {result}")


def process(
    model: openai_whisper.Model,
    stage_name: str,
    rank: int,
    world_size: int,
    stage_data_path: str,
    local_dir: str,
    batch_size: int = 32,
):
    upload_rate = 10  # create new parquet file every 10 batches
    with create_session() as session:
        logger.info(
            f"Starting processing, rank: {rank}, world_size: {world_size}, stage_data_path: {stage_data_path}, local_dir: {local_dir}"
        )
        curr_batch = 0
        stage_audio_files = list_files(session, stage_data_path)

        output_files = []
        output_transcriptions = []
        total_batches_to_process = (
            len(stage_audio_files) + batch_size * world_size - 1
        ) // (batch_size * world_size)
        for audio_file_batch in get_batch_iterator(
            rank, world_size, batch_size, stage_audio_files
        ):
            logger.info(f"Processing batch {curr_batch+1}/{total_batches_to_process}")
            curr_batch += 1
            audio_data_batches = []
            for audio_file in audio_file_batch:
                local_file_path = download_file_from_stage(
                    session, audio_file, local_dir
                )
                logger.debug(f"loading file: {local_file_path}")
                audio_data = load_audio(local_file_path)
                audio_data_batches.append(audio_data)

            transcriptions = model.transcribe_batch(audio_data_batches)
            output_files.extend(audio_file_batch)
            output_transcriptions.extend(transcriptions)

            for idx in range(0, len(audio_file_batch)):
                logger.debug(
                    f"Transcription for {audio_file_batch[idx]}: {transcriptions[idx]}"
                )

            if curr_batch % upload_rate == 0:
                upload_parquet_to_stage(
                    session,
                    local_dir,
                    get_stage_output_path(stage_name),
                    output_files,
                    output_transcriptions,
                    curr_batch,
                )
                output_files = []
                output_transcriptions = []

        if len(output_files) > 0:
            upload_parquet_to_stage(
                session,
                local_dir,
                get_stage_output_path(stage_name),
                output_files,
                output_transcriptions,
                curr_batch,
            )


def get_stage_output_path(stage_name: str) -> str:
    job_name = get_job_name()
    rank = get_rank()
    return f"{stage_name}/{job_name}/{rank}/output"


def get_model(config: Dict) -> openai_whisper.Model:
    model_type = config["general"]["model_type"]
    if model_type == "whisper-hf":
        return openai_whisper.Model(config)


@click.command()
@click.option("--config-file", help="Model Name")
@click.option("--stage-name", help="Stage name")
@click.option("--stage-data-path", help="Stage data path")
def main(config_file: str, stage_name: str, stage_data_path: str):
    config = toml.load(config_file)
    model = get_model(config)
    with tempfile.TemporaryDirectory() as temp_dir:
        process(
            model,
            stage_name,
            get_rank(),
            get_world_size(),
            f"{stage_name}/{stage_data_path}",
            temp_dir,
        )


if __name__ == "__main__":
    main()
