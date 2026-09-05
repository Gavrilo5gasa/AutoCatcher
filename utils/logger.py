"""
utils/logger.py — Internal app logging (NOT evidence logging).
This is for AutoCatcher's own debug/info output, not case records.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import APP_NAME


def get_logger(name: str) -> logging.Logger:
    """Get a named logger prefixed with the app name."""
    logger = logging.getLogger(f"{APP_NAME}.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
