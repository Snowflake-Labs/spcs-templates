#! /bin/bash

python -u ./spcs_runner/spcs_runner.py --nproc_per_node=1 --nnodes=${NUM_NODES} --master_port=29500 ./cifar10_dist_training/main.py
