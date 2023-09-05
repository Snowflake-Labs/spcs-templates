#!/bin/bash

exec python3 ./exec/exec.py \
  --command 'python3 -m fastchat.serve.controller' \
  --write_condition_location ${SYNC_DIR}/controller \
  --write_condition 'Uvicorn running'
