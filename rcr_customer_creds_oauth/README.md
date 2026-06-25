# rcr_customer_creds_oauth

SPCS sample demonstrating **customer-provided OAuth credentials** (interactive authorization-code flow).

A Gradio web app lets you log in as your own Snowflake user via OAuth. The service owner role has no `SELECT` on `finance_data`; the app makes that visible by trying (and failing) to query the table as the service user in Step 1. After you log in via OAuth in Step 2, the same query succeeds — because the service now runs it on your behalf, and your user has `FINANCE_ROLE`.

Reference: [SPCS docs — Connect to Snowflake by using customer-provided credentials](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/spcs-execute-sql#connect-to-snowflake-by-using-customer-provided-credentials)

## What it demonstrates

- Service owner role intentionally has **no direct access** to the data table
- `capabilities.securityContext.enableCustomCredentials: true` in the service spec
- `GRANT CALLER ...` on `service_owner_role` to scope what the service may do on behalf of the OAuth user
- Interactive OAuth **authorization-code flow**: browser → Snowflake authorize → callback → token exchange — all within the Snowflake network
- The app derives `redirect_uri` from the HTTP `Host` header, so no URL needs to be hardcoded in the service spec
- Token exchange uses `SNOWFLAKE_HOST` (internal endpoint) to keep traffic inside the Snowflake network

## Files

| File | What it does |
| --- | --- |
| `setup.sql` | Complete setup in one script: roles, DB, schema, warehouse, compute pool, table, network policy, CALLER grants, image repo, service, OAuth integration, secret |
| `ui/Dockerfile` | `python:3.11-slim`, installs deps, runs `uvicorn` |
| `ui/requirements.txt` | Python dependencies |
| `ui/app.py` | FastAPI (`/login`, `/callback`) + Gradio UI; handles the OAuth flow end-to-end |

## Walkthrough

```bash
# ── 1. Build and push the image ─────────────────────────────────────────────
cd ui
docker build --platform linux/amd64 -t rcr-customer-creds-oauth:dev .
snow spcs image-registry login
docker tag rcr-customer-creds-oauth:dev <repository_url>/rcr-customer-creds-oauth:dev
docker push <repository_url>/rcr-customer-creds-oauth:dev

# ── 2. Run setup.sql (as ACCOUNTADMIN) ──────────────────────────────────────
# Edit the SET block at the top if you want different names.
# Grant FINANCE_ROLE to yourself (uncomment the GRANT line near the top).
# Replace <repository_url> in the CREATE SERVICE spec.
#
# The script has two ▶▶ STOP markers where you paste in values before continuing:
#   Stop 1 — paste the endpoint URL from SHOW ENDPOINTS IN SERVICE
#   Stop 2 — paste OAUTH_CLIENT_ID + OAUTH_CLIENT_SECRET from SYSTEM$SHOW_OAUTH_CLIENT_SECRETS

# ── 3. Open the endpoint ─────────────────────────────────────────────────────
# • Step 1 on the page shows the service owner failing to query finance_data.
# • Click "Login with Snowflake" → OAuth consent → redirect back to the app.
# • Step 2 shows the finance data (because your user has FINANCE_ROLE).
```

## Cleanup

```sql
DROP SERVICE    rcr_oauth_db.rcr_oauth.rcr_oauth_app;
DROP INTEGRATION rcr_oauth_integration;
DROP DATABASE   rcr_oauth_db;
DROP COMPUTE POOL rcr_oauth_pool;
DROP WAREHOUSE  rcr_oauth_wh;
DROP ROLE       rcr_oauth_service_owner;
DROP ROLE       rcr_oauth_finance;
DROP NETWORK POLICY rcr_oauth_policy;
DROP NETWORK RULE   rcr_oauth_pool_rule;
```
