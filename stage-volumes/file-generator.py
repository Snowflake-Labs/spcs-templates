#!/usr/bin/env python3

import os
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from secrets import token_bytes
from pathlib import Path

# Constants
OUTPUT_DIR = "/mnt/stage/TEST_BP_APP_USER_SCHEMA/data-persist-dir/materialize/tables/v0__b8481b904854cb31b66b1532a68cbac9/1739849135/1758092781218882556/"
TOTAL_WORKERS = 64
FILE_SIZE = 15 * 1024 * 1024  # 15MB
FILES_TO_GENERATE = 10000  # Total files to generate

def generate_random_data(size):
    """Creates a byte array of the specified size with random data"""
    return token_bytes(size)

def write_file(directory):
    """Creates a 15MB file with UUID name at the specified directory"""
    # Generate UUID for filename
    file_uuid = uuid.uuid4()
    filename = f"{file_uuid}.15MB"
    filepath = Path(directory) / filename

    try:
        # Generate 15MB of random data
        data = generate_random_data(FILE_SIZE)

        # Write file
        with open(filepath, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"Error writing file {filepath}: {e}")
        return False

def file_worker(worker_id, directory, files_per_worker):
    """Generates files in the specified directory"""
    local_success = 0
    print(f"Worker {worker_id} starting - generating {files_per_worker} files")

    for i in range(files_per_worker):
        if write_file(directory):
            local_success += 1

        # Progress update every 50 files
        if (i + 1) % 50 == 0:
            print(f"Worker {worker_id}: {i + 1}/{files_per_worker} files completed")

    print(f"Worker {worker_id} completed - successfully wrote {local_success} files")
    return local_success

def main():
    print("Starting 15MB file generation...")
    print("Configuration:")
    print(f"- Total workers: {TOTAL_WORKERS}")
    print(f"- File size: {FILE_SIZE // (1024 * 1024)} MB")
    print(f"- Files to generate: {FILES_TO_GENERATE}")
    print(f"- Target directory: {OUTPUT_DIR}")

    # Create directory if it doesn't exist
    try:
        os.makedirs(OUTPUT_DIR, mode=0o755, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory: {e}")
        return 1

    files_per_worker = FILES_TO_GENERATE // TOTAL_WORKERS

    start_time = time.time()

    # Use ThreadPoolExecutor for concurrent execution
    with ThreadPoolExecutor(max_workers=TOTAL_WORKERS) as executor:
        futures = []

        # Start all workers
        print(f"\nStarting {TOTAL_WORKERS} workers...")
        for i in range(TOTAL_WORKERS):
            local_files_per_worker = files_per_worker
            # Last worker gets any remaining files
            if i == TOTAL_WORKERS - 1:
                local_files_per_worker += FILES_TO_GENERATE % TOTAL_WORKERS
            future = executor.submit(
                file_worker,
                i + 1,
                OUTPUT_DIR,
                local_files_per_worker
            )
            futures.append(future)

        # Wait for all workers to complete and collect results
        print("\nWaiting for all workers to complete...")
        worker_results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                worker_results.append(result)
            except Exception as e:
                print(f"Worker failed with error: {e}")
                worker_results.append(0)

    duration = time.time() - start_time

    # Sum up all worker results
    total_files_created = sum(worker_results)

    # Print results
    print("\n=== Generation Complete ===")
    print(f"Duration: {duration:.2f}s")
    print(f"Files successfully created: {total_files_created}")
    print(f"Expected total: {FILES_TO_GENERATE}")

    if total_files_created == FILES_TO_GENERATE:
        print("All files generated successfully!")
    else:
        print(f"Some files failed to generate. Missing: {FILES_TO_GENERATE - total_files_created} files")

    return 0

if __name__ == "__main__":
    exit(main())
