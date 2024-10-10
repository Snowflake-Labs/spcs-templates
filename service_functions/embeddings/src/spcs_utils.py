import logging
import os
import os.path
from pathlib import Path
from dataclasses import dataclass

import snowflake.connector
import toml
from snowflake.snowpark import Session


@dataclass
class ModelConfiguration:
    """
    Defines the model configuration
    """
    classifier_model_name: str
    embedding_model_name: str
    embedding_tokenizer_name: str


@dataclass
class InputRow:
    """
    Defines the input format of each row
    """
    idx: int
    text: str


@dataclass
class OutputRow:
    """
    Defines the output format of each row
    """
    idx: int
    output: str


def init_logger(log_name: str):
    logger = logging.getLogger(log_name)
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logger.setLevel(log_level)

    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s;%(levelname)s:  %(message)s", "%Y-%m-%d %H:%M:%S")
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger


def get_snowpark_session(config):
    params = _get_connection_parameters(config)
    return Session.builder.configs(params).create()


def get_connection(config):
    params = _get_connection_parameters(config)
    return snowflake.connector.connect(**params)


def _check_config_parameter(config, parameter_name: str):
    value = config[parameter_name]
    if value is None:
        raise ValueError(f"Parameter {parameter_name} not found")
    if value.startswith("<<"):
        raise ValueError(f"Update config.toml file. Parameter {parameter_name} has incorrect value: {value}")


def _get_connection_parameters(config):
    if 'SNOWFLAKE_HOST' in os.environ:
        return _get_spcs_connection_parameters()
    parameters_to_check = ['account', 'user', 'warehouse', 'database', 'schema', 'stage_name', 'password']
    for param in parameters_to_check:
        _check_config_parameter(config, param)
    params = {
        "account": config['account'],
        "user": config['user'],
        "database": config['database'],
        'schema': config['schema'],
        'password': config['password'],
    }
    if 'host' in config:
        params['host'] = config['host']
    return params


def _get_spcs_connection_parameters():
    params = {
        "account": os.environ['SNOWFLAKE_ACCOUNT'],
        "host": os.environ['SNOWFLAKE_HOST'],
        'authenticator': 'oauth',
        'token': _get_login_token(),
        "database": os.environ['SNOWFLAKE_DATABASE'],
        'schema': os.environ['SNOWFLAKE_SCHEMA'],
    }
    return params


def _get_login_token():
    with open('/snowflake/session/token', 'r') as f:
        return f.read()


def _get_test_connection(config):
    params = {
        "account": config['account'],
        "user": config['user'],
        "password": config['password'],
        "database": config['database'],
        'schema': config['schema'],
    }
    if 'host' in config:
        params['host'] = config['host']
    return snowflake.connector.connect(**params)


def load_toml_config():
    path = Path(__file__)
    return toml.load(path.parent.parent.joinpath("config.toml"))


def get_compute_pool_type():
    return os.environ.get('COMPUTE_POOL_INSTANCE_TYPE', 'default')
