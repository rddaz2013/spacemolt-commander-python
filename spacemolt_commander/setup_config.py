#!/usr/bin/env python3
"""
SpaceMolt Commander - Interactive Setup Configuration

Creates the default session directory at ~/.spacemolt/sessions/default/
and writes the configuration file with API keys and player name.
"""

import os
import sys
import yaml


# Default paths
SPACEMOLT_BASE_DIR = os.path.expanduser("~/.spacemolt")
SESSIONS_DIR = os.path.join(SPACEMOLT_BASE_DIR, "sessions")
DEFAULT_SESSION_DIR = os.path.join(SESSIONS_DIR, "default")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_SESSION_DIR, "config.yaml")
DEFAULT_LOG_PATH = os.path.join(DEFAULT_SESSION_DIR, "session.log")

# Default API endpoints
GAME_API_BASE_URL = "https://game.spacemolt.com/api/v2/"
LLM_API_BASE_URL = "https://apis.abacus.ai/api/routellm"


def get_default_config(api_key: str, player_name: str) -> dict:
    """Return the default configuration dictionary.

    Args:
        api_key: The Abacus RouteLLM API key.
        player_name: The player's in-game name.

    Returns:
        A dictionary containing the full default configuration.
    """
    return {
        "llm": {
            "api_key": api_key,
            "api_base_url": LLM_API_BASE_URL,
            "model": "routellm",
            "max_tokens": 1024,
            "temperature": 0.7,
        },
        "game_api": {
            "base_url": GAME_API_BASE_URL,
            "timeout": 30,
            "max_retries": 3,
        },
        "player": {
            "name": player_name,
        },
        "session": {
            "default_session": "default",
        },
        "logging": {
            "enabled": True,
            "level": "DEBUG",
            "log_filename": "session.log",
            "format": "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
        },
    }


def create_session_directory(session_dir: str) -> None:
    """Create the session directory if it does not exist.

    Args:
        session_dir: Path to the session directory.
    """
    os.makedirs(session_dir, exist_ok=True)
    print(f"[OK] Session directory ready: {session_dir}")


def write_config(config: dict, config_path: str) -> None:
    """Write the configuration dictionary to a YAML file.

    Args:
        config: The configuration dictionary.
        config_path: Path to write the YAML config file.
    """
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"[OK] Configuration written to: {config_path}")


def prompt_input(prompt_text: str, default: str = "") -> str:
    """Prompt the user for input with an optional default value.

    Args:
        prompt_text: The prompt message.
        default: Default value if user presses Enter.

    Returns:
        The user's input or the default value.
    """
    if default:
        user_input = input(f"{prompt_text} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        user_input = input(f"{prompt_text}: ").strip()
        return user_input


def setup_config(session_name: str = "default") -> None:
    """Run the interactive setup to create a session configuration.

    This creates the directory ~/.spacemolt/sessions/<session_name>/
    and writes config.yaml with the user-supplied API key and player name.

    Args:
        session_name: Name of the session to configure. Defaults to "default".
    """
    print("=" * 60)
    print("  SpaceMolt Commander - Configuration Setup")
    print("=" * 60)
    print()

    session_dir = os.path.join(SESSIONS_DIR, session_name)

    # Check if config already exists
    config_path = os.path.join(session_dir, "config.yaml")
    if os.path.exists(config_path):
        overwrite = input(
            f"Configuration already exists at {config_path}.\n"
            "Overwrite? (y/N): "
        ).strip().lower()
        if overwrite != "y":
            print("Setup cancelled.")
            return

    # Prompt for API key
    print("\n--- Abacus RouteLLM API Key ---")
    print("Get your API key from: https://apps.abacus.ai/")
    api_key = prompt_input("Enter your Abacus RouteLLM API key")
    if not api_key:
        print("[ERROR] API key is required. Aborting setup.")
        sys.exit(1)

    # Prompt for player name
    print("\n--- Player Configuration ---")
    player_name = prompt_input("Enter your in-game player name")
    if not player_name:
        print("[ERROR] Player name is required. Aborting setup.")
        sys.exit(1)

    # Build configuration
    config = get_default_config(api_key=api_key, player_name=player_name)

    # Create directory and write config
    create_session_directory(session_dir)
    write_config(config, config_path)

    # Summary
    print()
    print("=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    print(f"  Session directory : {session_dir}")
    print(f"  Config file       : {config_path}")
    print(f"  Log file          : {os.path.join(session_dir, 'session.log')}")
    print(f"  Game API          : {GAME_API_BASE_URL}")
    print(f"  Player name       : {player_name}")
    print("=" * 60)


def main():
    """Entry point for setup_config when run as a module."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SpaceMolt Commander - Configuration Setup"
    )
    parser.add_argument(
        "--session",
        default="default",
        help="Session name to configure (default: 'default')",
    )
    args = parser.parse_args()
    setup_config(session_name=args.session)


if __name__ == "__main__":
    main()
