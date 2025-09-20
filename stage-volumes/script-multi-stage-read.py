#!/usr/bin/env python3
import concurrent.futures
import os
import re
import shutil
import random


def worker_for_files(args):
    """Worker that handles a list of files."""
    src_dir, dst_dir, file_list = args
    copied = 0

    print(f"Worker processing {len(file_list)} files")

    # Copy all the files assigned to this worker
    for filename in file_list:
        try:
            src_path = os.path.join(src_dir, filename)
            shutil.copy2(src_path, os.path.join(dst_dir, filename))
            copied += 1
        except Exception:
            pass

    return copied


def main():
    src_dirs = ["/mnt/stage1", "/mnt/stage2", "/mnt/stage3"]

    dst_dir = "/mnt/block1"
    workers = 60

    os.makedirs(dst_dir, exist_ok=True)

    # Get all .dat files in one go with UUID validation
    print("Getting file list...")
    uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    all_files = []
    for f in os.listdir(src_dirs[0]):
        if f.startswith("file_") and f.endswith(".dat"):
            # Check if filename contains a UUID
            if uuid_pattern.search(f):
                all_files.append(f)

    print(f"Found {len(all_files)} valid files with UUIDs to copy")

    # Split files evenly across workers
    files_per_worker = len(all_files) // workers
    tasks = []

    for i in range(workers):
        start_idx = i * files_per_worker
        if i == workers - 1:  # Last worker gets any remaining files
            end_idx = len(all_files)
        else:
            end_idx = (i + 1) * files_per_worker

        worker_files = all_files[start_idx:end_idx]
        src_dir = src_dirs[i % len(src_dirs)]
        if worker_files:  # Only create task if there are files to process
            tasks.append((src_dir, dst_dir, worker_files))

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(tasks)) as executor:
        results = executor.map(worker_for_files, tasks)
        print(f"Copied {sum(results)} files")


if __name__ == "__main__":
    main()
