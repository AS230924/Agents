"""
Step 3 — Evaluator Agent
Scores the startup on all 12 venture evaluation criteria (0 or 1 each).
"""

from __future__ import annotations
import logging

from .base import BaseAgent
from ..core.llm_client import LLMClient
from ..models.schemas import StartupData, StackLayerResult, TwelvePointResult, CriterionScore
from ..config.prompts import EVALUATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

TWELVE_CRITERIA = [
    "market_size", "market_growth", "problem_severity", "clear_wedge",
    "unique_insight", "data_moat", "workflow_lockin", "distribution_advantage",
    "network_effects", "platform_potential", "competition_intensity", "founder_advantage",
]


class EvaluatorAgent(BaseAgent):
    """
    Runs the 12-point venture evaluation and returns structured scores with rationales.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)

    def run(self, research: StartupData, layer: StackLayerResult) -> TwelvePointResult:
        """
        Args:
            research: Startup data from ResearcherAgent.
            layer: AI stack classification from ClassifierAgent.

        Returns:
            TwelvePointResult with all 12 criterion scores and rationales.
        """
        user_message = f"""Evaluate this startup on all 12 venture criteria:

Company: {research.name}
Website: {research.website}
Summary: {research.summary}
Market: {research.market}
Tech Stack: {research.tech_stack}
Business Model: {research.business_model}
Team Signals: {research.team_signals}
Traction Signals: {research.traction_signals}
Stage: {research.stage_estimate}
AI Stack Layer: {layer.layer}

Return the JSON object as instructed. Score each criterion 0 or 1 with a 1-sentence rationale."""

        raw = self._llm.call(EVALUATOR_SYSTEM_PROMPT, user_message, max_tokens=3000)
        data = self._parse_json(raw)

        # Normalize and validate each criterion
        normalized: dict = {}
        for criterion in TWELVE_CRITERIA:
            raw_val = data.get(criterion, {})

            if isinstance(raw_val, dict):
                score = int(raw_val.get("score", 0))
                rationale = str(raw_val.get("rationale", "No rationale provided."))
            elif isinstance(raw_val, int):
                # LLM returned just an int (shouldn't happen but handle gracefully)
                score = raw_val
                rationale = "No rationale provided."
            else:
                score = 0
                rationale = "Unable to evaluate."

            # Clamp to 0 or 1
            score = max(0, min(1, score))
            normalized[criterion] = CriterionScore(score=score, rationale=rationale)

        return TwelvePointResult(**normalized)
