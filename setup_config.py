#!/usr/bin/env python3
"""Interactive setup for SpaceMolt Commander.

Creates the default session directory at::

    ~/.spacemolt/sessions/default/

and writes a fully-populated ``config.yaml`` containing:

* LLM configuration for the **Abacus RouteLLM API** (cloud backend)
* Spacemolt Game API endpoint (always v2)
* Player / commander display name
* Logging configuration (file + console, detailed format)
* Default session metadata

The script intentionally collects the **minimum** set of inputs required
by the project spec:

* Abacus RouteLLM API key
* Player name

All other values fall back to sensible defaults documented in
``config.example.yaml``.

Usage
-----

::

    python setup_config.py            # interactive
    python setup_config.py --non-interactive --player-name "Alice" \
        --abacus-api-key "abc123"     # scripted

Re-running the script asks before overwriting an existing config.yaml.
"""

from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path
from typing import Any, Optional

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: PyYAML is not installed. Run: pip install -r requirements.txt\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants — single source of truth for default paths and URLs
# ---------------------------------------------------------------------------

SPACEMOLT_HOME: Path = Path(
    os.environ.get("SPACEMOLT_HOME", str(Path.home() / ".spacemolt"))
)
SESSIONS_DIR: Path = SPACEMOLT_HOME / "sessions"
DEFAULT_SESSION_NAME: str = "default"
DEFAULT_SESSION_DIR: Path = SESSIONS_DIR / DEFAULT_SESSION_NAME
DEFAULT_CONFIG_PATH: Path = DEFAULT_SESSION_DIR / "config.yaml"
DEFAULT_LOG_PATH: Path = DEFAULT_SESSION_DIR / "session.log"
DEFAULT_PLAYER_NAME_PATH: Path = DEFAULT_SESSION_DIR / "player.txt"
DEFAULT_CREDENTIALS_PATH: Path = DEFAULT_SESSION_DIR / "credentials.json"

# Game API — always v2 (v1 is deprecated and no longer used in this code base)
GAME_API_BASE_URL: str = "https://game.spacemolt.com/api/v2/"

# Abacus RouteLLM defaults
LLM_API_BASE_URL: str = "https://routellm.abacus.ai/v1"
LLM_DEFAULT_MODEL: str = "abacus/claude-sonnet-4-20250514"
LLM_DEFAULT_LOCAL_MODEL: str = "ollama/qwen3:8b"
LLM_DEFAULT_OLLAMA_URL: str = "http://localhost:11434"

# Logging defaults — timestamps + function names are mandatory
LOG_FORMAT: str = (
    "%(asctime)s | %(levelname)-7s | %(name)s.%(funcName)s:%(lineno)d | %(message)s"
)
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Tiny ANSI helpers (no third-party deps)
# ---------------------------------------------------------------------------

class _C:
    HEADER = "\033[95m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _header(text: str) -> None:
    print(f"\n{_C.HEADER}{_C.BOLD}{'=' * 70}\n{text:^70}\n{'=' * 70}{_C.RESET}\n")


def _section(text: str) -> None:
    print(f"\n{_C.CYAN}{_C.BOLD}▶ {text}{_C.RESET}\n{_C.CYAN}{'-' * (len(text) + 2)}{_C.RESET}")


def _ok(text: str) -> None:
    print(f"{_C.GREEN}✓ {text}{_C.RESET}")


def _warn(text: str) -> None:
    print(f"{_C.YELLOW}⚠ {text}{_C.RESET}")


def _err(text: str) -> None:
    print(f"{_C.RED}✗ {text}{_C.RESET}")


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def prompt_input(
    question: str,
    default: Optional[str] = None,
    required: bool = True,
    secret: bool = False,
) -> str:
    """Prompt the user for a value with an optional default."""
    suffix = f" [{default}]" if default else ""
    label = f"{_C.BOLD}{question}{suffix}: {_C.RESET}"

    while True:
        try:
            value = (getpass(label) if secret else input(label)).strip()
        except EOFError:
            value = ""

        if not value and default is not None:
            return default
        if not value and not required:
            return ""
        if not value and required:
            _err("This field is required. Please enter a value.")
            continue
        return value


