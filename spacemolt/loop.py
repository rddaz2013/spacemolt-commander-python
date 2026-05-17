"""Inner tool-calling loop — drives the LLM ↔ tool interaction cycle.

Each "turn" of the agent runs this loop for up to MAX_TOOL_ROUNDS rounds.
On each round the LLM either makes tool calls or produces a final text
response (which ends the turn).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from spacemolt.api import SpaceMoltAPI
from spacemolt.code_executor import CodeExecutor
from spacemolt.compaction import compact_context, needs_compaction
from spacemolt.llm_router import LLMRouter
from spacemolt.models import CompactionState, TOOL_DEFINITIONS
from spacemolt.session import SessionStore
from spacemolt.tools import execute_tool
from spacemolt.ui import log_error, log_info, log_warning

# Constants
MAX_TOOL_ROUNDS = 30
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5.0  # seconds
LLM_TIMEOUT = 120.0


async def run_inner_loop(
    messages: list[dict[str, Any]],
    *,
    router: LLMRouter,
    api: SpaceMoltAPI,
    session_store: SessionStore,
    code_executor: CodeExecutor,
    compaction_state: CompactionState,
    force_credentials: bool = False,
    abort_event: Optional[asyncio.Event] = None,
) -> tuple[list[dict[str, Any]], CompactionState]:
    """Run the inner tool-calling loop.

    Parameters
    ----------
    messages
        Conversation so far (including system prompt as messages[0]).
    router
        The hybrid LLM router.
    api
        SpaceMolt API client.
    session_store
        On-disk session store.
    code_executor
        Sandboxed code executor.
    compaction_state
        Accumulated compaction state.
    force_credentials
        Allow credential overwrite.
    abort_event
        Set by the outer loop on Ctrl+C to abort the current turn.

    Returns
    -------
    (updated_messages, updated_compaction_state)
    """

    context_window = router.get_context_window()

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        if abort_event and abort_event.is_set():
            log_warning("Turn aborted by user")
            break

        # --- Context compaction ---
        # We compact everything except messages[0] (system prompt)
        non_system = messages[1:]
        if needs_compaction(non_system, context_window):
            async def _summary_llm(messages, **kw):
                return await router.complete(messages, **kw)

            non_system, compaction_state = await compact_context(
                non_system, context_window, _summary_llm, compaction_state,
            )
            messages = [messages[0]] + non_system

        # --- LLM call with retry ---
        response = await _complete_with_retry(
            messages, router, abort_event=abort_event,
        )
        if response is None:
            log_error("LLM call failed after retries — ending turn")
            break

        choice = response.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason", "")
        assistant_msg = choice.get("message", {})

        # Append the assistant message
        messages.append(assistant_msg)

        # --- Handle tool calls ---
        tool_calls = assistant_msg.get("tool_calls")
        if not tool_calls:
            # No tool calls → turn ends with a text response
            text = assistant_msg.get("content", "")
            if text:
                log_info(f"[Agent says] {text[:300]}")
            break

        # Execute each tool call and append results
        for tc in tool_calls:
            if abort_event and abort_event.is_set():
                break

            func = tc.get("function", {})
            tool_name = func.get("name", "")
            raw_args = func.get("arguments", "{}")

            try:
                tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                tool_args = {}

            result_str = await execute_tool(
                tool_name,
                tool_args,
                api=api,
                session_store=session_store,
                code_executor=code_executor,
                force_credentials=force_credentials,
            )

            # Append tool result message
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result_str,
            })

        if round_num == MAX_TOOL_ROUNDS:
            log_warning(f"Reached max tool rounds ({MAX_TOOL_ROUNDS})")

    return messages, compaction_state


# ---------------------------------------------------------------------------
# LLM call with exponential-backoff retry
# ---------------------------------------------------------------------------

async def _complete_with_retry(
    messages: list[dict[str, Any]],
    router: LLMRouter,
    *,
    abort_event: Optional[asyncio.Event] = None,
) -> Optional[dict[str, Any]]:
    """Call the LLM with up to MAX_RETRIES attempts."""
    for attempt in range(1, MAX_RETRIES + 1):
        if abort_event and abort_event.is_set():
            return None
        try:
            return await router.complete(
                messages,
                tools=TOOL_DEFINITIONS,
                timeout=LLM_TIMEOUT,
            )
        except Exception as exc:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            log_warning(f"LLM attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                log_info(f"Retrying in {delay:.0f}s…")
                await asyncio.sleep(delay)
    return None
