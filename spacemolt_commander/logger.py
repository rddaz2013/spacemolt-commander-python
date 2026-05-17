#!/usr/bin/env python3
"""
SpaceMolt Commander - Logging Configuration

Sets up detailed logging for the default session.
Log format includes timestamps and function names.
Log file is written to the session directory:
    ~/.spacemolt/sessions/default/session.log
"""

import logging
import os

from spacemolt_commander.setup_config import DEFAULT_SESSION_DIR


DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FILE = os.path.join(DEFAULT_SESSION_DIR, "session.log")


def setup_logging(
    log_level: str = "DEBUG",
    log_file: str = DEFAULT_LOG_FILE,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    enabled: bool = True,
) -> logging.Logger:
    """Configure and return the application logger.

    Detailed logging is enabled by default for the default session.
    The log format includes timestamps (asctime) and function names (funcName).
    The log file is written to ~/.spacemolt/sessions/default/session.log.

    Args:
        log_level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to the log file.
        log_format: Format string for log messages.
        date_format: Date format for timestamps.
        enabled: Whether logging is enabled.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger("spacemolt_commander")

    if not enabled:
        logger.addHandler(logging.NullHandler())
        return logger

    logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # File handler - writes to session directory
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.debug("Logging initialized — file: %s", log_file)
    return logger


def get_logger(name: str = "spacemolt_commander") -> logging.Logger:
    """Get an existing logger by name.

    Args:
        name: Logger name (dot-separated hierarchy supported).

    Returns:
        The requested Logger instance.
    """
    return logging.getLogger(name)
