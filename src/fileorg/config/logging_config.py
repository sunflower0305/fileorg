"""Logging configuration using loguru."""

import sys
import os
from pathlib import Path
from loguru import logger

LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging(log_dir: Path | None = None) -> None:
    """Configure loguru logger.

    Args:
        log_dir: Directory for log files. If None, only console output is used.
    """
    # Remove default handler
    logger.remove()

    # Add console handler with colors
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
    )

    # Add file handler if log_dir is provided
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "fileorg.log"
        logger.add(
            log_file,
            format=LOG_FORMAT,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="gz",
        )
        logger.info(f"Log file: {log_file}")
