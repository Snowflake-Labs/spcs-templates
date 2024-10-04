import os.path

import toml
from pathlib import Path
import logging
import snowflake.connector
from snowflake.snowpark import Session, DataFrame


def init_logger(log_name: str):
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

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
    parameters_to_check = ['account', 'user', 'warehouse', 'database', 'schema', 'stage_name']
    for param in parameters_to_check:
        _check_config_parameter(config, param)
    params = {
        "account": config['account'],
        "user": config['user'],
        "database": config['database'],
        'schema': config['schema'],
    }
    if 'host' in config:
        params['host'] = config['host']

    if 'SNOWFLAKE_HOST' in os.environ:
        params['authenticator'] = 'oauth'
        params['token'] = _get_login_token()
    else:
        _check_config_parameter(config, 'password')
        params['password'] = config['password']
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
