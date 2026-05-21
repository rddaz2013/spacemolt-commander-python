#!/usr/bin/env python3
"""
SpaceMolt Commander - Game API Client

Handles communication with the Spacemolt Game API v2.
Endpoint: https://game.spacemolt.com/api/v2/
"""

import requests

from spacemolt_commander.logger import get_logger
from spacemolt_commander.setup_config import GAME_API_BASE_URL

logger = get_logger(__name__)

# Game API base URL — all requests go to v2
API_BASE_URL = GAME_API_BASE_URL  # https://game.spacemolt.com/api/v2/


class SpacemoltAPIClient:
    """Client for the Spacemolt Game API v2.

    All endpoints use https://game.spacemolt.com/api/v2/ as the base URL.
    """

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = 30, max_retries: int = 3):
        """Initialize the API client.

        Args:
            base_url: Base URL for the Spacemolt Game API (default: https://game.spacemolt.com/api/v2/).
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries on failure.
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        logger.info("SpacemoltAPIClient initialized — base_url: %s", self.base_url)

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an HTTP request to the Game API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (appended to base_url).
            **kwargs: Additional arguments passed to requests.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            requests.exceptions.RequestException: On request failure after retries.
        """
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("API request [%d/%d]: %s %s", attempt, self.max_retries, method, url)
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as exc:
                last_exception = exc
                logger.warning("Request failed (attempt %d/%d): %s", attempt, self.max_retries, exc)

        logger.error("All %d attempts failed for %s %s", self.max_retries, method, url)
        raise last_exception

    def get(self, endpoint: str, params: dict = None) -> dict:
        """Send a GET request.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            Parsed JSON response.
        """
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict = None, json_data: dict = None) -> dict:
        """Send a POST request.

        Args:
            endpoint: API endpoint.
            data: Form data.
            json_data: JSON body.

        Returns:
            Parsed JSON response.
        """
        return self._request("POST", endpoint, data=data, json=json_data)

    def get_player_status(self, player_name: str) -> dict:
        """Get the status of a player.

        Args:
            player_name: The player's in-game name.

        Returns:
            Player status data.
        """
        logger.info("Fetching status for player: %s", player_name)
        return self.get("player/status", params={"name": player_name})

    def get_game_state(self) -> dict:
        """Get the current game state.

        Returns:
            Current game state data.
        """
        logger.info("Fetching current game state")
        return self.get("game/state")

    def send_command(self, player_name: str, command: str, params: dict = None) -> dict:
        """Send a game command.

        Args:
            player_name: The player's in-game name.
            command: The command to execute.
            params: Additional command parameters.

        Returns:
            Command response data.
        """
        payload = {"player": player_name, "command": command}
        if params:
            payload["params"] = params
        logger.info("Sending command '%s' for player '%s'", command, player_name)
        return self.post("command/execute", json_data=payload)
