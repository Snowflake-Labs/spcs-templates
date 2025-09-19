#!/usr/bin/env python3
import concurrent.futures
import os
import shutil


def worker_for_files(args):
    """Worker that handles a list of files."""
    dst_dir, file_list = args
    copied = 0
    print(f"Worker processing {len(file_list)} files")
    for filename in file_list:
        try:
            shutil.copy2(filename, os.path.join(dst_dir, filename))
            copied += 1
        except Exception as e:
            print(f"ERROR copying {filename}: {e}")
    return copied

def get_all_file_paths():
    return os.listdir(".")

def main():
    src_dir = "/mnt/stage/TEST_BP_APP_USER_SCHEMA/data-persist-dir/materialize/tables/v0__b8481b904854cb31b66b1532a68cbac9/1739849135/1758092781218882556/"
    dst_dir = "/mnt/block"
    workers = 64
    print("Getting file list...")

    # Chdir helps to avoid performing inode lookups to get to the innermost directory for each file, which reduce number of metadata operations performed for each file
    os.chdir(src_dir)

    all_files = get_all_file_paths()
    print(f"Found {len(all_files)} files to copy")

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
            tasks.append((dst_dir, worker_files))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        results = executor.map(worker_for_files, tasks)
        print(f"Copied {sum(results)} files")


if __name__ == "__main__":
    main()
