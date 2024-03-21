#!/bin/bash

exec python3 ./exec/exec.py \
  --command 'python3 -m fastchat.serve.gradio_web_server' \
  --wait_condition_location ${SYNC_DIR}/worker