#!/usr/bin/env python3

"""
Logging configuration for Grok Assistant

Provides structured logging with file rotation and configurable levels.
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_level: str = None) -> logging.Logger:
    """
    Setup structured logging for Grok Assistant.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR).
                   Defaults to env var GROK_LOG_LEVEL or INFO.

    Returns:
        Configured logger instance
    """
    if log_level is None:
        log_level = os.getenv("GROK_LOG_LEVEL", "INFO")

    logger = logging.getLogger("grok")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers if setup_logging called multiple times
    if logger.handlers:
        return logger

    # File handler (rotating logs)
    log_dir = Path.home() / ".grok" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "grok.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler (only warnings/errors - user messages go through UI)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # Formatter with detailed context
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (e.g., 'memory', 'context', 'session')

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"grok.{name}")
