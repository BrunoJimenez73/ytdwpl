from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    """Configure rotating application logs without duplicating handlers."""
    log_dir = Path.home() / ".ytdwpl"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ytdwpl")
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logger.addHandler(handler)
