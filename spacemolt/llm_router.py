"""Hybrid LLM router — routes tasks between local and cloud LLMs.

Cloud (Abacus.AI / Anthropic / OpenAI via litellm):
  - Strategic decisions, complex planning, code generation
Local (Ollama via litellm):
  - Simple game-API calls, quick reactions, status checks

Supports flexible base_url configuration for all backends:
  - Ollama on remote hosts (IP/hostname)
  - Abacus.AI Router (https://routellm.abacus.ai/v1)
  - Any OpenAI-compatible endpoint

Routing is based on keyword heuristics + explicit overrides.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import litellm

from spacemolt.models import LLMBackend, TaskComplexity
from spacemolt.ui import log_info, log_llm, log_warning

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
    # Abacus.AI Router models
    "abacus/claude-sonnet-4-20250514": 200_000,
    "abacus/gpt-4o": 128_000,
    "abacus/gpt-4-turbo": 128_000,
    "abacus/gpt-3.5-turbo": 16_000,
}
DEFAULT_CONTEXT_WINDOW = 32_000

# Default Ollama URL (can be overridden)
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Abacus.AI Router URL
ABACUS_ROUTER_URL = "https://routellm.abacus.ai/v1"

# Keywords that indicate higher complexity
_HIGH_COMPLEXITY_PATTERNS = [
    r"\b(strateg|plan|analyz|compar|optimi|code|script|calculat|decid)\w*\b",
    r"\b(best route|market analysis|profit|which .* should)\b",
]
_LOW_COMPLEXITY_PATTERNS = [
    r"\b(get_status|get_cargo|get_ship|mine|travel|dock|undock|refuel|repair|buy|sell)\b",
    r"\b(check|look|scan|status)\b",
]


def _resolve_ollama_url(base_url: Optional[str]) -> str:
    """Resolve the Ollama API base URL from config or environment.

    Priority: explicit base_url > OLLAMA_HOST env var > default localhost.
    """
    if base_url:
        return base_url.rstrip("/")
    env_host = os.environ.get("OLLAMA_HOST", "")
    if env_host:
        # Ensure it has a scheme
        if not env_host.startswith("http"):
            env_host = f"http://{env_host}"
        return env_host.rstrip("/")
    return DEFAULT_OLLAMA_URL


@dataclass
class LLMRouter:
    """Intelligent task router between local and cloud LLMs.

    Supports flexible endpoint configuration:
      - ollama_base_url: URL for Ollama (local or remote, e.g. "http://192.168.1.100:11434")
      - cloud_base_url:  Custom base URL for cloud provider (e.g. Abacus.AI Router)
    """

    cloud_model: str = DEFAULT_CLOUD_MODEL
    local_model: str = DEFAULT_LOCAL_MODEL
    force_backend: Optional[LLMBackend] = None
    local_available: bool = False  # set after connectivity check

    # Flexible endpoint configuration
    ollama_base_url: Optional[str] = None   # e.g. "http://192.168.1.100:11434"
    cloud_base_url: Optional[str] = None    # e.g. "https://routellm.abacus.ai/v1"

    _cloud_model_re: list[re.Pattern] = field(default_factory=list, init=False)
    _local_model_re: list[re.Pattern] = field(default_factory=list, init=False)
    _resolved_ollama_url: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self._cloud_model_re = [re.compile(p, re.I) for p in _HIGH_COMPLEXITY_PATTERNS]
        self._local_model_re = [re.compile(p, re.I) for p in _LOW_COMPLEXITY_PATTERNS]
        self._resolved_ollama_url = _resolve_ollama_url(self.ollama_base_url)

    # ------------------------------------------------------------------
    # Connectivity check
    # ------------------------------------------------------------------

    async def check_local_availability(self) -> bool:
        """Ping the Ollama instance (local or remote)."""
        url = self._resolved_ollama_url
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.get(f"{url}/api/tags")
                self.local_available = resp.status_code == 200
        except Exception:
            self.local_available = False

        if self.local_available:
            if url != DEFAULT_OLLAMA_URL:
                log_info(f"Ollama available at {url}")
        else:
            log_warning(f"Ollama not available at {url} — all requests will use cloud model")
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

    def _build_litellm_kwargs(self, model: str) -> dict[str, Any]:
        """Build extra kwargs for litellm based on model and endpoint config."""
        extra: dict[str, Any] = {}

        # Ollama models: set api_base to configured Ollama URL
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            if self._resolved_ollama_url != DEFAULT_OLLAMA_URL:
                extra["api_base"] = self._resolved_ollama_url

        # Cloud models with custom base_url (e.g. Abacus.AI Router)
        elif self.cloud_base_url:
            extra["api_base"] = self.cloud_base_url
            # For Abacus.AI Router, use the API key from environment
            abacus_key = os.environ.get("ABACUS_API_KEY", "")
            if "abacus" in self.cloud_base_url.lower() and abacus_key:
                extra["api_key"] = abacus_key

        return extra

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

        # Add endpoint-specific kwargs
        kwargs.update(self._build_litellm_kwargs(model))

        try:
            response = await litellm.acompletion(**kwargs)
            return response.model_dump()
        except Exception as exc:
            # If local model fails, retry with cloud
            if "ollama" in model and model != self.cloud_model:
                log_warning(f"Local model failed ({exc}), retrying with cloud…")
                kwargs["model"] = self.cloud_model
                # Replace endpoint kwargs for cloud model
                for key in ("api_base", "api_key"):
                    kwargs.pop(key, None)
                kwargs.update(self._build_litellm_kwargs(self.cloud_model))
                response = await litellm.acompletion(**kwargs)
                return response.model_dump()
            raise
