#!/usr/bin/env python3
"""
Demo: Snowflake OAuth External-Browser Flow
==========================================

This script launches your default web browser to perform the Snowflake OAuth
PKCE flow and prints the resulting access token (and optional refresh token).

Configuration can be supplied via command-line arguments, environment
variables, or interactive prompts.

Required parameters:
  • Snowflake account URL        – env `SNOWFLAKE_ACCOUNT_URL`  or `--account`
  • OAuth client ID              – env `SNOWFLAKE_CLIENT_ID`    or `--client-id`

Optional parameters:
  • Redirect URI                 – env `SNOWFLAKE_REDIRECT_URI` or `--redirect`
  • OAuth scopes (space-separated) – env `SNOWFLAKE_SCOPES`      or `--scopes`
  • Client secret (confidential clients only) – env `SNOWFLAKE_CLIENT_SECRET`

Example:
    export SNOWFLAKE_ACCOUNT_URL="https://myaccount.snowflakecomputing.com"
    export SNOWFLAKE_CLIENT_ID="my_cli_app"
    python external_browser_demo.py

Running without environment variables:

    python external_browser_demo.py \
      --account https://myaccount.snowflakecomputing.com \
      --client-id my_cli_app \
      --redirect http://localhost:8080/callback \
      --scopes "session:role:<ROLE_NAME>"

You’ll be prompted for any value not supplied via a flag or environment variable.

"""
from __future__ import annotations

import os
import sys
import argparse
import json
# Standard libs
import base64
import hashlib
import secrets
import urllib.parse
import webbrowser
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import requests

