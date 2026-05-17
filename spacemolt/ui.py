"""Rich-based terminal UI for SpaceMolt Commander."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Custom theme matching SpaceMolt categories
_THEME = Theme(
    {
        "info": "cyan",
        "mining": "green",
        "combat": "bold red",
        "trade": "yellow",
        "travel": "blue",
        "social": "magenta",
        "system": "dim white",
        "error": "bold red",
        "warning": "bold yellow",
        "success": "bold green",
        "llm": "bright_cyan",
        "tool": "bright_yellow",
        "compaction": "bright_magenta",
    }
)

console = Console(theme=_THEME)

# Regex to detect 64-char hex strings (passwords / tokens)
_SECRET_RE = re.compile(r"\b[0-9a-fA-F]{64}\b")


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _redact(text: str) -> str:
    """Replace 64-char hex tokens with a redacted placeholder."""
    return _SECRET_RE.sub("[REDACTED]", text)


def json_to_yaml(data: Any) -> str:
    """Convert a JSON-like object to compact YAML (token-saving)."""
    if data is None:
        return ""
    try:
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, width=120).rstrip()
    except Exception:
        return str(data)


# ---------------------------------------------------------------------------
# Public logging helpers
# ---------------------------------------------------------------------------

def log_info(msg: str) -> None:
    console.print(f"[system][{_timestamp()}][/system] {_redact(msg)}")


def log_tool_call(name: str, args: dict | None = None) -> None:
    args_str = json_to_yaml(args) if args else ""
    console.print(f"[tool][{_timestamp()}] 🔧 {name}[/tool]")
    if args_str:
        console.print(f"  [dim]{_redact(args_str)}[/dim]")


def log_tool_result(name: str, result: str) -> None:
    console.print(f"[tool][{_timestamp()}] ← {name}[/tool]: {_redact(result[:200])}")


def log_llm(provider: str, model: str, msg: str = "") -> None:
    console.print(f"[llm][{_timestamp()}] 🤖 {provider}/{model} {msg}[/llm]")


def log_error(msg: str) -> None:
    console.print(f"[error][{_timestamp()}] ❌ {msg}[/error]")


def log_warning(msg: str) -> None:
    console.print(f"[warning][{_timestamp()}] ⚠️  {msg}[/warning]")


def log_success(msg: str) -> None:
    console.print(f"[success][{_timestamp()}] ✅ {msg}[/success]")


def log_compaction(before: int, after: int) -> None:
    console.print(
        f"[compaction][{_timestamp()}] 📦 Context compacted: "
        f"{before} → {after} messages[/compaction]"
    )


def log_notification(notif: dict) -> None:
    """Pretty-print a game notification."""
    ntype = notif.get("type", "system")
    text = notif.get("message") or notif.get("text") or str(notif)
    style_map = {
        "chat": "social",
        "combat": "combat",
        "trade": "trade",
        "system": "system",
        "dm": "social",
        "broadcast": "warning",
    }
    style = style_map.get(ntype, "info")
    console.print(f"[{style}][{_timestamp()}] 📢 [{ntype}] {_redact(str(text))}[/{style}]")


def show_banner() -> None:
    banner = Text()
    banner.append("🚀 SpaceMolt Commander ", style="bold bright_cyan")
    banner.append("v0.5.0-py", style="dim")
    console.print(Panel(banner, border_style="bright_cyan", padding=(0, 2)))


def show_session_info(session_name: str, model: str) -> None:
    console.print(f"[info]Session:[/info] {session_name}  [info]Model:[/info] {model}")
