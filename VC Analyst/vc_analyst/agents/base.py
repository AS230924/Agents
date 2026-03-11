"""
Abstract base class for all VC Analyst agents.
"""

from __future__ import annotations
import json
import re
import logging
from abc import ABC, abstractmethod
from pydantic import BaseModel

from ..core.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class providing:
    - A shared LLMClient instance
    - JSON parsing with markdown fence stripping and error recovery
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()

    @abstractmethod
    def run(self, *args, **kwargs) -> BaseModel:
        """Execute the agent and return a typed Pydantic model."""
        ...

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> dict:
        """
        Parse a JSON object from an LLM response.
        Handles:
        - Markdown code fences (```json ... ```)
        - Leading/trailing whitespace
        - Single-line and multi-line responses
        """
        # Strip markdown code fences
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
        text = text.strip()

        # Find first { to last } (handles text before/after JSON)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw text:\n{text[:500]}")
            raise ValueError(f"Failed to parse LLM JSON response: {e}") from e
