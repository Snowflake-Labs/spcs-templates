import logging
import os
import os.path
from pathlib import Path
import sys
import toml


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


def get_rank() -> int:
    return int(os.environ.get("SNOWFLAKE_JOB_INDEX", 0))


def get_world_size() -> int:
    return int(os.environ.get("SNOWFLAKE_JOBS_COUNT", 1))


def get_job_name() -> int:
    return os.environ.get("SNOWFLAKE_SERVICE_NAME", "test01")


def get_connection_parameters(config=None):
    if os.path.exists("/snowflake/session/token"):
        return _get_spcs_connection_parameters()
    params = {
        "account": config["account"],
        "user": config["user"],
        "database": config["database"],
        "schema": config["schema"],
        "password": os.environ["SNOWFLAKE_PASSWORD"],
    }
    if os.environ.get("SNOWFLAKE_HOST") is not None:
        params["host"] = os.environ["SNOWFLAKE_HOST"]
    return params


def _get_spcs_connection_parameters():
    params = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "host": os.environ["SNOWFLAKE_HOST"],
        "authenticator": "oauth",
        "token": _get_login_token(),
        "database": os.environ["SNOWFLAKE_DATABASE"],
        "schema": os.environ["SNOWFLAKE_SCHEMA"],
    }
    if os.environ.get("SNOWFLAKE_QUERY_WAREHOUSE") is not None:
        params["warehouse"] = os.environ["SNOWFLAKE_QUERY_WAREHOUSE"]
    return params


def _get_login_token():
    with open("/snowflake/session/token", "r") as f:
        return f.read()


def load_toml_config():
    path = Path(__file__)
    return toml.load(path.parent.parent.joinpath("config.toml"))
