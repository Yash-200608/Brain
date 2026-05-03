"""Centralised logging setup."""
from __future__ import annotations

import logging
import logging.handlers
import os

from config import settings


def configure_logging() -> None:
    os.makedirs(settings.log_dir, exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    file_h = logging.handlers.RotatingFileHandler(
        os.path.join(settings.log_dir, "jarvis.log"),
        maxBytes=2_000_000,
        backupCount=5,
    )
    file_h.setFormatter(logging.Formatter(fmt))
    handlers.append(file_h)

    logging.basicConfig(level=settings.log_level, format=fmt, handlers=handlers, force=True)
