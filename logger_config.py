from __future__ import annotations

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configure structured rotating logging for Friday."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("friday")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"friday_{timestamp}.log"

    # Rotating file handler (10MB per file, up to 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Formatters
    detailed_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s():%(lineno)d - %(message)s"
    )
    simple_format = logging.Formatter("[%(levelname)s] %(message)s")

    file_handler.setFormatter(detailed_format)
    console_handler.setFormatter(simple_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
