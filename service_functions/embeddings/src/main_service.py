import click
import os

from utils import init_logger
from app import app

logger = init_logger("main")


@click.command()
@click.option('--ip', default="0.0.0.0", help="ip address to bind")
@click.option('--port', default=8000, help="port to bind")
def main(ip: str, port: int):
    app.run(ip, port, debug=False)


if __name__ == '__main__':
    logger.info(f"starting worker: {os.getpid()}")
    main()
