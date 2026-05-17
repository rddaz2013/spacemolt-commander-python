"""Outer loop — orchestrates the full agent lifecycle.

Responsibilities:
  1. Build the system prompt (role + mission + game guide + credentials + commands + TODO)
  2. Run the outer loop: inner-loop turn → sleep → poll status → nudge → refresh
  3. Graceful shutdown with session handoff
"""

from __future__ import annotations

import asyncio
import signal
from pathlib import Path
from typing import Any, Optional

from spacemolt.api import SpaceMoltAPI
from spacemolt.code_executor import CodeExecutor
from spacemolt.compaction import CompactionState
from spacemolt.llm_router import LLMRouter
from spacemolt.loop import run_inner_loop
from spacemolt.models import Credentials
from spacemolt.game_sequences import get_sequence_list_for_prompt
from spacemolt.schema import fetch_commands, format_command_list
from spacemolt.session import SessionStore
from spacemolt.wiki import WikiStore
from spacemolt.ui import (
    log_error,
    log_info,
    log_notification,
    log_success,
    log_warning,
    show_banner,
    show_session_info,
)

OUTER_LOOP_DELAY = 2.0  # seconds between turns
PROMPT_FILE = Path(__file__).parent / "prompt.md"


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(
    mission: str,
    game_guide: str,
    command_list: str,
    credentials: Optional[Credentials] = None,
    todo: str = "",
    game_status: str = "",
) -> str:
    """Construct the system prompt analogous to commander.ts."""
    sections: list[str] = []

    # Role
    sections.append(
        "You are an autonomous AI agent playing SpaceMolt, "
        "a text-based MMO for AI agents. You make decisions and execute "
        "game commands to accomplish the player's mission."
    )

    # Mission
    sections.append(f"## Mission\n{mission}")

    # Game guide
    if game_guide:
        sections.append(f"## Game Knowledge\n{game_guide}")

    # Credentials
    if credentials and credentials.username:
        sections.append(
            f"## Credentials\n"
            f"Username: {credentials.username}\n"
            f"Empire: {credentials.empire or 'unknown'}\n"
            f"PlayerID: {credentials.player_id or 'unknown'}\n"
            f"(Password stored — do NOT reveal it in chat)"
        )
    else:
        sections.append(
            "## Credentials\n"
            "No credentials yet. Register a new account or log in first.\n"
            "Use save_credentials after successful registration/login."
        )

    # Current game status
    if game_status:
        sections.append(f"## Current Game State\n{game_status}")

    # Available commands
    sections.append(f"## Available Commands\n{command_list}")

    # TODO list
    if todo:
        sections.append(f"## Your TODO List\n{todo}")

    # Predefined sequences
    sections.append(f"## Predefined Sequences\n{get_sequence_list_for_prompt()}")

    # Wiki info
    sections.append(
        "## Wiki Knowledge Base\n"
        "You have a persistent Wiki that automatically learns from every game interaction.\n"
        "- **ALWAYS check the Wiki first** before making API calls (use `query_wiki`).\n"
        "- The Wiki stores: systems, stations, items, recipes, market prices, mining history, intel.\n"
        "- Use `catalog_sync` sequence early to populate the Wiki with game catalog data.\n"
        "- Use `query_wiki` with questions like:\n"
        '  - "systems with asteroid_belt"\n'
        '  - "where did I mine Iron Ore"\n'
        '  - "best prices for Fuel"\n'
        '  - "crafting recipes"\n'
        '  - "stats" (wiki overview)\n'
    )

    # Rules / tips
    sections.append(
        "## Rules\n"
        "- Act autonomously. Do not ask the player for input — decide yourself.\n"
        "- **Check the Wiki first** before querying game data you might already know.\n"
        "- Use 'execute_sequence' for common multi-step workflows (mining, trading, flying, crafting).\n"
        "- Use the 'game' tool for individual commands not covered by sequences.\n"
        "- Use 'execute_code' for data-heavy analysis (market comparisons, route planning).\n"
        "- Use 'update_todo' to track your goals and progress.\n"
        "- Use 'query_wiki' to check what you already know before making API calls.\n"
        "- Use 'get_recipes', 'craft_item', 'check_materials' for crafting workflows.\n"
        "- Use 'query_intel', 'query_trade_intel' for faction intelligence (free queries).\n"
        "- Use 'query_catalog' to browse items, recipes, modules, ships, facilities.\n"
        "- Query commands are free. Action commands cost 1 tick (10 s).\n"
        "- Keep your context lean — avoid requesting the same data repeatedly.\n"
        "- PREFER sequences over individual game calls to save tokens and time.\n"
        "- Run 'catalog_sync' once after login to populate the Wiki with game data.\n"
        "- If you're stuck, try 'spacemolt/get_guide' or 'spacemolt/get_commands'.\n"
        "- Always save credentials after registering or logging in."
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Commander (outer loop)
# ---------------------------------------------------------------------------

class Commander:
    """Top-level orchestrator for the SpaceMolt agent."""

    def __init__(
        self,
        *,
        mission: str,
        session_name: str = "default",
        router: LLMRouter,
        api: SpaceMoltAPI,
        force_credentials: bool = False,
        debug: bool = False,
    ) -> None:
        self.mission = mission
        self.router = router
        self.api = api
        self.debug = debug
        self.force_credentials = force_credentials

        self.session_store = SessionStore(session_name)
        self.code_executor = CodeExecutor(api_client=api)
        self.compaction_state = CompactionState()
        self.messages: list[dict[str, Any]] = []
        self._running = False
        self._abort_event = asyncio.Event()
        self._game_guide = ""
        self._command_list = ""

        # Initialize Wiki knowledge base
        wiki_path = self.session_store._dir / "wiki.json"
        self.wiki = WikiStore(wiki_path)
        # Attach wiki to API for auto-learning
        self.api.set_wiki(self.wiki)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialise and enter the outer loop."""
        show_banner()
        show_session_info(self.session_store.name, self.router.cloud_model)

        # Check local LLM availability
        await self.router.check_local_availability()

        # Load game guide
        if PROMPT_FILE.exists():
            self._game_guide = PROMPT_FILE.read_text(encoding="utf-8")

        # Fetch command list from OpenAPI
        try:
            commands = await fetch_commands(self.api.base_url)
            self._command_list = format_command_list(commands)
        except Exception as exc:
            log_warning(f"Command discovery failed: {exc}")
            self._command_list = "(use 'spacemolt/get_commands' to list available commands)"

        # Create API session
        await self.api.create_session()

        # Load credentials and auto-login
        creds = self.session_store.load_credentials()
        if creds and creds.username and creds.password:
            self.api.set_credentials(creds.username, creds.password)
            log_info("Logging in with stored credentials…")
            login_result = await self.api.execute(
                "spacemolt_auth/login",
                {"username": creds.username, "password": creds.password},
            )
            log_info(f"Login: {login_result[:200]}")

        # Build initial system prompt
        self._refresh_system_prompt(creds)

        # Add mission as first user message
        self.messages.append({"role": "user", "content": self.mission})

        # Register signal handlers
        self._running = True
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._handle_shutdown)
            except NotImplementedError:
                pass  # Windows

        log_success("Commander started — entering outer loop")
        await self._outer_loop()

    async def _outer_loop(self) -> None:
        """Outer loop: run turn → sleep → poll → nudge → refresh."""
        while self._running:
            try:
                # 1) Run agent turn (inner loop)
                self._abort_event.clear()
                self.messages, self.compaction_state = await run_inner_loop(
                    self.messages,
                    router=self.router,
                    api=self.api,
                    session_store=self.session_store,
                    code_executor=self.code_executor,
                    compaction_state=self.compaction_state,
                    force_credentials=self.force_credentials,
                    abort_event=self._abort_event,
                    wiki=self.wiki,
                )

                if not self._running:
                    break

                # 2) Sleep between turns
                await asyncio.sleep(OUTER_LOOP_DELAY)

                # 3) Poll status / notifications
                try:
                    status = await self.api.execute("spacemolt/get_status")
                    if status and status.strip():
                        # Inject status as context
                        pass  # notifications are handled inside api.execute
                except Exception:
                    pass  # non-critical

                # 4) Push "continue" nudge
                self.messages.append({
                    "role": "user",
                    "content": "Continue your mission. Check your TODO and proceed.",
                })

                # 5) Refresh system prompt
                creds = self.session_store.load_credentials()
                self._refresh_system_prompt(creds)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                log_error(f"Outer loop error: {exc}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(5)

        # Shutdown
        await self._shutdown()

    # ------------------------------------------------------------------
    # System prompt management
    # ------------------------------------------------------------------

    def _refresh_system_prompt(self, creds: Optional[Credentials] = None) -> None:
        """Rebuild and update the system prompt (messages[0])."""
        todo = self.session_store.read_todo()
        prompt = build_system_prompt(
            mission=self.mission,
            game_guide=self._game_guide,
            command_list=self._command_list,
            credentials=creds,
            todo=todo,
        )
        sys_msg = {"role": "system", "content": prompt}
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = sys_msg
        else:
            self.messages.insert(0, sys_msg)

    # ------------------------------------------------------------------
    # Shutdown & handoff
    # ------------------------------------------------------------------

    def _handle_shutdown(self) -> None:
        if not self._running:
            # Second Ctrl+C → force exit
            log_warning("Force exit!")
            import sys
            sys.exit(1)
        log_info("Shutting down gracefully (Ctrl+C again to force)…")
        self._running = False
        self._abort_event.set()

    async def _shutdown(self) -> None:
        """Generate session handoff and clean up."""
        log_info("Generating session handoff…")
        try:
            await self._generate_handoff()
        except Exception as exc:
            log_error(f"Handoff generation failed: {exc}")

        await self.api.close()
        log_success("Commander stopped.")

    async def _generate_handoff(self) -> None:
        """Summarise the last N messages into a handoff note."""
        recent = self.messages[-30:]
        if len(recent) < 2:
            return

        from spacemolt.compaction import _format_transcript
        transcript = _format_transcript(recent)

        handoff_prompt = [
            {
                "role": "system",
                "content": (
                    "Summarize this agent session in 3-8 bullet points. "
                    "Include: current location, goals, progress, next steps, "
                    "any warnings or blockers."
                ),
            },
            {"role": "user", "content": transcript},
        ]

        try:
            resp = await self.router.complete(
                handoff_prompt, max_tokens=512, timeout=30.0,
            )
            summary = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            summary = transcript[:1000]

        if summary:
            self.session_store.save_handoff(summary)
            # Also try to save to captain's log on the server
            try:
                await self.api.execute(
                    "spacemolt_social/captains_log_add",
                    {"content": f"[Handoff] {summary}"},
                )
            except Exception:
                pass

        # Update TODO with handoff
        self.session_store.write_todo(summary)
