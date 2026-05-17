"""Hybrid LLM router — routes tasks between local and cloud LLMs.

Cloud (Abacus.AI / Anthropic / OpenAI via litellm):
  - Strategic decisions, complex planning, code generation
Local (Ollama via litellm):
  - Simple game-API calls, quick reactions, status checks

Routing is based on keyword heuristics + explicit overrides.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import litellm

from spacemolt.models import LLMBackend, TaskComplexity
from spacemolt.ui import log_llm, log_warning

# Suppress litellm's noisy logging
litellm.suppress_debug_info = True

# Default model IDs
DEFAULT_CLOUD_MODEL = "anthropic/claude-sonnet-4-20250514"
DEFAULT_LOCAL_MODEL = "ollama/qwen3:8b"

# Context window sizes (conservative estimates)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "anthropic/claude-sonnet-4-20250514": 200_000,
    "anthropic/claude-3-haiku-20240307": 200_000,
    "openai/gpt-4o": 128_000,
    "openai/gpt-4o-mini": 128_000,
    "ollama/qwen3:8b": 32_000,
    "ollama/llama3.1:8b": 128_000,
    "ollama/mistral:7b": 32_000,
}
DEFAULT_CONTEXT_WINDOW = 32_000

# Keywords that indicate higher complexity
_HIGH_COMPLEXITY_PATTERNS = [
    r"\b(strateg|plan|analyz|compar|optimi|code|script|calculat|decid)\w*\b",
    r"\b(best route|market analysis|profit|which .* should)\b",
]
_LOW_COMPLEXITY_PATTERNS = [
    r"\b(get_status|get_cargo|get_ship|mine|travel|dock|undock|refuel|repair|buy|sell)\b",
    r"\b(check|look|scan|status)\b",
]


@dataclass
class LLMRouter:
    """Intelligent task router between local and cloud LLMs."""

    cloud_model: str = DEFAULT_CLOUD_MODEL
    local_model: str = DEFAULT_LOCAL_MODEL
    force_backend: Optional[LLMBackend] = None
    local_available: bool = False  # set after connectivity check
    _cloud_model_re: list[re.Pattern] = field(default_factory=list, init=False)
    _local_model_re: list[re.Pattern] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._cloud_model_re = [re.compile(p, re.I) for p in _HIGH_COMPLEXITY_PATTERNS]
        self._local_model_re = [re.compile(p, re.I) for p in _LOW_COMPLEXITY_PATTERNS]

    # ------------------------------------------------------------------
    # Connectivity check
    # ------------------------------------------------------------------

    async def check_local_availability(self) -> bool:
        """Ping the local Ollama instance."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.get("http://localhost:11434/api/tags")
                self.local_available = resp.status_code == 200
        except Exception:
            self.local_available = False

        if not self.local_available:
            log_warning("Local Ollama not available — all requests will use cloud model")
        return self.local_available

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------

    def classify_complexity(self, text: str) -> TaskComplexity:
        """Heuristic complexity classifier."""
        for pat in self._cloud_model_re:
            if pat.search(text):
                return TaskComplexity.HIGH
        for pat in self._local_model_re:
            if pat.search(text):
                return TaskComplexity.LOW
        return TaskComplexity.MEDIUM

    def select_model(self, text: str = "") -> str:
        """Pick the best model for the given text / task."""
        if self.force_backend == LLMBackend.CLOUD:
            return self.cloud_model
        if self.force_backend == LLMBackend.LOCAL:
            if self.local_available:
                return self.local_model
            log_warning("Forced local but unavailable — falling back to cloud")
            return self.cloud_model

        complexity = self.classify_complexity(text)
        if complexity == TaskComplexity.LOW and self.local_available:
            return self.local_model
        return self.cloud_model

    def get_context_window(self, model: Optional[str] = None) -> int:
        model = model or self.cloud_model
        return MODEL_CONTEXT_WINDOWS.get(model, DEFAULT_CONTEXT_WINDOW)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict]] = None,
        *,
        model_override: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Call the LLM via litellm and return the response dict."""
        # Decide model
        if model_override:
            model = model_override
        else:
            # Use last user/assistant message for routing
            last_text = ""
            for m in reversed(messages):
                if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
                    last_text = m["content"]
                    break
            model = self.select_model(last_text)

        provider = model.split("/")[0] if "/" in model else "unknown"
        log_llm(provider, model, "calling…")

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await litellm.acompletion(**kwargs)
            return response.model_dump()
        except Exception as exc:
            # If local model fails, retry with cloud
            if "ollama" in model and model != self.cloud_model:
                log_warning(f"Local model failed ({exc}), retrying with cloud…")
                kwargs["model"] = self.cloud_model
                response = await litellm.acompletion(**kwargs)
                return response.model_dump()
            raise
