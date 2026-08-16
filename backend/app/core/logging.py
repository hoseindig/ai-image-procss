"""Centralized application logging using the standard library.

Format is machine-parseable key=value style in the message body while keeping a
stable prefix: timestamp | level | component | message.

Never log embeddings, raw images, secrets, or credential material.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: str) -> None:
    """Configure root logging once with a consistent, timestamped format."""
    global _CONFIGURED

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Prefer `app.*` names (e.g. `app.db`)."""
    return logging.getLogger(name)
