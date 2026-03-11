"""
Multi-provider LLM client.
Primary:  xAI Grok (OpenAI-compatible API via XAI_API_KEY)
Fallback: Anthropic Claude Haiku (via ANTHROPIC_API_KEY)
"""

from __future__ import annotations
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# xAI Grok model to use
GROK_MODEL = os.getenv("GROK_MODEL", "grok-3-fast")
GROK_BASE_URL = "https://api.x.ai/v1"

# Anthropic fallback model
ANTHROPIC_FALLBACK_MODEL = os.getenv(
    "ANTHROPIC_FALLBACK_MODEL", "claude-haiku-4-5-20251001"
)


class LLMClient:
    """
    Unified LLM client with Grok primary and Claude Haiku fallback.
    All calls are synchronous and return a plain string response.
    """

    def __init__(self) -> None:
        self._xai_key = os.getenv("XAI_API_KEY", "")
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not self._xai_key and not self._anthropic_key:
            raise EnvironmentError(
                "No API keys found. Set XAI_API_KEY or ANTHROPIC_API_KEY in your .env file."
            )

    # ── Public Interface ──────────────────────────────────────────────────────

    def call(self, system_prompt: str, user_message: str, max_tokens: int = 4096) -> str:
        """
        Call the LLM with a system prompt and user message.
        Tries Grok first; falls back to Anthropic Claude Haiku on any error.
        """
        if self._xai_key:
            try:
                return self._call_grok(system_prompt, user_message, max_tokens)
            except Exception as e:
                logger.warning(f"Grok call failed ({e}), falling back to Anthropic...")

        if self._anthropic_key:
            return self._call_anthropic(system_prompt, user_message, max_tokens)

        raise RuntimeError("All LLM providers failed. Check API keys.")

    # ── Private Providers ─────────────────────────────────────────────────────

    def _call_grok(
        self, system_prompt: str, user_message: str, max_tokens: int
    ) -> str:
        """Call xAI Grok via OpenAI-compatible SDK."""
        from openai import OpenAI  # lazy import

        client = OpenAI(
            api_key=self._xai_key,
            base_url=GROK_BASE_URL,
        )
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(
        self, system_prompt: str, user_message: str, max_tokens: int
    ) -> str:
        """Call Anthropic Claude Haiku as fallback."""
        import anthropic  # lazy import

        client = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model=ANTHROPIC_FALLBACK_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text if response.content else ""
