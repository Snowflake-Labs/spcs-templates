#!/bin/bash

exec python3 ./exec/exec.py \
  --command 'python3 -m fastchat.serve.model_worker --model-path meta-llama/Llama-2-7b-chat-hf' \
  --wait_condition_location ${SYNC_DIR}/controller \
  --write_condition_location ${SYNC_DIR}/worker \
  --write_condition 'Uvicorn running'
