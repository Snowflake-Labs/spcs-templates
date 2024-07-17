#!/bin/bash
snow --config-file="$HOME/config.toml" connection set-default "airflow"
while true; do
    snow --config-file="$HOME/config.toml" git fetch airflow_db.airflow_schema.airflow_dags_repo
    snow --config-file="$HOME/config.toml" sql -q "remove @airflow_db.airflow_schema.airflow_dags"
    snow --config-file="$HOME/config.toml" git copy @airflow_db.airflow_schema.airflow_dags_repo/branches/main/sample_dags @airflow_db.airflow_schema.airflow_dags --parallel 4
    sleep 300
done;