# ---------------------------------------------------------------------------
# Minimal OAuth helper (stand-alone – no external import required)
# ---------------------------------------------------------------------------


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the authorization code from the redirect"""

    def do_GET(self):  # noqa: N802 – method name required by BaseHTTPRequestHandler
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            self.server.auth_code = params["code"][0]  # type: ignore[attr-defined]
            self.server.auth_state = params.get("state", [None])[0]  # type: ignore[attr-defined]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            success_html = "<h1>Authentication successful. You may close this window.</h1>"
            self.wfile.write(success_html.encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>OAuth error</h1>")

    def log_message(self, *_):  # silence default logging
        return


class SnowflakeOAuth:
    """Lightweight helper for Snowflake OAuth PKCE flow (browser-based)."""

    def __init__(self, account_url: str, client_id: str, client_secret: str | None = None, redirect_uri: str | None = None):
        self.account_url = account_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or "http://localhost:8080/callback"

        parsed = urllib.parse.urlparse(self.redirect_uri)
        self._callback_port = parsed.port or 8080

    # ------------------------------------------------------------------
    # PKCE helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        return verifier, challenge

    # ------------------------------------------------------------------
    # Flow helpers
    # ------------------------------------------------------------------

    def _auth_url(self, state: str, code_challenge: str, scopes: list[str]) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.account_url}/oauth/authorize?" + urllib.parse.urlencode(params)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def authenticate(self, scopes: list[str]) -> dict:

        verifier, challenge = self._pkce_pair()
        state = secrets.token_urlsafe(32)

        url = self._auth_url(state, challenge, scopes)

        # Start minimal callback server
        server: HTTPServer = HTTPServer(("localhost", self._callback_port), _OAuthCallbackHandler)
        server.auth_code = None  # type: ignore[attr-defined]
        server.auth_state = None  # type: ignore[attr-defined]
        server.auth_error = None  # type: ignore[attr-defined]

        Thread(target=server.serve_forever, daemon=True).start()

        print(f"🌐 Opening browser for authentication … ({url})")
        print(f"📍 Callback listening on {self.redirect_uri}")
        webbrowser.open(url)

        print("⏳ Waiting for user to complete login …")
        start = time.time()
        while server.auth_code is None and time.time() - start < 300:
            time.sleep(0.3)

        server.shutdown()

        if server.auth_code is None:
            raise TimeoutError("No authorization code received within 5 minutes.")

        if server.auth_state != state:
            raise RuntimeError("OAuth state mismatch – possible CSRF attack.")

        # Exchange code for token
        token_url = f"{self.account_url}/oauth/token-request"
        data = {
            "grant_type": "authorization_code",
            "code": server.auth_code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": verifier,
            "client_id": self.client_id,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.client_secret:
            basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"

        resp = requests.post(token_url, data=data, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Token exchange failed: {resp.status_code} – {resp.text}")

        print("🎉 Authentication successful!")
        return resp.json()


# ---------------------------------------------------------------------------
# SPCS API helper
# ---------------------------------------------------------------------------


def call_spcs_api(token: str):
    """Prompt user for an SPCS endpoint and make a POST request with the token."""
    api_url = os.getenv("SPCS_API_URL") or input("Enter the SPCS endpoint URL: ").strip()
    if not api_url:
        print("❌ No URL provided – skipping API call.")
        return

    payload_default = "Hello from external-browser demo!"
    payload = os.getenv("SPCS_API_DATA") or input(f"Input payload (default: '{payload_default}'): ").strip() or payload_default

    headers = {
        "Authorization": f'Snowflake Token="{token}"',
        "X-SF-SPCS-Authentication-Method": "OAUTH",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "ExternalBrowserDemo/1.0",
    }

    print("\n⏳ Sending request …")
    print(headers)
    print(payload)
    print(api_url)
    try:
        resp = requests.get(api_url, headers=headers, data={"input": payload}, timeout=30)
    except requests.exceptions.RequestException as exc:
        print(f"❌ Request failed: {exc}")
        return

    print(f"\nStatus: {resp.status_code}")
    try:
        print(resp.json())
    except ValueError:
        print(resp.text[:1000])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Snowflake OAuth External-Browser Demo")
    parser.add_argument("--account", help="Snowflake account URL (e.g. https://xyz.snowflakecomputing.com)")
    parser.add_argument("--client-id", help="OAuth client ID")
    parser.add_argument("--redirect", help="Redirect URI (default: http://localhost:8080/callback)")
    parser.add_argument("--scopes", help="Space-separated list of OAuth scopes")
    parser.add_argument("--client-secret", help="OAuth client secret (for confidential clients)")
    return parser.parse_args()


def resolve_param(cli_value: str | None, env_var: str, prompt: str | None = None) -> str:
    if cli_value:
        return cli_value
    env_val = os.getenv(env_var)
    if env_val:
        return env_val
    if prompt:
        try:
            return input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            sys.exit(1)
    raise ValueError(f"Parameter not provided and environment variable {env_var} not set")


def main():
    args = parse_args()

    account_url = resolve_param(args.account, "SNOWFLAKE_ACCOUNT_URL", "Snowflake account URL: ")
    client_id   = resolve_param(args.client_id, "SNOWFLAKE_CLIENT_ID", "OAuth client ID: ")
    client_secret = args.client_secret or os.getenv("SNOWFLAKE_CLIENT_SECRET")
    redirect_uri  = args.redirect or os.getenv("SNOWFLAKE_REDIRECT_URI")
    scopes_str    = args.scopes or os.getenv("SNOWFLAKE_SCOPES")
    scopes        = scopes_str.split()

    oauth = SnowflakeOAuth(account_url, client_id, client_secret, redirect_uri)

    try:
        token_response = oauth.authenticate(scopes=scopes)
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)

    print("\n=== Token Response ===")
    print(json.dumps(token_response, indent=2))

    access_token = token_response.get("access_token")
    if access_token:
        print("\n🔑 Access token:")
        print(access_token)

    refresh_token = token_response.get("refresh_token")
    if refresh_token:
        print("\n💾 Refresh token:")
        print(refresh_token)


    call_spcs_api(access_token)
    print("\n✅ Done!") 


if __name__ == "__main__":
    main()
