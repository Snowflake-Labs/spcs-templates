"""Gradio UI for the rcr_customer_creds SPCS sample.

Two PATs are mounted into this container as env vars (one per team's service
user). Switching the team in the dropdown switches which PAT/user is used to
query the same row-access-policy-protected table, demonstrating how
customer-provided credentials let an SPCS service connect to Snowflake as
different identities at runtime.
"""

import logging
import os
import sys

import gradio as gr
import pandas as pd
import snowflake.connector


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(name)s [%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


log = get_logger("rcr_customer_creds")

ACCOUNT   = os.environ["SNOWFLAKE_ACCOUNT"]
HOST      = os.environ["SNOWFLAKE_HOST"]
WAREHOUSE = os.environ["WAREHOUSE"]
DATABASE  = os.environ["DATABASE"]
SCHEMA    = os.environ["SCHEMA"]
TABLE     = os.environ["TABLE"]
PORT      = int(os.environ.get("SERVER_PORT", "8080"))

TEAMS = {
    "Finance": {
        "user": os.environ["FINANCE_USER"],
        "pat":  os.environ["FINANCE_PAT"],
        "role": os.environ["FINANCE_ROLE"],
    },
    "Marketing": {
        "user": os.environ["MARKETING_USER"],
        "pat":  os.environ["MARKETING_PAT"],
        "role": os.environ["MARKETING_ROLE"],
    },
}

_connections: dict[str, snowflake.connector.SnowflakeConnection] = {}


def get_conn(team: str) -> snowflake.connector.SnowflakeConnection:
    """Return a cached Snowflake connection for the given team."""
    conn = _connections.get(team)
    if conn is not None and not conn.is_closed():
        return conn

    cfg = TEAMS[team]
    log.info("Opening connection for team=%s user=%s role=%s", team, cfg["user"], cfg["role"])
    conn = snowflake.connector.connect(
        account=ACCOUNT,
        host=HOST,
        user=cfg["user"],
        password=cfg["pat"],
        role=cfg["role"],
        warehouse=WAREHOUSE,
        database=DATABASE,
        schema=SCHEMA,
        client_session_keep_alive=True,
    )
    _connections[team] = conn
    return conn


def load_table(team: str) -> tuple[pd.DataFrame, str]:
    """Query team_data as the team's service user.

    Returns a (dataframe, status_message) tuple. On any failure (auth, missing
    grants, table not visible, transient network) we surface the error in the
    UI instead of crashing the app, so the readiness probe still passes.
    """
    cfg = TEAMS[team]
    try:
        conn = get_conn(team)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, team, region, metric, amount FROM {DATABASE}.{SCHEMA}.{TABLE} ORDER BY id"
            )
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=cols)
        status = (
            f"Loaded **{len(df)}** row(s) as `{cfg['user']}` "
            f"using role `{cfg['role']}`."
        )
        return df, status
    except Exception as exc:
        log.exception("Failed to load team_data for team=%s", team)
        # Drop the cached connection so the next attempt rebuilds it.
        _connections.pop(team, None)
        status = (
            f"**Query failed for team `{team}`** "
            f"(user `{cfg['user']}`, role `{cfg['role']}`):\n\n"
            f"```\n{type(exc).__name__}: {exc}\n```"
        )
        return pd.DataFrame(), status


with gr.Blocks(title="RCR customer credentials demo") as demo:
    gr.Markdown(
        "# Team data viewer\n"
        "This SPCS service connects to Snowflake using two different "
        "customer-provided PATs (Finance vs Marketing service users). "
        "A row access policy on `team_data` filters rows based on the "
        "service user's role — switching the dropdown changes which PAT "
        "the backend uses, and therefore which rows you see."
    )
    team_input = gr.Dropdown(choices=list(TEAMS.keys()), value="Finance", label="Team")
    status_output = gr.Markdown()
    table_output = gr.Dataframe(label="team_data")
    team_input.change(fn=load_table, inputs=team_input, outputs=[table_output, status_output])
    # Run the initial fetch on page load instead of at module import time, so
    # startup never depends on Snowflake being reachable / the role still
    # having the required CALLER grants.
    demo.load(fn=load_table, inputs=team_input, outputs=[table_output, status_output])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT)
