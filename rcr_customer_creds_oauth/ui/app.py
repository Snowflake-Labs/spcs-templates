"""Finance data viewer — rcr_customer_creds_oauth SPCS sample.

Demonstrates customer-provided OAuth credentials (interactive authorization-code
flow) in SPCS.  The service owner role has NO SELECT on finance_data; only a user
who authenticates via Snowflake OAuth and has FINANCE_ROLE can query it.

Architecture
────────────
FastAPI app with two custom routes and a Gradio UI:

  GET /login     — Redirect the user's browser to Snowflake's OAuth authorize page.
  GET /callback  — Receive the authorization code, exchange it for an access token,
                   store it in a server-side session, and redirect back to /.
  GET /          — Gradio UI (shows the demo).

Session state is kept in a plain dict (session_id cookie → access token).  This
is intentionally simple: a demo running in a single SPCS pod, no persistence
required.
"""

import logging
import os
import secrets as py_secrets
import sys
import time
import urllib.parse

import gradio as gr
import pandas as pd
import requests
import snowflake.connector
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# ── Logging ───────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(name)s [%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(h)
    return logger

log = get_logger("rcr_oauth")

# ── Config ────────────────────────────────────────────────────────────────────

ACCOUNT   = os.environ["SNOWFLAKE_ACCOUNT"]
HOST      = os.environ["SNOWFLAKE_HOST"]
WAREHOUSE = os.environ["WAREHOUSE"]
DATABASE  = os.environ["DATABASE"]
SCHEMA    = os.environ["SCHEMA"]
TABLE     = os.environ["TABLE"]
PORT      = int(os.environ.get("SERVER_PORT", "8080"))

# OAuth client credentials — mounted from a Snowflake SECRET by configure_oauth.sql.
# Absent until that script is run and the service is updated.
OAUTH_CLIENT_ID     = os.environ.get("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
OAUTH_CONFIGURED    = bool(OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET)

# ── Session + CSRF state ──────────────────────────────────────────────────────

_sessions: dict[str, str] = {}          # session_id → access_token
_pending_states: dict[str, float] = {}  # CSRF state value → issued timestamp
_STATE_TTL = 300                         # seconds; states older than this are rejected


def _purge_expired_states() -> None:
    cutoff = time.time() - _STATE_TTL
    for s in [k for k, t in _pending_states.items() if t < cutoff]:
        del _pending_states[s]


# ── FastAPI routes ────────────────────────────────────────────────────────────

app = FastAPI()


@app.get("/login")
async def login(request: Request):
    """Start the OAuth authorization-code flow."""
    if not OAUTH_CONFIGURED:
        return HTMLResponse(
            "OAuth not configured — run configure_oauth.sql and restart the service.",
            status_code=503,
        )
    # Derive redirect_uri from the Host header so no env var is needed.
    # The OAuth integration's OAUTH_REDIRECT_URI must match this exactly.
    host = request.headers.get("host", HOST)
    redirect_uri = f"https://{host}/callback"

    state = py_secrets.token_hex(16)
    _pending_states[state] = time.time()
    _purge_expired_states()

    auth_url = (
        f"https://{HOST}/oauth/authorize"
        f"?response_type=code"
        f"&client_id={urllib.parse.quote(OAUTH_CLIENT_ID)}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&state={urllib.parse.quote(state)}"
    )
    log.info("Starting OAuth flow; redirect_uri=%s", redirect_uri)
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
):
    """Handle the redirect from Snowflake; exchange the code for a token."""
    if error:
        log.error("OAuth error from Snowflake: %s — %s", error, error_description)
        return HTMLResponse(
            f"<h3>OAuth error: {error}</h3><p>{error_description or ''}</p>"
            f'<p><a href="/">Back</a></p>',
            status_code=400,
        )

    # CSRF check: state must match something we issued recently.
    if not state or state not in _pending_states:
        return HTMLResponse(
            "Invalid or expired state parameter — please try logging in again."
            '<p><a href="/">Back</a></p>',
            status_code=400,
        )
    del _pending_states[state]

    host = request.headers.get("host", HOST)
    redirect_uri = f"https://{host}/callback"
    log.info("Token exchange: redirect_uri=%s token_url=https://%s/oauth/token-request", redirect_uri, HOST)

    # Exchange authorization code for access token via the internal Snowflake host.
    try:
        resp = requests.post(
            f"https://{HOST}/oauth/token-request",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
            timeout=10,
        )
        log.info("Token endpoint: status=%d body=%r", resp.status_code, resp.text[:500])
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log.exception("Token exchange request failed")
        return HTMLResponse(
            f"<h3>Token exchange failed</h3><pre>{type(exc).__name__}: {exc}</pre>"
            f"<p><a href='/'>Back</a></p>",
            status_code=502,
        )

    access_token = resp.json()["access_token"]
    session_id = py_secrets.token_hex(32)
    _sessions[session_id] = access_token
    log.info("OAuth login succeeded; session created")

    response = RedirectResponse("/", status_code=302)
    response.set_cookie("session_id", session_id, httponly=True, secure=True, samesite="lax")
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session_token(request: gr.Request) -> str | None:
    """Parse the session cookie from the raw Cookie header and look up the token."""
    raw = request.headers.get("cookie", "")
    cookies = {
        k: v
        for part in raw.split(";")
        if "=" in part
        for k, v in [part.strip().split("=", 1)]
    }
    sid = cookies.get("session_id")
    return _sessions.get(sid) if sid else None


