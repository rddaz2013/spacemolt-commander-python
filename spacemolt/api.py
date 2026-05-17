"""Async HTTP client for the SpaceMolt v2 REST API.

Handles session lifecycle, rate-limiting, auto-retry, and reconnection.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from spacemolt import __version__
from spacemolt.models import ApiResponse, ApiSession
from spacemolt.ui import json_to_yaml, log_error, log_info, log_warning

DEFAULT_BASE_URL = "https://game.spacemolt.com/api/v2"
USER_AGENT = f"SpaceMolt-Commander-Py/{__version__}"
RESULT_TRUNCATION = 4_000  # max chars per tool result

# Reconnect constants
MAX_RECONNECT_ATTEMPTS = 6
RECONNECT_BASE_DELAY = 5.0  # seconds
MAX_RECONNECT_DELAY = 160.0

# Session renewal threshold
SESSION_RENEWAL_THRESHOLD_S = 60


class SpaceMoltAPI:
    """Async REST client for SpaceMolt v2 with session management."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, debug: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self._session: Optional[ApiSession] = None
        self._credentials: dict[str, str] = {}
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            follow_redirects=True,
        )

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def create_session(self) -> ApiSession:
        """POST /session → new session handle."""
        resp = await self._raw_post("/session", {})
        data = resp.json()
        self._session = ApiSession.model_validate(data.get("session", data))
        log_info(f"Session created: {self._session.id[:12]}…")
        return self._session

    async def ensure_session(self) -> None:
        """Create or renew the session if needed."""
        if self._session is None:
            await self.create_session()
            return

        expires = datetime.fromisoformat(self._session.expires_at.replace("Z", "+00:00"))
        remaining = (expires - datetime.now(timezone.utc)).total_seconds()
        if remaining < SESSION_RENEWAL_THRESHOLD_S:
            log_info("Session expiring soon — renewing…")
            await self.create_session()

    def set_credentials(self, username: str, password: str) -> None:
        self._credentials = {"username": username, "password": password}

    @property
    def session_id(self) -> Optional[str]:
        return self._session.id if self._session else None

    @property
    def player_id(self) -> Optional[str]:
        return self._session.player_id if self._session else None

    # ------------------------------------------------------------------
    # Command execution (the core interface used by tools.py)
    # ------------------------------------------------------------------

    async def execute(self, command: str, args: Optional[dict[str, Any]] = None) -> str:
        """Execute a game command and return the YAML-formatted result string.

        This is the single entry point used by the ``game`` tool.
        Returns a YAML string (compact, token-efficient).
        """
        await self.ensure_session()

        # Build the path from the command name
        path = f"/{command.lstrip('/')}"
        body = args or {}

        response = await self._post_with_retry(path, body)

        # Handle notifications side-effect
        if response.notifications:
            from spacemolt.ui import log_notification
            for n in response.notifications:
                if isinstance(n, dict):
                    log_notification(n)

        # Update session if server sent a new one
        if response.session:
            self._session = response.session

        # Return the human-readable result (preferred) or structured content
        result_data = response.result or response.structured_content or ""
        result_str = json_to_yaml(result_data) if not isinstance(result_data, str) else result_data

        # Truncate
        if len(result_str) > RESULT_TRUNCATION:
            result_str = result_str[:RESULT_TRUNCATION] + "\n… [truncated]"

        return result_str

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self._session:
            h["X-Session-Id"] = self._session.id
        return h

    async def _raw_post(self, path: str, body: dict) -> httpx.Response:
        url = f"{self.base_url}{path}"
        if self.debug:
            log_info(f"POST {url}")
        resp = await self._client.post(url, json=body, headers=self._headers())
        resp.raise_for_status()
        return resp

    async def _post_with_retry(self, path: str, body: dict) -> ApiResponse:
        """POST with rate-limit, session-expiry, and reconnect handling."""
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            try:
                await self.ensure_session()
                url = f"{self.base_url}{path}"
                if self.debug:
                    log_info(f"POST {url} (attempt {attempt + 1})")

                resp = await self._client.post(url, json=body, headers=self._headers())

                # HTTP-level session invalidation
                if resp.status_code == 401:
                    log_warning("HTTP 401 — session invalid, recreating…")
                    self._session = None
                    await self.create_session()
                    await self._re_login()
                    continue

                data = resp.json()
                api_resp = ApiResponse.model_validate(data)

                if api_resp.error:
                    err = api_resp.error
                    if err.code == "rate_limited":
                        wait = err.wait_seconds or 5.0
                        log_warning(f"Rate limited — sleeping {wait:.1f}s")
                        await asyncio.sleep(wait)
                        continue
                    if err.code in ("session_invalid", "session_expired", "not_authenticated"):
                        log_warning(f"{err.code} — recreating session…")
                        self._session = None
                        await self.create_session()
                        await self._re_login()
                        continue
                    # Non-recoverable API error
                    return api_resp

                return api_resp

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                delay = min(RECONNECT_BASE_DELAY * (2 ** attempt), MAX_RECONNECT_DELAY)
                log_error(f"Network error: {exc} — retrying in {delay:.0f}s")
                await asyncio.sleep(delay)

        # Exhausted retries
        log_error("All reconnect attempts failed.")
        return ApiResponse(error={"code": "network_failure", "message": "All retries exhausted"})  # type: ignore[arg-type]

    async def _re_login(self) -> None:
        """Re-authenticate if credentials are available."""
        if self._credentials:
            log_info("Re-logging in with stored credentials…")
            await self.execute("spacemolt_auth/login", self._credentials)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()
