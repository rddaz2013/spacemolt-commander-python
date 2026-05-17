"""Centralised file + console logger for SpaceMolt Commander.

The Rich-based helpers in :mod:`spacemolt.ui` are kept for the colourful
terminal UI.  This module is responsible for **persistent** logging:

* every line carries a precise timestamp and the name of the calling
  function (``%(funcName)s``), as required by the project spec;
* logs are written to ``~/.spacemolt/sessions/<session>/session.log`` by
  default;
* an optional console handler (stderr) can also be enabled.

Other modules obtain a logger via :func:`get_logger` and may rely on
:func:`setup_logging` having been called once at process start by
:mod:`spacemolt.cli` or :mod:`spacemolt.commander`.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults — mirror the layout used by setup_config.py
# ---------------------------------------------------------------------------

SPACEMOLT_HOME = Path(os.environ.get("SPACEMOLT_HOME", str(Path.home() / ".spacemolt")))
SESSIONS_DIR = SPACEMOLT_HOME / "sessions"
DEFAULT_SESSION_DIR = SESSIONS_DIR / "default"
DEFAULT_LOG_FILENAME = "session.log"

DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-7s | %(name)s.%(funcName)s:%(lineno)d | %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Logger name used as the root for the whole project.  Sub-modules retrieve
# their logger with ``get_logger(__name__)``; because every module name
# starts with ``spacemolt.``, all loggers inherit from this one.
ROOT_LOGGER_NAME = "spacemolt"

_INITIALISED = False


def _resolve_log_path(
    session_name: Optional[str] = None,
    log_file: Optional[str] = None,
) -> Path:
    """Resolve the absolute path of the log file for a session."""
    if log_file:
        path = Path(log_file).expanduser()
        if path.is_absolute():
            return path
        # Relative path is resolved inside the session directory.
        session = session_name or "default"
        return SESSIONS_DIR / session / path

    session = session_name or "default"
    return SESSIONS_DIR / session / DEFAULT_LOG_FILENAME


def setup_logging(
    *,
    session_name: str = "default",
    level: str | int = "INFO",
    log_file: Optional[str] = None,
    fmt: str = DEFAULT_LOG_FORMAT,
    datefmt: str = DEFAULT_DATE_FORMAT,
    console: bool = True,
    enabled: bool = True,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Configure the project-wide logger.

    Idempotent — calling it twice will not double the handlers.

    Parameters
    ----------
    session_name:
        Name of the active session; used to derive the log file location
        (``~/.spacemolt/sessions/<session_name>/session.log``).
    level:
        Logging level name (``"DEBUG"``/``"INFO"``/…) or numeric level.
    log_file:
        Override the log file path.  Absolute paths are honoured as-is;
        relative paths are placed inside the session directory.
    fmt, datefmt:
        Format strings forwarded to :class:`logging.Formatter`.  The
        default format includes timestamp, level, ``module.function:line``
        and message.
    console:
        If True, also write log records to stderr.
    enabled:
        If False, only a NullHandler is attached — effectively disabling
        file logging while still allowing :func:`get_logger` to work.
    max_bytes, backup_count:
        Rotation parameters for the file handler.

    Returns
    -------
    logging.Logger
        The configured project root logger.
    """
    global _INITIALISED

    root = logging.getLogger(ROOT_LOGGER_NAME)

    # Reset existing handlers so repeated calls (e.g. test suites,
    # interactive reload) don't accumulate duplicates.
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level
    root.setLevel(numeric_level)
    root.propagate = False

    if not enabled:
        root.addHandler(logging.NullHandler())
        _INITIALISED = True
        return root

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    # ---- File handler ------------------------------------------------
    log_path = _resolve_log_path(session_name=session_name, log_file=log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception as exc:  # pragma: no cover — never block startup
        sys.stderr.write(
            f"[spacemolt.logger] Failed to open log file {log_path}: {exc}\n"
        )

    # ---- Console handler --------------------------------------------
    if console:
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    _INITIALISED = True
    root.debug(
        "Logging initialised — session=%s level=%s file=%s",
        session_name, logging.getLevelName(numeric_level), log_path,
    )
    return root


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger that inherits from the project root logger.

    If :func:`setup_logging` has not yet been called, a sensible default
    configuration is applied so that early log lines are still captured.
    """
    if not _INITIALISED:
        # Best-effort: configure with defaults to the "default" session.
        # Callers can override later by calling setup_logging() again.
        setup_logging()

    if not name:
        return logging.getLogger(ROOT_LOGGER_NAME)

    # Always nest under ``spacemolt.<name>`` so handlers attached to
    # the root logger pick up everything.
    if name == ROOT_LOGGER_NAME or name.startswith(ROOT_LOGGER_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


__all__ = [
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_DATE_FORMAT",
    "DEFAULT_SESSION_DIR",
    "SESSIONS_DIR",
    "SPACEMOLT_HOME",
    "get_logger",
    "setup_logging",
]
