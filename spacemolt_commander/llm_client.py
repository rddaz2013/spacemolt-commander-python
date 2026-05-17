#!/usr/bin/env python3
"""
SpaceMolt Commander - LLM Client

Handles communication with the Abacus RouteLLM API for hybrid
LLM architecture and token optimization.
"""

import requests

from spacemolt_commander.logger import get_logger
from spacemolt_commander.setup_config import LLM_API_BASE_URL

logger = get_logger(__name__)


class LLMClient:
    """Client for the Abacus RouteLLM API.

    Sends prompts to the RouteLLM endpoint and returns responses
    with token-optimized payloads.
    """

    def __init__(
        self,
        api_key: str,
        api_base_url: str = LLM_API_BASE_URL,
        model: str = "routellm",
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """Initialize the LLM client.

        Args:
            api_key: Abacus RouteLLM API key.
            api_base_url: Base URL for the RouteLLM API.
            model: Model identifier.
            max_tokens: Maximum tokens per request.
            temperature: Sampling temperature (0.0–1.0).
        """
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        logger.info("LLMClient initialized — model: %s", self.model)

    def chat(self, messages: list, max_tokens: int = None, temperature: float = None) -> dict:
        """Send a chat completion request to the RouteLLM API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Override default max tokens for this request.
            temperature: Override default temperature for this request.

        Returns:
            The API response as a dictionary.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        url = f"{self.api_base_url}/chat/completions"
        logger.debug("LLM chat request to %s with %d messages", url, len(messages))

        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.debug("LLM response received — tokens used: %s", result.get("usage", {}))
            return result
        except requests.exceptions.RequestException as exc:
            logger.error("LLM request failed: %s", exc)
            raise

    def ask(self, prompt: str) -> str:
        """Simple single-turn prompt helper.

        Args:
            prompt: The user prompt string.

        Returns:
            The assistant's response text.
        """
        messages = [{"role": "user", "content": prompt}]
        result = self.chat(messages)
        return result["choices"][0]["message"]["content"]
