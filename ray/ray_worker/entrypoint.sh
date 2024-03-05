#!/bin/bash
set -e  # Exit on command errors
set -x  # Print each command before execution, useful for debugging
if [ -z "${RAY_HEAD_ADDRESS}" ]; then
    echo "Error: RAY_HEAD_ADDRESS not set"
    exit 1
fi

ray start \
    --verbose \
    --block \
    --address=${RAY_HEAD_ADDRESS} \
    --object-manager-port=8076 \
    --node-manager-port=8077 \
    --runtime-env-agent-port=8078 \
    --dashboard-agent-grpc-port=8079 \
    --dashboard-agent-listen-port=8081 \
    --metrics-export-port=8082 \
    --dashboard-host=0.0.0.0 \
    --min-worker-port=10002 \
    --max-worker-port=10005
