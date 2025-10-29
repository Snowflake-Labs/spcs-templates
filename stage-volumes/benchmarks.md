# Stage Volume Concurrent Read/Writes

- `read-rsync.py` : Runs rsync -a with multiple workers between the source and destination directory to copy files from stage volume to local disk
- `file-generator.py` : Generates files and writes to stage volume with multiple workers using `ThreadPoolExecutor`
