#!/usr/bin/env python3

import argparse
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional


def setup_logging(log_level=logging.INFO):
    logger = logging.getLogger("setup")
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


log = setup_logging()


def _condition_fulfilled(line: str, condition: str) -> bool:
    if not condition:
        return False
    return condition.lower() in line.lower()


def _write_wait_condition(location: str) -> None:
    path = Path(location)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        file.write("fulfilled")
    log.info("Write condition fulfilled")


def _process_stream(data: Optional[str], prefix: str, write_condition_location: str, write_condition: str) -> None:
    if not data:
        return
    log.info(f"{prefix}: {data}")
    if _condition_fulfilled(data, write_condition):
        _write_wait_condition(write_condition_location)


def run_cmd_and_stream(cmd: str, write_condition_location: str, write_condition: str) -> None:
    log.info(f"Executing: {cmd}")
    cmd = cmd.split(" ")
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                               universal_newlines=True, encoding='utf8',
                               bufsize=1, close_fds=True)

    try:
        for stderr_line in iter(process.stderr.readline, b""):
            if not stderr_line:
                time.sleep(0.01)
                continue
            _process_stream(stderr_line, "[STDERR]", write_condition_location, write_condition)
    except KeyboardInterrupt as e:
        process.kill()
        raise e


def wait_for_condition(condition_location: str, timeout_seconds: int = 600) -> None:
    path = Path(condition_location)
    start_time_ms = round(time.time() * 1000)
    end_time_ms = start_time_ms + timeout_seconds * 1000
    while end_time_ms > start_time_ms:
        if path.is_file():
            return
        else:
            log.info(f"Waiting for condition: {condition_location}")
            time.sleep(5)
    raise Exception(
        f"Timeout waiting for condition: {condition_location}, check logs of depending service")


def main():
    parser = argparse.ArgumentParser(description="Exec")

    parser.add_argument("--command", required=True, help="Command to execute")
    parser.add_argument("--wait_condition_location", required=False, help="Condition location to wait before execution")
    parser.add_argument("--write_condition_location", required=False, help="Write condition location")
    parser.add_argument("--write_condition", required=False, help="Write Condition")

    args = parser.parse_args()

    log.info("===============================")
    log.info("Command: %s", args.command)
    log.info("Condition: %s", args.wait_condition_location)
    log.info("Condition: %s", args.write_condition)
    log.info("Condition: %s", args.write_condition_location)
    log.info("===============================")

    if args.wait_condition_location:
        wait_for_condition(args.wait_condition_location)

    run_cmd_and_stream(args.command, args.write_condition_location, args.write_condition)


if __name__ == "__main__":
    main()
