# SPCS Authentication Demo Scripts

Welcome to the **SPCS Authentication Demos**.  This collection of small Python scripts shows several common ways to obtain an access token for Snowflake Platform Connectivity Services (SPCS) and use that token to call downstream applications.

## Folder structure

* `token_demo.py` – Demonstrates using a **Programmatic Access Token (PAT) or External Oauth Token** and forwarding it to an SPCS-enabled application.
* `external_browser_demo.py` – Implements the **External-Browser OAuth flow**.  The script launches your browser, completes the PKCE dance, and prints the resulting Snowflake access token.

## Prerequisites

1. Python 3.8+  
2. Network reachability to your SPCS endpoints.

## Configure Snowflake OAuth Integration

Before running the demos you need an OAuth integration configured in your Snowflake account.  Below is a minimal example for a **public** client.  Adjust values as needed (e.g., use `CONFIDENTIAL` and set a client secret if required).

```sql
CREATE SECURITY INTEGRATION demo_oauth
  TYPE = OAUTH
  ENABLED = TRUE
  OAUTH_CLIENT = CUSTOM
  OAUTH_CLIENT_TYPE = 'PUBLIC'         -- 'CONFIDENTIAL' if you need client secret
  OAUTH_REDIRECT_URI = 'http://localhost:8080/callback'
  OAUTH_ISSUE_REFRESH_TOKENS = TRUE
  OAUTH_ALLOW_NON_TLS_REDIRECT_URI = TRUE;
```

After creation, retrieve the client ID (and secret, if confidential):

```sql
SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('DEMO_OAUTH');
```

Use the returned `CLIENT_ID` (and `CLIENT_SECRET` where applicable) with the demo scripts via environment variables or command-line flags.

## Usage

Each script can be executed directly from this directory, e.g.

```bash
python token_demo.py
```

Refer to the inline comments of each script for configuration details.

### Running the External-Browser OAuth demo

```bash
# Using environment variables (recommended)
export SNOWFLAKE_ACCOUNT_URL="https://<your-account>.snowflakecomputing.com"
export SNOWFLAKE_CLIENT_ID="my_cli_app"
# Optional for confidential clients
# export SNOWFLAKE_CLIENT_SECRET="<secret>"

python external_browser_demo.py

# Or supply parameters directly via flags
python external_browser_demo.py \
  --account https://<your-account>.snowflakecomputing.com \
  --client-id my_cli_app \
  --redirect http://localhost:8080/callback \
  --scopes "session:role:ALL_ACCESS"

# Any value not provided via a flag or environment variable will be prompted interactively.
```