#!/opt/conda/bin/python3

import os
import logging
import ffmpeg
import numpy as np
import gzip
import shutil
from typing import List, Generator
from snowflake.snowpark import Session
from dataclasses import dataclass


@dataclass
class InputRow:
    audio_id: str
    filepath: str
    text: str
    audio_data: list


@dataclass
class OutputRow:
    text: str


def get_rank() -> int:
    return int(os.environ.get("SNOWFLAKE_JOB_INDEX", 0))


def get_world_size() -> int:
    return int(os.environ.get("SNOWFLAKE_JOBS_COUNT", 1))


def get_job_name() -> int:
    return os.environ.get("SNOWFLAKE_SERVICE_NAME", "test01")


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


class WorkerFormatter(logging.Formatter):
    def format(self, record):
        record.rank, record.world_size = get_rank(), get_world_size()
        return super().format(record)


def init_logger(name: str):
    logger = logging.getLogger(name)
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logger.setLevel(log_level)

    ch = logging.StreamHandler()
    log_format = (
        "%(asctime)s [Rank: %(rank)d/%(world_size)d];%(levelname)s:  %(message)s"
    )
    formatter = WorkerFormatter(log_format)

    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger


logger = init_logger(__name__)


def load_audio(local_filepath: str, encode=True, sample_rate: int = 16000):
    with open(local_filepath, "rb") as file:
        byte_data = file.read()

    if encode:
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input("pipe:", threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sample_rate)
                .run(
                    cmd="ffmpeg",
                    capture_stdout=True,
                    capture_stderr=True,
                    input=byte_data,
                )
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    else:
        out = byte_data

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


def list_files(session: Session, stage_path: str) -> List[str]:
    if not stage_path.startswith("@"):
        stage_path = f"@{stage_path}"

    list_command = f"LIST {stage_path}"
    try:
        result = session.sql(list_command).collect()
        audio_files = [row["name"] for row in result]
        return audio_files
    except Exception as e:
        logger.error(f"Error listing files in stage {stage_path}: {e}")
        raise e


def download_file_from_stage(session: Session, stage_path: str, local_path: str) -> str:
    if not stage_path.startswith("@"):
        stage_path = f"@{stage_path}"

    get_command = f"GET {stage_path} file://{local_path}"
    try:
        session.sql(get_command).collect()
        logger.debug(f"Downloaded {stage_path} to {local_path}")
    except Exception as e:
        logger.error(f"Error downloading file from stage {stage_path}: {e}")
        raise e
    file_name = stage_path.split("/")[-1]

    # remove .gz if it exists
    dest_filename = os.path.join(local_path, file_name)
    if dest_filename.endswith(".gz"):
        with gzip.open(dest_filename, "rb") as f_in:
            with open(dest_filename[:-3], "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
                os.remove(dest_filename)
    return dest_filename[:-3] if dest_filename.endswith(".gz") else dest_filename


def get_batch_iterator(
        rank: int, world_size: int, batch_size: int, files: List[str]
) -> Generator[List[str], None, None]:
    """
    Generator to yield batches of files for distributed processing.
    :param rank: The rank of the current worker.
    :param world_size: The total number of workers.
    :param batch_size: The size of each batch.
    :param files: List of files to be processed.
    :return: Generator yielding batches of files.
    """
    for i in range(rank * batch_size, len(files), batch_size * world_size):
        yield files[i: i + batch_size]
