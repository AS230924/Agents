"""
Step 2 — Classifier Agent
Classifies a startup into one of the 9 AI Stack Layers.
"""

from __future__ import annotations
import logging

from .base import BaseAgent
from ..core.llm_client import LLMClient
from ..models.schemas import StartupData, StackLayerResult
from ..config.prompts import CLASSIFIER_SYSTEM_PROMPT
from ..config.frameworks import AI_STACK_LAYERS

logger = logging.getLogger(__name__)


class ClassifierAgent(BaseAgent):
    """
    Classifies the startup into one of 9 AI stack layers.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)

    def run(self, research: StartupData) -> StackLayerResult:
        """
        Args:
            research: The structured startup data from ResearcherAgent.

        Returns:
            StackLayerResult with layer name and rationale.
        """
        user_message = f"""Classify this startup into the correct AI Stack Layer:

Company: {research.name}
Website: {research.website}
Summary: {research.summary}
Market: {research.market}
Tech Stack: {research.tech_stack}
Business Model: {research.business_model}
Team Signals: {research.team_signals}

Return the JSON object as instructed."""

        raw = self._llm.call(CLASSIFIER_SYSTEM_PROMPT, user_message)
        data = self._parse_json(raw)

        # Validate that the layer is one of the 9 defined layers
        layer = data.get("layer", "")
        if layer not in AI_STACK_LAYERS:
            logger.warning(
                f"Classifier returned unknown layer '{layer}'. "
                f"Attempting fuzzy match..."
            )
            layer = self._fuzzy_match_layer(layer)
            data["layer"] = layer

        return StackLayerResult(**data)

    def _fuzzy_match_layer(self, raw_layer: str) -> str:
        """Find the closest matching layer name (case-insensitive substring match)."""
        raw_lower = raw_layer.lower()
        for valid_layer in AI_STACK_LAYERS:
            if any(word in raw_lower for word in valid_layer.lower().split()):
                return valid_layer
        logger.warning(f"No fuzzy match found for '{raw_layer}'. Defaulting to 'AI Applications'.")
        return "AI Applications"
