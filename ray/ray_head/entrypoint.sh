#!/bin/bash
set -e  # Exit on command errors
set -x  # Print each command before execution, useful for debugging
export log_dir="/raylogs/ray"
echo "Making log directory $log_dir..."
mkdir -p $log_dir

ray start \
  --head \
  --disable-usage-stats \
  --port=6379 \
  --dashboard-port=8265 \
  --object-manager-port=8076 \
  --node-manager-port=8077 \
  --runtime-env-agent-port=8078 \
  --dashboard-agent-grpc-port=8079 \
  --dashboard-grpc-port=8080 \
  --dashboard-agent-listen-port=8081 \
  --metrics-export-port=8082 \
  --ray-client-server-port=10001 \
  --min-worker-port=10002 \
  --max-worker-port=10005 \
  --dashboard-host=0.0.0.0 \
  --temp-dir=/raylogs/ray \
  --block \
  --verbose
