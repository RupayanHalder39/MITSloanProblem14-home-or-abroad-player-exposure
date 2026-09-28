"""Logging helpers so all scripts have a consistent console + file log."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_log(name: str = "nti", level: int = logging.INFO) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(level)
    if log.handlers:  # avoid duplicate handlers when scripts are re-run in-process
        return log
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    log.propagate = False
    return log


def add_file_handler(log: logging.Logger, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    log.addHandler(fh)


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")