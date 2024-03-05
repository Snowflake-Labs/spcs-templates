#!/bin/bash
set -e  # Exit on command errors
set -x  # Print each command before execution, useful for debugging

export log_dir="/raylogs/ray"
export RAY_SESSION_LATEST_DIR="$log_dir/session_latest"
export RAY_SESSION_LATEST_FILE_NAME="$RAY_SESSION_LATEST_DIR/metrics/grafana/grafana.ini"
until [ -f $RAY_SESSION_LATEST_FILE_NAME ]
do
    echo "Ray session metrics not ready. Waiting..."
    sleep 5
done

export RAY_PROMETHEUS_DATASOURCES="/raylogs/ray/session_latest/metrics/grafana/provisioning/datasources/default.yml"

until [ -f $RAY_PROMETHEUS_DATASOURCES ]
do
    echo "Waiting for prometheus datasources"
    sleep 5
done

export GRAFANA_CONFIG_FILE_PATH="./grafana.ini"
echo "printing grafana config"
cat $GRAFANA_CONFIG_FILE_PATH
ls /tmp/grafanadir
/tmp/grafanadir/bin/grafana-server --config $GRAFANA_CONFIG_FILE_PATH --homepath /tmp/grafanadir web
tail -f /dev/null