def _connect_as_service() -> snowflake.connector.SnowflakeConnection:
    """Connect using the Snowflake-provided service user token (no customer creds)."""
    with open("/snowflake/session/token") as f:
        svc_token = f.read()
    return snowflake.connector.connect(
        account=ACCOUNT,
        host=HOST,
        authenticator="oauth",
        token=svc_token,
    )


def _connect_as_user(oauth_token: str) -> snowflake.connector.SnowflakeConnection:
    """Connect using the customer-provided OAuth access token."""
    return snowflake.connector.connect(
        account=ACCOUNT,
        host=HOST,
        authenticator="oauth",
        token=oauth_token,
        warehouse=WAREHOUSE,
        database=DATABASE,
        schema=SCHEMA,
    )


# ── Gradio functions ──────────────────────────────────────────────────────────

def check_service_owner(request: gr.Request) -> str:  # noqa: ARG001
    """Attempt to query finance_data as the service user — expected to fail."""
    try:
        conn = _connect_as_service()
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {DATABASE}.{SCHEMA}.{TABLE}")
            n = cur.fetchone()[0]
        conn.close()
        return (
            f"Unexpected: service user CAN see the table ({n} rows).  "
            "Verify that service_owner_role has no SELECT on finance_data."
        )
    except Exception as exc:
        return (
            "**Expected result** — service owner cannot query finance_data:\n\n"
            f"```\n{type(exc).__name__}: {exc}\n```\n\n"
            "This confirms the table is invisible to the service's own credentials."
        )


def load_finance_data(request: gr.Request) -> tuple[pd.DataFrame, str]:
    """Query finance_data using the logged-in user's OAuth token."""
    token = _get_session_token(request)
    if not token:
        return pd.DataFrame(), "Not logged in — click **Login with Snowflake** below."

    try:
        conn = _connect_as_user(token)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, region, metric, amount FROM {DATABASE}.{SCHEMA}.{TABLE} ORDER BY id"
            )
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
        conn.close()
        df = pd.DataFrame(rows, columns=cols)
        return df, f"Loaded **{len(df)}** row(s) as your Snowflake user via OAuth."
    except Exception as exc:
        log.exception("OAuth query failed")
        return pd.DataFrame(), (
            "Query failed — make sure `FINANCE_ROLE` is granted to your Snowflake user "
            "(see setup.sql):\n\n"
            f"```\n{type(exc).__name__}: {exc}\n```"
        )


def login_widget(request: gr.Request) -> str:
    """Return HTML for the login button or logged-in status."""
    if _get_session_token(request):
        return (
            '<p style="margin:0">You are logged in. '
            '<a href="/login">Switch user</a></p>'
        )
    if OAUTH_CONFIGURED:
        return (
            '<a href="/login" target="_top">'
            '<button style="font-size:1em;padding:6px 18px;cursor:pointer">'
            "Login with Snowflake"
            "</button></a>"
        )
    return (
        "<em>OAuth not configured — run configure_oauth.sql and restart the service.</em>"
    )


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Finance data viewer — OAuth credentials") as demo:
    gr.Markdown(
        "# Finance data viewer\n"
        "The **service owner role** has no `SELECT` on `finance_data`.  "
        "Only a user authenticated via **Snowflake OAuth** who has `FINANCE_ROLE` "
        "can query the table — the service acts on behalf of that user, not as itself."
    )

    # ── Step 1: service owner access check ────────────────────────────────────
    gr.Markdown("## Step 1 — Service owner access (expected: denied)")
    service_out = gr.Markdown()
    gr.Button("Check service owner access").click(
        fn=check_service_owner, outputs=service_out
    )

    gr.Markdown("---")

    # ── Step 2: OAuth login + data ────────────────────────────────────────────
    gr.Markdown("## Step 2 — Log in as yourself to see the data")
    login_html  = gr.HTML()
    data_status = gr.Markdown()
    data_table  = gr.Dataframe(label="finance_data")
    gr.Button("Refresh").click(fn=load_finance_data, outputs=[data_table, data_status])

    # On every page load: run the service-owner check and populate login state.
    demo.load(fn=check_service_owner, outputs=service_out)
    demo.load(fn=login_widget, outputs=login_html)
    demo.load(fn=load_finance_data, outputs=[data_table, data_status])


# ── Mount Gradio into FastAPI and run ─────────────────────────────────────────
# Custom routes (/login, /callback) are registered above; Gradio catches everything else.

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
