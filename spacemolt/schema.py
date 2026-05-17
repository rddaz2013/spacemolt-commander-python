"""OpenAPI-based command discovery for SpaceMolt.

Fetches the v2 OpenAPI spec and extracts a compact command list
for the system prompt (pipe-delimited, token-efficient).
"""

from __future__ import annotations

from typing import Optional

import httpx

from spacemolt.models import GameCommandInfo
from spacemolt.ui import log_info, log_warning

OPENAPI_URL = "https://game.spacemolt.com/api/v2/openapi.json"


async def fetch_commands(base_url: str = "") -> list[GameCommandInfo]:
    """Fetch the OpenAPI spec and extract game commands."""
    url = f"{base_url.rstrip('/')}/openapi.json" if base_url else OPENAPI_URL
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            spec = resp.json()
    except Exception as exc:
        log_warning(f"Failed to fetch OpenAPI spec: {exc}")
        return []

    commands: list[GameCommandInfo] = []
    paths: dict = spec.get("paths", {})
    v2_prefix = "/api/v2/"

    for path, methods in paths.items():
        # Normalise to a relative command name
        name = path
        if name.startswith(v2_prefix):
            name = name[len(v2_prefix):]
        name = name.strip("/")

        for _method, details in methods.items():
            if _method.lower() not in ("post", "get"):
                continue
            summary = details.get("summary", "")
            is_mutation = details.get("x-is-mutation", False)
            commands.append(GameCommandInfo(
                name=name,
                description=summary,
                is_mutation=bool(is_mutation),
            ))

    log_info(f"Discovered {len(commands)} commands from OpenAPI spec")
    return commands


def format_command_list(commands: list[GameCommandInfo]) -> str:
    """Format commands as compact pipe-delimited text for the system prompt."""
    if not commands:
        return "(No commands discovered — use game tool with 'spacemolt/get_commands' to list available commands)"

    queries = [c for c in commands if not c.is_mutation]
    actions = [c for c in commands if c.is_mutation]

    lines: list[str] = []

    if queries:
        names = "|".join(c.name for c in queries)
        lines.append(f"Query commands (free, no tick cost): {names}")

    if actions:
        names = "|".join(c.name for c in actions)
        lines.append(f"Action commands (costs 1 tick): {names}")

    return "\n".join(lines)
