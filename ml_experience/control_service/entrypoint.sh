#!/bin/bash
set -e  # Exit on command errors
set -x  # Print each command before execution, useful for debugging

ttyd -p 9090 -W bash &

jupyter lab --generate-config
jupyter lab --ip='0.0.0.0' --port=9091 --no-browser --allow-root --NotebookApp.password='' --NotebookApp.token='' --NotebookApp.iopub_data_rate_limit=1.0e10