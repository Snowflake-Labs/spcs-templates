# Stage Volume Benchmarking


## Setup

- `parallel_rsync_flat.py` : Runs rsync -a with multiple workers between the source and destination directory to copy files: From stage volume to local disk/ block storage
- `script-change-working-dir.py` : Changes working dir `os.chdir()` to the actual directory containing files and copies all files to destination directory using simple `os.listdir()` + `shutil.copy2`. Uses `ProcessPoolExecutor` for parallelism using multiple processes
- `script-chdir-threadpool.py` : Runs same workload as `script-change-working-dir.py` but uses `ThreadPoolExecutor` to copy using multiple threads instead of processes- performance remains similar.


## Results

- Experiment: Reading ~67k 1MB files - 700-750 Mbps networking bandwidth achieved
- Experiment: Reading ~20k 15MB files - 6 Gbps bandwidth achieved with 64 workers. Couple of scripts achieve the same bandwidth-