"""
Step 5 — Scorer Agent (No LLM)
Applies deterministic scoring rules: base score + layer adjustment + wrapper penalty.
"""

from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import (
    TwelvePointResult,
    StackLayerResult,
    WrapperRiskResult,
    ScoringResult,
)
from ..config.frameworks import LAYER_ADJUSTMENTS, WRAPPER_PENALTIES


class ScorerAgent(BaseAgent):
    """
    Pure deterministic scorer — no LLM calls.
    Computes the final adjusted investment score.
    """

    def run(
        self,
        evaluation: TwelvePointResult,
        layer: StackLayerResult,
        wrapper: WrapperRiskResult,
    ) -> ScoringResult:
        """
        Args:
            evaluation: 12-point scores from EvaluatorAgent.
            layer: Stack layer classification from ClassifierAgent.
            wrapper: Wrapper risk from WrapperDetectorAgent.

        Returns:
            ScoringResult with base, adjustments, and final score.
        """
        base_score = evaluation.total

        layer_adjustment = LAYER_ADJUSTMENTS.get(layer.layer, 0)
        wrapper_penalty = WRAPPER_PENALTIES.get(wrapper.risk_level, 0)

        final_score = base_score + layer_adjustment + wrapper_penalty
        # Don't let score go below 0
        final_score = max(0, final_score)

        return ScoringResult(
            base_score=base_score,
            layer_adjustment=layer_adjustment,
            wrapper_penalty=wrapper_penalty,
            final_score=final_score,
        )
