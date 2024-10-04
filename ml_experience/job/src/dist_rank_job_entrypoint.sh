#! /bin/bash

python -u ./spcs_runner/spcs_runner.py --nproc_per_node=4 --nnodes=${NUM_NODES} --master_port=29500 ./dist_rank_job/main.py
