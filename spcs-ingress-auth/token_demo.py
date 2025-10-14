#!/usr/bin/env python3
"""
Demo: Forwarding a Programmatic Access Token (PAT) or External OAuth Token to an SPCS-enabled application.

This script shows how to:
1. Read a PAT or External OAuth Token from an environment variable or prompt.
2. Make a POST request to a sample SPCS endpoint, forwarding the PAT in the
   `Authorization` header with the expected `Snowflake Token` scheme.

Provide the URL of the SPCS application you want to call, for example:

    https://my-spcs-app.example.com/hello

Requirements: `requests`
"""

import os
import sys
import json
import getpass
import requests
from typing import Optional

def resolve_api_url() -> str:
    """Determine the target SPCS application URL.

    Order of precedence:
    1. Command-line argument (first positional argument)
    2. Environment variable `SPCS_API_URL`
    3. Interactive prompt
    """

    # 1. CLI arg
    if len(sys.argv) > 1:
        return sys.argv[1]

    # 2. Environment variable
    env_url = os.getenv("SPCS_API_URL")
    if env_url:
        return env_url

    # 3. Prompt
    try:
        return input("Enter the full URL of the SPCS endpoint: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(1)


# Lazily evaluated later to ensure CLI args are captured
API_URL: str | None = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_token() -> str:
    """Return the token from SPCS_TOKEN environment variable or interactive prompt."""
    token = os.getenv("SPCS_TOKEN")
    if token:
        return token

    try:
        # Fallback to interactive prompt (input hidden)
        token = getpass.getpass("Enter your Programmatic Access Token or External OAuth Token (input hidden): ")
        if not token:
            raise ValueError("PAT or External OAuth Token cannot be empty")
        return token.strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(1)


def pretty_print_response(resp: requests.Response):
    """Pretty-print the HTTP response."""
    print("\n=== Response ===")
    print(f"Status : {resp.status_code}")
    print("Headers:")
    for k, v in resp.headers.items():
        print(f"  {k}: {v}")

    print("\nBody:")
    try:
        print(json.dumps(resp.json(), indent=2))
    except ValueError:
        # Not JSON
        print(resp.text[:1000])  # truncate

# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def call_spcs_api(token: str, data: Optional[dict] = None):
    """Call the SPCS endpoint using the supplied Token."""
    headers = {
        "Authorization": f'Snowflake Token="{token}"',
    }

    payload = data or {"input": "Hello from Token demo!"}

    print("\nSending request …")
    resp = requests.post(API_URL, headers=headers, data=payload, timeout=30)
    pretty_print_response(resp)

    if resp.ok:
        print("\n✅ Success – API call completed.")
    elif resp.status_code == 401:
        print("\n❌ Unauthorized – check your Token value and permissions.")
    else:
        print(f"\n⚠️  Received status code {resp.status_code} – see details above.")


if __name__ == "__main__":
    # Resolve endpoint lazily so we can capture CLI args
    API_URL = resolve_api_url()

    print("🌐 SPCS Programmatic Access Token Demo")
    print("=" * 40)
    print(f"Endpoint : {API_URL}\n")

    token = read_token()
    call_spcs_api(token)
