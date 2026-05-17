"""Per-session credential and TODO persistence.

Layout:
    sessions/<name>/credentials.json
    sessions/<name>/TODO.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from spacemolt.models import Credentials
from spacemolt.ui import log_info, log_warning

DEFAULT_SESSIONS_DIR = Path("sessions")


class SessionStore:
    """Manages on-disk state for a named session."""

    def __init__(self, name: str, base_dir: Path = DEFAULT_SESSIONS_DIR) -> None:
        self.name = name
        self._dir = base_dir / name
        self._dir.mkdir(parents=True, exist_ok=True)

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
