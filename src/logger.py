"""Logging setup for MBM Mod Loader.

Creates a "_mbm_logs" folder next to the script (only if missing) and writes to
a daily log file named "DD-MM-YYYY_log.txt". Existing files are appended to.

Log line format: "DD-MM-YYYY hh-mm-ss | LEVEL | Message" (24-hour clock).
"""

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR_NAME = "_mbm_ml_logs"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"   # 24-hour clock
FILE_DATE_FORMAT = "%d-%m-%Y"        # used for the log file name

_LOGGER_NAME = "mbm"


def get_log_dir() -> Path:
    """Return the log directory (next to this script), creating it if missing."""
    log_dir = Path(__file__).resolve().parent.parent / LOG_DIR_NAME
    log_dir.mkdir(exist_ok=True)
    return log_dir


def get_log_file() -> Path:
    """Return today's log file path: DD-MM-YYYY_log.txt."""
    file_name = f"{datetime.now().strftime(FILE_DATE_FORMAT)}_log.txt"
    return get_log_dir() / file_name


def write_separator(logger: logging.Logger) -> None:
    """Append a visual separator line directly to the log file."""
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
            with open(handler.baseFilename, "a", encoding="utf-8") as f:
                f.write("-" * 60 + "\n")
            break


def setup_logger() -> logging.Logger:
    """Configure and return the application logger.

    Logs are appended to today's file (the file is kept if it already exists).
    Calling this more than once is safe — handlers are not duplicated.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger  # already configured

    handler = logging.FileHandler(get_log_file(), mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(handler)

    return logger
