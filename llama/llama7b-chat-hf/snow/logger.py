#!/usr/bin/env python3

import logging


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
