import os

import click
from gunicorn.app.base import BaseApplication
from async_app import app
from spcs_utils import load_toml_config, init_logger, InputRow, ModelConfiguration
from classifier import run_classifier

logger = init_logger("GunicornMain")

try:
    import _scproxy

    # Cache the return values of _scproxy functions
    # This avoids calling them in subprocesses
    proxies = _scproxy._get_proxies()
    _scproxy._get_proxies = lambda: proxies
    proxy_settings = _scproxy._get_proxy_settings()
    _scproxy._get_proxy_settings = lambda: proxy_settings
except ImportError:
    pass

DEBUG = True


def load_model(_):
    global sess
    print('fork')
    config = load_toml_config()
    model_config = ModelConfiguration(classifier_model_name=config['general']['classifier_model_name'],
                                      embedding_model_name=config['general']['embedding_model_name'],
                                      embedding_tokenizer_name=config['general']['embedding_tokenizer_name'])
    run_classifier([InputRow(idx=0, text='test')], batch_size=1, model_config=model_config)


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)
        self.cfg.set('post_worker_init', load_model)

    def load(self):
        return self.application


@click.command()
@click.option('--ip', default="0.0.0.0", help="ip address to bind")
@click.option('--port', default=8000, help="port to bind")
def main(ip: str, port: int):
    config = load_toml_config()
    options = {
        'bind': f'{ip}:{port}',
        "worker_class": "uvicorn.workers.UvicornWorker",
        'workers': config['general']['max_concurrent_workers'],
    }

    StandaloneApplication(app, options).run()


if __name__ == "__main__":
    main()
