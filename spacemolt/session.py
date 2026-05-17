"""Per-session credential and TODO persistence.

Default layout (per the project spec):

    ~/.spacemolt/sessions/<name>/
        config.yaml         # written by setup_config.py
        credentials.json    # SpaceMolt login credentials
        TODO.md             # agent's running TODO list
        handoff.md          # last session handoff summary
        wiki.json           # WikiStore knowledge base
        session.log         # rotating log file written by spacemolt.logger

For backward compatibility the legacy ``./sessions/<name>/`` location
(relative to the current working directory) is still honoured when it
already exists.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from spacemolt.logger import SESSIONS_DIR as DEFAULT_SESSIONS_DIR
from spacemolt.logger import get_logger
from spacemolt.models import Credentials
from spacemolt.ui import log_info, log_warning

_LEGACY_SESSIONS_DIR = Path("sessions")  # ./sessions/<name>/ in CWD
_log = get_logger(__name__)


def _resolve_session_dir(name: str, base_dir: Optional[Path]) -> Path:
    """Pick the session directory, falling back to a legacy location."""
    if base_dir is not None:
        return base_dir / name

    # 1) Explicit env override
    env_base = os.environ.get("SPACEMOLT_SESSIONS_DIR", "").strip()
    if env_base:
        return Path(env_base).expanduser() / name

    # 2) If a legacy ./sessions/<name>/ already exists, keep using it so
    #    existing users don't lose their state on upgrade.
    legacy = _LEGACY_SESSIONS_DIR / name
    if legacy.exists():
        return legacy

    # 3) Default: ~/.spacemolt/sessions/<name>/
    return DEFAULT_SESSIONS_DIR / name


class SessionStore:
    """Manages on-disk state for a named session."""

    def __init__(self, name: str, base_dir: Optional[Path] = None) -> None:
        self.name = name
        self._dir = _resolve_session_dir(name, base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        _log.debug("SessionStore initialised — name=%s dir=%s", name, self._dir)

    # ------------------------------------------------------------------
    # Path accessors (so the rest of the code never hard-codes filenames)
    # ------------------------------------------------------------------

    @property
    def directory(self) -> Path:
        """Absolute path of the session directory."""
        return self._dir

    @property
    def log_path(self) -> Path:
        """Path of the rotating ``session.log`` file."""
        return self._dir / "session.log"

    @property
    def config_path(self) -> Path:
        """Path of the per-session ``config.yaml``."""
        return self._dir / "config.yaml"

    @property
    def player_name_path(self) -> Path:
        """Path of the simple ``player.txt`` file."""
        return self._dir / "player.txt"

    # ------------------------------------------------------------------
    # Player display name (separate from login credentials)
    # ------------------------------------------------------------------

    def load_player_name(self) -> str:
        """Return the saved player / commander display name (may be empty)."""
        try:
            if self.player_name_path.exists():
                return self.player_name_path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            _log.warning("Failed to read player name: %s", exc)
        return ""

    def save_player_name(self, player_name: str) -> None:
        """Persist the player / commander display name to disk."""
        try:
            self.player_name_path.write_text(
                (player_name or "").strip() + "\n", encoding="utf-8"
            )
            _log.info("Player name saved for session '%s'", self.name)
        except Exception as exc:
            _log.error("Failed to save player name: %s", exc)

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    @property
    def _creds_path(self) -> Path:
        return self._dir / "credentials.json"

    def load_credentials(self) -> Optional[Credentials]:
        if not self._creds_path.exists():
            return None
        try:
            data = json.loads(self._creds_path.read_text(encoding="utf-8"))
            return Credentials.model_validate(data)
        except Exception as exc:
            log_warning(f"Failed to load credentials: {exc}")
            return None

    def save_credentials(self, creds: Credentials, *, force: bool = False) -> bool:
        """Save credentials.  Refuses to overwrite unless *force* is True."""
        if self._creds_path.exists() and not force:
            log_warning("Credentials already saved — use --force-credentials to overwrite")
            return False
        self._creds_path.write_text(
            creds.model_dump_json(indent=2), encoding="utf-8"
        )
        log_info(f"Credentials saved for session '{self.name}'")
        return True

    # ------------------------------------------------------------------
    # TODO list
    # ------------------------------------------------------------------

    @property
    def _todo_path(self) -> Path:
        return self._dir / "TODO.md"

    def read_todo(self) -> str:
        if not self._todo_path.exists():
            return ""
        return self._todo_path.read_text(encoding="utf-8")

    def write_todo(self, content: str) -> None:
        self._todo_path.write_text(content, encoding="utf-8")
        log_info("TODO list updated")

    # ------------------------------------------------------------------
    # Handoff log (Captain's Log snapshot)
    # ------------------------------------------------------------------

    @property
    def _handoff_path(self) -> Path:
        return self._dir / "handoff.md"

    def save_handoff(self, summary: str) -> None:
        self._handoff_path.write_text(summary, encoding="utf-8")
        log_info("Session handoff saved")

    def load_handoff(self) -> str:
        if not self._handoff_path.exists():
            return ""
        return self._handoff_path.read_text(encoding="utf-8")
