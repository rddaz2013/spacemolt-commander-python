#!/usr/bin/env python3
"""
SpaceMolt Commander - Main Entry Point

Usage:
    python -m spacemolt_commander            # Run the commander
    python -m spacemolt_commander --setup    # Run interactive setup
"""

import argparse
import os
import sys

import yaml

from spacemolt_commander.setup_config import (
    DEFAULT_SESSION_DIR,
    DEFAULT_CONFIG_PATH,
    setup_config,
)
from spacemolt_commander.logger import setup_logging
from spacemolt_commander.api_client import SpacemoltAPIClient
from spacemolt_commander.llm_client import LLMClient


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load the session configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Configuration dictionary.
    """
    if not os.path.exists(config_path):
        print(f"[ERROR] Config not found at {config_path}")
        print("Run setup first:  python -m spacemolt_commander --setup")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    """Main entry point for SpaceMolt Commander."""
    parser = argparse.ArgumentParser(description="SpaceMolt Commander")
    parser.add_argument(
        "--setup", action="store_true", help="Run interactive configuration setup"
    )
    parser.add_argument(
        "--session", default="default", help="Session name (default: 'default')"
    )
    args = parser.parse_args()

    if args.setup:
        setup_config(session_name=args.session)
        return

    # Load configuration
    config = load_config()

    # Setup logging (detailed, with timestamps and function names)
    log_cfg = config.get("logging", {})
    session_dir = DEFAULT_SESSION_DIR
    log_file = os.path.join(session_dir, log_cfg.get("log_filename", "session.log"))

    logger = setup_logging(
        log_level=log_cfg.get("level", "DEBUG"),
        log_file=log_file,
        log_format=log_cfg.get(
            "format",
            "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s",
        ),
        date_format=log_cfg.get("date_format", "%Y-%m-%d %H:%M:%S"),
        enabled=log_cfg.get("enabled", True),
    )

    logger.info("SpaceMolt Commander starting")
    logger.info("Session directory: %s", session_dir)

    # Initialize clients
    llm_cfg = config.get("llm", {})
    game_cfg = config.get("game_api", {})
    player_cfg = config.get("player", {})

    api_client = SpacemoltAPIClient(
        base_url=game_cfg.get("base_url", "https://game.spacemolt.com/api/v2/"),
        timeout=game_cfg.get("timeout", 30),
        max_retries=game_cfg.get("max_retries", 3),
    )

    llm_client = LLMClient(
        api_key=llm_cfg.get("api_key", ""),
        api_base_url=llm_cfg.get("api_base_url", "https://apis.abacus.ai/api/routellm"),
        model=llm_cfg.get("model", "routellm"),
        max_tokens=llm_cfg.get("max_tokens", 1024),
        temperature=llm_cfg.get("temperature", 0.7),
    )

    player_name = player_cfg.get("name", "Unknown")
    logger.info("Player: %s", player_name)
    logger.info("Game API: %s", api_client.base_url)

    print(f"SpaceMolt Commander ready — Player: {player_name}")
    print(f"Game API: {api_client.base_url}")
    print("Type 'help' for available commands, 'quit' to exit.")

    # Simple command loop
    while True:
        try:
            user_input = input("\n[SpaceMolt]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting SpaceMolt Commander.")
            logger.info("Commander exited by user")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Exiting SpaceMolt Commander.")
            logger.info("Commander exited by user")
            break

        if user_input.lower() == "help":
            print("Available commands:")
            print("  status   - Get your player status")
            print("  state    - Get current game state")
            print("  ask <q>  - Ask the LLM a question")
            print("  quit     - Exit the commander")
            continue

        if user_input.lower() == "status":
            try:
                result = api_client.get_player_status(player_name)
                print(f"Player Status: {result}")
            except Exception as exc:
                logger.error("Failed to get player status: %s", exc)
                print(f"Error: {exc}")
            continue

        if user_input.lower() == "state":
            try:
                result = api_client.get_game_state()
                print(f"Game State: {result}")
            except Exception as exc:
                logger.error("Failed to get game state: %s", exc)
                print(f"Error: {exc}")
            continue

        if user_input.lower().startswith("ask "):
            question = user_input[4:].strip()
            if question:
                try:
                    answer = llm_client.ask(question)
                    print(f"LLM: {answer}")
                except Exception as exc:
                    logger.error("LLM request failed: %s", exc)
                    print(f"Error: {exc}")
            else:
                print("Usage: ask <your question>")
            continue

        # Default: try to send as game command
        try:
            result = api_client.send_command(player_name, user_input)
            print(f"Result: {result}")
        except Exception as exc:
            logger.error("Command failed: %s", exc)
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
