"""Finance data viewer — rcr_customer_creds_oauth SPCS sample.

Demonstrates customer-provided OAuth credentials (interactive authorization-code
flow) in SPCS.  The service owner role has NO SELECT on finance_data; only a user
who authenticates via Snowflake OAuth and has FINANCE_ROLE can query it.

Architecture
────────────
FastAPI app with two custom routes and a Gradio UI:

  GET /login     — Redirect the user's browser to Snowflake's OAuth authorize page.
  GET /callback  — Receive the authorization code, exchange it for an access token,
                   resolve the Snowflake username via CURRENT_USER(), store both in
                   a server-side session, and redirect back to /.
  GET /           — Gradio UI (shows the demo).

Session state is kept in a plain dict (session_id cookie → {token, username}).
This is intentionally simple: a demo running in a single SPCS pod, no persistence
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

OAUTH_CLIENT_ID     = os.environ.get("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
OAUTH_CONFIGURED    = bool(OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET)

# ── Session + CSRF state ──────────────────────────────────────────────────────

_sessions: dict[str, dict] = {}         # session_id → {"token": str, "username": str}
_pending_states: dict[str, float] = {}  # CSRF state value → issued timestamp
_STATE_TTL = 300


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
            "OAuth not configured — run setup.sql and restart the service.",
            status_code=503,
        )
    host = request.headers.get("host", HOST)
    redirect_uri = f"https://{host}/callback"

    state = py_secrets.token_hex(16)
    _pending_states[state] = time.time()
    _purge_expired_states()

    auth_url = (
        f"https://{ACCOUNT}.snowflakecomputing.com/oauth/authorize"
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

    # Resolve the username so we can display it on the button.
    try:
        conn = snowflake.connector.connect(
            account=ACCOUNT, host=HOST, authenticator="oauth", token=access_token,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT CURRENT_USER()")
            username = cur.fetchone()[0]
        conn.close()
    except Exception:
        log.warning("Could not resolve CURRENT_USER; using fallback", exc_info=True)
        username = "you"

    session_id = py_secrets.token_hex(32)
    _sessions[session_id] = {"token": access_token, "username": username}
    log.info("OAuth login succeeded for user=%s", username)

    response = RedirectResponse("/", status_code=302)
    response.set_cookie("session_id", session_id, httponly=True, secure=True, samesite="lax")
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session(request: gr.Request) -> dict | None:
    """Return the session dict for the current request, or None."""
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
    with open("/snowflake/session/token") as f:
        svc_token = f.read()
    return snowflake.connector.connect(
        account=ACCOUNT, host=HOST, authenticator="oauth", token=svc_token,
    )


def _connect_as_user(token: str) -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=ACCOUNT, host=HOST, authenticator="oauth", token=token,
        warehouse=WAREHOUSE, database=DATABASE, schema=SCHEMA,
    )


# ── Gradio functions ──────────────────────────────────────────────────────────

def query_as_service() -> tuple[pd.DataFrame, str]:
    """Query finance_data as the service user — expected to fail."""
    try:
        conn = _connect_as_service()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, region, metric, amount FROM {DATABASE}.{SCHEMA}.{TABLE} ORDER BY id"
            )
            df = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
        conn.close()
        return df, "Unexpected: service user can query the table. Check CALLER grants."
    except Exception as exc:
        return pd.DataFrame(), (
            "**Expected** — service user cannot query `finance_data`:\n\n"
            f"```\n{type(exc).__name__}: {exc}\n```"
        )


def query_as_user(request: gr.Request) -> tuple[pd.DataFrame, str]:
    """Query finance_data using the logged-in user's OAuth token."""
    session = _get_session(request)
    if not session:
        return pd.DataFrame(), "Not logged in — click **Login with Snowflake**."
    try:
        conn = _connect_as_user(session["token"])
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, region, metric, amount FROM {DATABASE}.{SCHEMA}.{TABLE} ORDER BY id"
            )
            df = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
        conn.close()
        return df, f"Loaded **{len(df)}** row(s) as `{session['username']}`."
    except Exception as exc:
        log.exception("OAuth query failed")
        return pd.DataFrame(), (
            f"Query failed — make sure `FINANCE_ROLE` is granted to `{session['username']}`:\n\n"
            f"```\n{type(exc).__name__}: {exc}\n```"
        )


def oauth_widget(request: gr.Request) -> tuple[dict, dict, str]:
    """Return (login_btn_update, oauth_btn_update, switch_html) based on login state."""
    session = _get_session(request)
    if session:
        username = session["username"]
        return (
            gr.update(visible=False),
            gr.update(visible=True, value=f"Load as {username}"),
            '<a href="/login" target="_top" style="font-size:13px;color:#666">switch user</a>',
        )
    if OAUTH_CONFIGURED:
        return gr.update(visible=True), gr.update(visible=False), ""
    return (
        gr.update(visible=True, value="OAuth not configured — run setup.sql and restart."),
        gr.update(visible=False),
        "",
    )


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Finance data viewer — OAuth credentials") as demo:
    gr.Markdown(
        "# Finance data viewer\n"
        "The **service owner role** has no `SELECT` on `finance_data`.  "
        "Only a user authenticated via **Snowflake OAuth** who has `FINANCE_ROLE` "
        "can query the table — the service acts on behalf of that user, not as itself."
    )

    with gr.Row():
        svc_btn     = gr.Button("Load as service user")
        login_btn   = gr.Button("Login with Snowflake")
        oauth_btn   = gr.Button(visible=False)
        switch_html = gr.HTML()

    status_md = gr.Markdown()
    data_tbl  = gr.Dataframe(label="finance_data")

    demo.load(fn=oauth_widget, outputs=[login_btn, oauth_btn, switch_html])
    svc_btn.click(fn=query_as_service, outputs=[data_tbl, status_md])
    login_btn.click(fn=None, js="() => { window.top.location.href = '/login'; }")
    oauth_btn.click(fn=query_as_user, outputs=[data_tbl, status_md])


# ── Mount Gradio into FastAPI and run ─────────────────────────────────────────

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
