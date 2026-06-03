# rcr_customer_creds

SPCS sample showing a service that connects back to Snowflake with **customer-provided credentials** (Programmatic Access Tokens) instead of the auto-injected service OAuth token. The container hosts a Gradio web app with a Finance / Marketing dropdown. Each team has its own service user + PAT; switching the dropdown switches which PAT the backend uses, and a row access policy filters `team_data` accordingly.

Reference: [SPCS docs — Connect to Snowflake by using customer-provided credentials](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/spcs-execute-sql#connect-to-snowflake-by-using-customer-provided-credentials).

## What it demonstrates

- Two `TYPE = SERVICE` users with PATs, one per team
- PATs stored in Snowflake `SECRET` objects (`TYPE = password`) and mounted into the container as env vars
- Service spec with `capabilities.securityContext.enableCustomCredentials: true`
- `TYPE = COMPUTE_POOL`, `MODE = INGRESS` network rule on the service users so PATs can authenticate from inside the SPCS pool
- `GRANT CALLER ...` on `service_owner_role` so the calling user's privileges are scoped down to what the service is allowed to do
- A row access policy on `team_data` keyed on `CURRENT_ROLE()`

## Files

| File | What it does |
| --- | --- |
| `setup.sql` | Creates roles, db, schema, warehouse, compute pool, table, RAP, service users, PATs, secrets, network policy, caller grants, image repo |
| `create_service.sql` | Creates the SPCS service (mounts both secrets, enables custom credentials) |
| `ui/Dockerfile` | `python:3.11-slim`, installs `gradio` + `snowflake-connector-python>=4.5.0` |
| `ui/requirements.txt` | Python dependencies |
| `ui/app.py` | Gradio app: dropdown -> per-team cached connection -> `SELECT * FROM team_data` |

## Walkthrough

```bash
# 1. Run setup.sql in your worksheet (as ACCOUNTADMIN)
#    Edit the SET block at the top to use your own names if you want.

# 2. Build and push the image. After setup.sql runs, copy the
#    "repository_url" from SHOW IMAGE REPOSITORIES.
cd ui
docker build --platform linux/amd64 -t rcr-customer-creds:dev .
snow spcs image-registry login
docker tag rcr-customer-creds:dev <repository_url>/rcr-customer-creds:dev
docker push <repository_url>/rcr-customer-creds:dev

# 3. Edit create_service.sql, replacing <repository_url> with the value above.
#    Run create_service.sql.

# 4. Open the public endpoint shown by SHOW ENDPOINTS IN SERVICE.
#    Default Finance dropdown shows only team='FINANCE' rows.
#    Switch to Marketing -> only team='MARKETING' rows.
```

## Customizing names

`setup.sql` and `create_service.sql` both have a `SET` block at the top. Edit those values to use different identifiers, or uncomment the PM-account override block to deploy with the `yavorg_*` names into `yavorg_spcs_tuts.rcr`.

## Cleanup

```sql
DROP SERVICE app_db.rcr.rcr_customer_creds_app;
DROP USER finance_service_user;
DROP USER marketing_service_user;
DROP NETWORK POLICY rcr_service_users_policy;
DROP NETWORK RULE rcr_compute_pool_rule;
DROP DATABASE app_db;
DROP COMPUTE POOL app_compute_pool;
DROP WAREHOUSE app_wh;
DROP ROLE service_owner_role;
DROP ROLE finance_role;
DROP ROLE marketing_role;
```
