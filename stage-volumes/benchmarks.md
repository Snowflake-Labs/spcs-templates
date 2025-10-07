# Stage Volume Benchmarking

## Setup

All experiments are run with 3Gi memory limit and 3 CPU limit for the stage volume.

- `parallel_rsync_flat.py` : Runs rsync -a with multiple workers between the source and destination directory to copy files: From stage volume to local disk/ block storage
- `script-chdir-threadpool.py` : Changes working dir `os.chdir()` to the actual directory containing files and copies all files to destination directory using simple `os.listdir()` + `shutil.copy2`. Uses `ThreadPoolExecutor` for parallelism using multiple threads
- `file-generator.py` : Generates 15MB (configurable) files and writes to stage volume using `ThreadPoolExecutor`

## Results

- Reading ~30k 1MB files - ~600-650 Mbps networking bandwidth achieved
- Reading ~20k 15MB files - ~4 Gbps bandwidth achieved with 64 workers. Couple of scripts achieve the same bandwidth- `read-chdir-threadpool.py` and `read-rsync.py`.
- Writing ~20k 15MB files - ~6.5 Gbps bandwidth achieved with 64 workers- `file-generator.py`.
- Writing 512 1GB files- ~6.5 Gbps bandwidth achieved with 64 workers- `file-generator.py`.
- Reading 600 1GB files - ~4 Gbps bandwidth achieved with 64 workers - `read-rsync.py`