def prompt_yes_no(question: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    while True:
        ans = input(f"{_C.BOLD}{question} [{default_str}]: {_C.RESET}").strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        _err("Please answer y or n.")


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def create_session_directory(session_dir: Path = DEFAULT_SESSION_DIR) -> Path:
    """Create the session directory tree, returning the absolute path."""
    session_dir.mkdir(parents=True, exist_ok=True)
    # Tighten permissions on the parent so secrets aren't world-readable.
    try:
        os.chmod(SPACEMOLT_HOME, 0o700)
        os.chmod(SESSIONS_DIR, 0o700)
        os.chmod(session_dir, 0o700)
    except OSError:
        pass
    return session_dir


def get_default_config(
    *,
    abacus_api_key: str,
    player_name: str,
    session_name: str = DEFAULT_SESSION_NAME,
) -> dict[str, Any]:
    """Return the canonical config.yaml dictionary."""
    return {
        # --- LLM ---------------------------------------------------------
        "llm": {
            "api_key": abacus_api_key,
            "api_base_url": LLM_API_BASE_URL,
            "model": LLM_DEFAULT_MODEL,
            "max_tokens": 4096,
            "temperature": 0.3,
            "local_model": LLM_DEFAULT_LOCAL_MODEL,
            "ollama_base_url": LLM_DEFAULT_OLLAMA_URL,
            "backend": "auto",
        },

        # --- Game API ----------------------------------------------------
        "game_api": {
            "base_url": GAME_API_BASE_URL,
            "timeout": 30,
            "max_retries": 6,
        },

        # --- Player ------------------------------------------------------
        "player": {
            "name": player_name,
        },

        # --- Session -----------------------------------------------------
        "session": {
            "default_session": session_name,
        },

        # --- Mission -----------------------------------------------------
        "mission": (
            "Explore the galaxy, mine ore, trade for profit, and grow stronger."
        ),

        # --- Logging -----------------------------------------------------
        "logging": {
            "enabled": True,
            "level": "INFO",
            "log_filename": "session.log",
            "format": LOG_FORMAT,
            "date_format": LOG_DATE_FORMAT,
            "console": True,
        },

        # --- Behaviour ---------------------------------------------------
        "debug": False,
        "force_credentials": False,

        # --- Legacy flat keys (kept for backward compatibility with the
        #     existing Click-based CLI which reads top-level keys) -------
        "cloud_model": LLM_DEFAULT_MODEL,
        "local_model": LLM_DEFAULT_LOCAL_MODEL,
        "api_url": GAME_API_BASE_URL,
        "session_name": session_name,
        "backend": "auto",
        "cloud_base_url": LLM_API_BASE_URL,
        "ollama_base_url": LLM_DEFAULT_OLLAMA_URL,
    }


def write_config(config: dict[str, Any], path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Serialise ``config`` to YAML and write it to ``path`` (mode 0600)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# SpaceMolt Commander — generated by setup_config.py\n"
        "#\n"
        f"# Session directory: {path.parent}\n"
        f"# Log file:          {path.parent / 'session.log'}\n"
        "#\n"
        "# Keep this file private — it contains your Abacus RouteLLM API key.\n"
        "#\n"
        "# To regenerate: rm config.yaml && python setup_config.py\n"
        "\n"
    )
    body = yaml.safe_dump(
        config,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
    )
    path.write_text(header + body, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def write_player_name(player_name: str, path: Path = DEFAULT_PLAYER_NAME_PATH) -> None:
    """Persist the player name in a simple text file alongside config.yaml."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(player_name.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def setup_config(
    *,
    abacus_api_key: Optional[str] = None,
    player_name: Optional[str] = None,
    session_name: str = DEFAULT_SESSION_NAME,
    non_interactive: bool = False,
    overwrite: bool = False,
) -> Path:
    """Interactive entry point — returns the absolute path of the written config."""
    _header("SpaceMolt Commander — Setup")

    session_dir = SESSIONS_DIR / session_name
    config_path = session_dir / "config.yaml"

    print(f"Default session directory : {_C.BOLD}{session_dir}{_C.RESET}")
    print(f"Default config file        : {_C.BOLD}{config_path}{_C.RESET}")
    print(f"Default log file           : {_C.BOLD}{session_dir / 'session.log'}{_C.RESET}")
    print(f"Game API endpoint          : {_C.BOLD}{GAME_API_BASE_URL}{_C.RESET}")
    print(f"LLM endpoint               : {_C.BOLD}{LLM_API_BASE_URL}{_C.RESET}")
    print()

    # --- Overwrite guard -------------------------------------------------
    if config_path.exists() and not overwrite:
        if non_interactive:
            _err(f"{config_path} already exists. Re-run with --overwrite to replace it.")
            sys.exit(2)
        if not prompt_yes_no(f"{config_path} already exists. Overwrite?", default=False):
            _warn("Setup cancelled — existing config left in place.")
            return config_path

    # --- Collect inputs --------------------------------------------------
    _section("Abacus RouteLLM API key")
    print(
        "Get your key from https://abacus.ai/app/account.  It will be saved\n"
        "to the per-session config.yaml with file mode 0600."
    )
    if not abacus_api_key:
        if non_interactive:
            _err("Missing --abacus-api-key in non-interactive mode.")
            sys.exit(2)
        # Try environment first so the user can pre-export and just press Enter
        env_key = os.environ.get("ABACUS_API_KEY", "").strip()
        if env_key:
            print(f"Using ABACUS_API_KEY from environment "
                  f"({_C.GREEN}{'*' * 4}{env_key[-4:]}{_C.RESET}).")
            abacus_api_key = env_key
        else:
            abacus_api_key = prompt_input(
                "Abacus RouteLLM API key", required=True, secret=True
            )

    _section("Player name")
    print("Your in-game commander / player display name (used for logs and prompts).")
    if not player_name:
        if non_interactive:
            _err("Missing --player-name in non-interactive mode.")
            sys.exit(2)
        player_name = prompt_input("Player name", default="Commander", required=False)

    # --- Build and write -------------------------------------------------
    _section("Writing configuration")
    create_session_directory(session_dir)
    config = get_default_config(
        abacus_api_key=abacus_api_key,
        player_name=player_name,
        session_name=session_name,
    )
    write_config(config, config_path)
    write_player_name(player_name, session_dir / "player.txt")

    _ok(f"Wrote {config_path}")
    _ok(f"Wrote {session_dir / 'player.txt'}")
    _ok(f"Log file will be written to {session_dir / 'session.log'}")

    # --- Next steps ------------------------------------------------------
    _section("Next steps")
    print("1. Install dependencies (if not already):")
    print(f"   {_C.BOLD}pip install -r requirements.txt{_C.RESET}")
    print()
    print("2. Run the commander:")
    print(f"   {_C.BOLD}python -m spacemolt run \"Mine ore and get rich\"{_C.RESET}")
    print()
    print("3. Tail the log:")
    print(f"   {_C.BOLD}tail -f {session_dir / 'session.log'}{_C.RESET}")
    print()
    _ok("Setup complete. 🚀")

    return config_path


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set up the SpaceMolt Commander default session.",
    )
    parser.add_argument(
        "--session-name",
        default=DEFAULT_SESSION_NAME,
        help=f"Session name (default: {DEFAULT_SESSION_NAME})",
    )
    parser.add_argument(
        "--player-name",
        default=None,
        help="Player / commander display name.",
    )
    parser.add_argument(
        "--abacus-api-key",
        default=None,
        help="Abacus RouteLLM API key (will be saved to config.yaml).",
    )
    parser.add_argument(
        "--non-interactive", "-y",
        action="store_true",
        help="Fail rather than prompt when a value is missing.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing config.yaml without prompting.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)
    try:
        setup_config(
            abacus_api_key=args.abacus_api_key,
            player_name=args.player_name,
            session_name=args.session_name,
            non_interactive=args.non_interactive,
            overwrite=args.overwrite,
        )
    except KeyboardInterrupt:
        print()
        _warn("Setup cancelled by user.")
        sys.exit(1)
    except Exception as exc:  # pragma: no cover
        _err(f"Setup failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
