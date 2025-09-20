#!/usr/bin/env python3
# Simple script to copy *.1GB files from /mnt/stage to /tmp
import concurrent.futures
import os
import shutil

def copy_single_file(src_file):
    """Copy a single file from source to /tmp."""
    dst_dir = "/mnt/block1"
    filename = os.path.basename(src_file)
    dst_file = os.path.join(dst_dir, filename)

    try:
        print(f"Copying {filename}...")
        shutil.copy2(src_file, dst_file)
        print(f"✓ Copied {filename}")
        return 1
    except Exception as e:
        print(f"✗ Error copying {filename}: {e}")
        return 0

def test_copy_1gb_files():
    """Copy all *.1GB files from /mnt/stage to /tmp using parallel workers."""
    src_dir = "/mnt/stage1"

    # Find all *.1GB files using os.listdir and for loop
    files = []
    for filename in os.listdir(src_dir):
        if filename.endswith('.1GB'):
            files.append(os.path.join(src_dir, filename))

    if not files:
        print(f"No *.1GB files found in {src_dir}")
        return

    print(f"Found {len(files)} files to copy")
    # Use parallel workers to copy files
    workers = min(100, len(files))  # Don't use more workers than files

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(copy_single_file, files))

    total_copied = sum(results)
    print(f"\nCopied {total_copied}/{len(files)} files total")

if __name__ == "__main__":
    test_copy_1gb_files()
