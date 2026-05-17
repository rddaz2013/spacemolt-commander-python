"""Context compaction — keeps the conversation within budget.

When the message list exceeds 55 % of the model's context window, older
messages are summarised by the LLM and replaced with a single summary
message.  This allows the agent to run for hours without hitting limits.
"""

from __future__ import annotations

from typing import Any, Optional

from spacemolt.models import CompactionState
from spacemolt.ui import log_compaction, log_info

# Constants (matching the TypeScript reference)
CHARS_PER_TOKEN = 4
CONTEXT_BUDGET_RATIO = 0.55  # use at most 55 % of the window for messages
MIN_RECENT_MESSAGES = 10
SUMMARY_MAX_TOKENS = 1024
OLD_RATIO = 0.40  # fraction of budgeted messages that count as "old"


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token count: total chars / 4."""
    total_chars = 0
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total_chars += len(str(part.get("text", "")))
        # tool_calls / function results
        if "tool_calls" in m:
            total_chars += len(str(m["tool_calls"]))
    return total_chars // CHARS_PER_TOKEN


def needs_compaction(messages: list[dict[str, Any]], context_window: int) -> bool:
    """Return True if messages exceed the budget ratio."""
    budget_tokens = int(context_window * CONTEXT_BUDGET_RATIO)
    current_tokens = estimate_tokens(messages)
    return current_tokens > budget_tokens


def _find_turn_boundary(messages: list[dict[str, Any]], target_idx: int) -> int:
    """Snap *target_idx* forward to the nearest user-message start (turn boundary)."""
    for i in range(target_idx, len(messages)):
        if messages[i].get("role") == "user":
            return i
    return target_idx


def _format_transcript(messages: list[dict[str, Any]]) -> str:
    """Format a slice of messages as a flat text transcript."""
    lines: list[str] = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, list):
            # multipart — flatten text parts
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if not content and "tool_calls" in m:
            calls = m["tool_calls"]
            content = ", ".join(
                f"{c.get('function', {}).get('name', '?')}(…)" for c in calls
            )
        lines.append(f"[{role}] {content[:500]}")
    return "\n".join(lines)


async def compact_context(
    messages: list[dict[str, Any]],
    context_window: int,
    llm_complete,  # async callable(messages, **kw) -> dict
    state: CompactionState,
) -> tuple[list[dict[str, Any]], CompactionState]:
    """Compact *messages* if they exceed the budget.

    Parameters
    ----------
    messages : list
        The full message list (excluding the system prompt).
    context_window : int
        Token limit of the current model.
    llm_complete : callable
        ``async (messages, max_tokens, timeout) -> response_dict``
    state : CompactionState
        Carried between turns to accumulate summaries.

    Returns
    -------
    (compacted_messages, updated_state)
    """
    if not needs_compaction(messages, context_window):
        return messages, state

    budget_tokens = int(context_window * CONTEXT_BUDGET_RATIO)
    old_budget = int(budget_tokens * OLD_RATIO)

    # Walk backwards from the end to find the split point
    recent_tokens = 0
    split_idx = len(messages)
    for i in range(len(messages) - 1, -1, -1):
        msg_tokens = estimate_tokens([messages[i]])
        if recent_tokens + msg_tokens > (budget_tokens - old_budget):
            split_idx = i + 1
            break
        recent_tokens += msg_tokens

    # Ensure we keep at least MIN_RECENT_MESSAGES
    split_idx = min(split_idx, max(0, len(messages) - MIN_RECENT_MESSAGES))

    if split_idx <= 0:
        return messages, state  # nothing old enough to compact

    # Snap to turn boundary
    split_idx = _find_turn_boundary(messages, split_idx)

    old_messages = messages[:split_idx]
    recent_messages = messages[split_idx:]

    # Build the summary request
    transcript = _format_transcript(old_messages)
    summary_prompt = [
        {
            "role": "system",
            "content": (
                "Summarize this game session transcript. "
                "Include: current location, resources, active missions, key events, "
                "and what the agent was working on. Be concise (3-8 bullet points)."
            ),
        },
        {"role": "user", "content": transcript},
    ]

    try:
        log_info("Compacting context…")
        resp = await llm_complete(
            messages=summary_prompt,
            max_tokens=SUMMARY_MAX_TOKENS,
            timeout=30.0,
        )
        choices = resp.get("choices", [])
        summary_text = ""
        if choices:
            summary_text = choices[0].get("message", {}).get("content", "")

        if not summary_text:
            summary_text = _format_transcript(old_messages[-5:])  # fallback

    except Exception as exc:
        log_info(f"Compaction summary failed ({exc}), using raw truncation")
        summary_text = _format_transcript(old_messages[-5:])

    # Build the compacted message list
    summary_msg: dict[str, Any] = {
        "role": "user",
        "content": f"[Session summary so far]\n{summary_text}",
    }

    compacted = [summary_msg] + recent_messages
    log_compaction(len(messages), len(compacted))

    # Update state
    from datetime import datetime
    state.summary = summary_text
    state.compacted_at = datetime.utcnow()
    state.messages_compacted += len(old_messages)

    return compacted, state
