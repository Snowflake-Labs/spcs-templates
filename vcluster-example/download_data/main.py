import os
import time

import click
import snowflake.connector


def get_connection():
    with open("/snowflake/session/token", "r") as f:
        token = f.read()

    connection_parameters = {
        "account": os.environ['SNOWFLAKE_ACCOUNT'],
        "host": os.environ['SNOWFLAKE_HOST'],
        "authenticator": "oauth",
        "token": token,
        "database": os.environ['SNOWFLAKE_DATABASE'],
        "schema": os.environ['SNOWFLAKE_SCHEMA'],
        "role": os.environ['SNOWFLAKE_ROLE'],
        "client_session_keep_alive": True
    }
    print(connection_parameters)

    return snowflake.connector.connect(**connection_parameters)


@click.command()
@click.option('--stage-path', required=True, help="Snowflake stage")
@click.option('--target-dir', help="Target directory to download data to")
def download_data(stage_path: str, target_dir: str):
    print(f"Downloading data from {stage_path} to {target_dir}")
    start_time = time.time()
    os.makedirs(target_dir, exist_ok=True)
    with get_connection() as conn:
        cur = conn.cursor()
        get_sql = f"GET @{stage_path} file://{os.path.abspath(target_dir)}/"
        print(f"Executing SQL: {get_sql}")
        print(cur.execute(get_sql).fetchall())
        total_time = time.time() - start_time
        print(f"Successfully downloaded files to: {target_dir} in {total_time} seconds")


if __name__ == "__main__":
    download_data()
