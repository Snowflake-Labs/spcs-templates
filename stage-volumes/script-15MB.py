#!/usr/bin/env python3
import concurrent.futures
import os
import shutil


def worker_for_files(args):
    """Worker that handles a list of files."""
    src_dir, dst_dir, file_list = args
    copied = 0
    print(f"Worker processing {len(file_list)} files")
    # Copy all the files assigned to this worker
    for src_path in file_list:
        try:
            # Remove src_dir prefix to get relative path
            relative_path = os.path.relpath(src_path, src_dir)
            dst_path = os.path.join(dst_dir, relative_path)
            # Create destination directory (mkdir -p equivalent)
            dst_dir_path = os.path.dirname(dst_path)
            os.makedirs(dst_dir_path, exist_ok=True)
            # Copy the file
            shutil.copy2(src_path, dst_path)
            copied += 1
        except Exception as e:
            print(f"ERROR copying {src_path}: {e}")
    return copied

def get_all_file_paths_os_walk(directory):
    file_paths = []
    for root, _, files in os.walk(directory):
        for filename in files:
            file_paths.append(os.path.join(root, filename))
    return file_paths


def main():
    src_dir = "/mnt/stage1/local_stage"

    dst_dir = "/mnt/block1"
    workers = 32

    os.makedirs(dst_dir, exist_ok=True)

    # Get all .dat files in one go with UUID validation
    print("Getting file list...")

    all_files = get_all_file_paths_os_walk(src_dir)

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
        if worker_files:  # Only create task if there are files to process
            tasks.append((src_dir, dst_dir, worker_files))

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(tasks)) as executor:
        results = executor.map(worker_for_files, tasks)
        print(f"Copied {sum(results)} files")


if __name__ == "__main__":
    main()
