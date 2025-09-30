#!/usr/bin/env python3
#
# SCRIPT: parallel_rsync_flat.py
#
# PURPOSE:
# Accelerates copying a large number of files from a single source directory
# to a local destination, particularly when the source is a high-latency
# filesystem like a Stage Mount.
#
# HOW IT WORKS:
# 1.  It first performs a single scan of the source directory to get a
#     complete list of all filenames. This initial scan is serial.
# 2.  The script then divides this large file list into smaller, more
#     manageable "chunks".
# 3.  It uses a thread pool to launch multiple `rsync` processes in parallel.
#     The number of parallel processes is controlled by the --workers flag.
# 4.  Each `rsync` process is assigned one chunk of files to copy. This is
#     achieved by writing the chunk's file list to a temporary file and
#     passing that path to rsync's `--files-from=` argument.
# 5.  The temporary files are securely created and automatically deleted
#     upon completion.
#
# USAGE:
# The --workers (-w) flag sets the number of simultaneous rsync jobs. A good
# starting value is 10-20, but the optimal number depends on your number of vCPUS.
#
#
# Example:
# python3 parallel_rsync_flat.py /path/to/source /path/to/dest --workers 16
#
import subprocess
import os
import argparse
import tempfile
from concurrent.futures import ThreadPoolExecutor

def run_rsync_on_file_list(source_dir, dest_dir, file_list_path):
    """Runs rsync using a --files-from list."""
    # -a: archive mode
    # --partial: resumes interrupted transfers
    # --files-from: reads the list of files to sync from the given file
    command = [
        "rsync",
        "-a",
        "--partial",
        f"--files-from={file_list_path}",
        source_dir,
        dest_dir
    ]

    try:
        # Using check=True to raise an exception on rsync errors
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return None  # Success
    except subprocess.CalledProcessError as e:
        error_message = f"❌ rsync process failed: {e.stderr}"
        print(error_message)
        return error_message  # Failure

def main(source_dir, dest_dir, workers):
    """
    Scans a single directory for files and runs rsync on chunks of that list in parallel.
    """
    print(f"Scanning for files in '{source_dir}'... (This may take a while)")
    try:
        # This initial scan is serial and will be slow on a Stage Mount
        all_files = [f.name for f in os.scandir(source_dir) if f.is_file() and f.name.endswith(".1GB")]
    except FileNotFoundError:
        print(f"Error: Source directory '{source_dir}' not found.")
        return

    if not all_files:
        print("No files found in the source directory.")
        return

    print(f"Found {len(all_files)} files. Dividing into {workers} chunks for parallel processing.")

    # Split the list of files into N chunks for the workers
    chunk_size = (len(all_files) + workers - 1) // workers
    file_chunks = [all_files[i:i + chunk_size] for i in range(0, len(all_files), chunk_size)]

    errors = []
    with ThreadPoolExecutor(max_workers=workers) as executor, \
         tempfile.TemporaryDirectory() as temp_dir:

        futures = []
        for i, chunk in enumerate(file_chunks):
            # Create a temporary file containing the list of filenames for this chunk
            list_path = os.path.join(temp_dir, f"chunk_{i}.txt")
            with open(list_path, 'w') as f:
                for filename in chunk:
                    f.write(filename + '\n')

            # Submit the rsync job for this chunk
            futures.append(executor.submit(run_rsync_on_file_list, source_dir, dest_dir, list_path))

        for future in futures:
            error = future.result()
            if error:
                errors.append(error)

    print("\n--- Summary ---")
    if not errors:
        print("✅ All parallel copy tasks completed successfully.")
    else:
        print(f"Completed with {len(errors)} errors.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run rsync in parallel on a flat directory.",
        epilog="Example: python3 parallel_rsync_flat.py /path/to/source /path/to/dest --workers 16"
    )
    parser.add_argument("source_directory", help="The source Stage Mount directory.")
    parser.add_argument("destination_directory", help="The local destination directory.")
    parser.add_argument("-w", "--workers", type=int, default=10, help="Number of parallel rsync processes.")
    args = parser.parse_args()

    main(args.source_directory, args.destination_directory, args.workers)