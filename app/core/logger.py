"""
Central logging configuration for UPT Disaster AI.
All modules should import via: from app.core.logger import get_logger
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Log directory — auto-created if missing
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "guardian.log")

# Log format: timestamp | level | module | message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _setup_root_logger() -> None:
    """Configure the root logger exactly once at import time."""
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger("upt")
    if root.handlers:          # Prevent duplicate handlers on hot-reload
        return

    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── Console handler (INFO+) ──────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ── Rotating file handler (DEBUG+, max 5 MB × 3 backups) ────────────────
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)


_setup_root_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'upt' namespace.

    Usage:
        logger = get_logger(__name__)
        logger.info("Server started")
    """
    return logging.getLogger(f"upt.{name}")
