import os
import time

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

    return snowflake.connector.connect(**connection_parameters)


def train():
    pass


if __name__ == "__main__":
    print("Running dummy workload")
    for i in range(0, 100000):
        print(f"iteration: {i}")
        time.sleep(2)
