"""
Step 6 — Verdict Agent
Maps the final score to a verdict label and generates an investor key insight.
"""

from __future__ import annotations
import logging

from .base import BaseAgent
from ..core.llm_client import LLMClient
from ..models.schemas import (
    StartupData,
    TwelvePointResult,
    StackLayerResult,
    WrapperRiskResult,
    ScoringResult,
    VerdictResult,
)
from ..config.frameworks import get_verdict_label
from ..config.prompts import VERDICT_INSIGHT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class VerdictAgent(BaseAgent):
    """
    Determines the investment verdict label (deterministic) and generates
    a Key Insight using the LLM.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)

    def run(
        self,
        score: ScoringResult,
        research: StartupData,
        evaluation: TwelvePointResult,
        layer: StackLayerResult,
        wrapper: WrapperRiskResult,
    ) -> VerdictResult:
        """
        Args:
            score: Final scoring result.
            research: Startup data.
            evaluation: 12-point evaluation.
            layer: Stack layer classification.
            wrapper: Wrapper risk assessment.

        Returns:
            VerdictResult with verdict label and key insight.
        """
        # Step 1: Deterministic verdict label
        verdict_label = get_verdict_label(score.final_score)

        # Step 2: LLM-generated key insight
        # Build a rich summary for the LLM to work with
        strengths = [
            k for k, v in {
                "Market Size": evaluation.market_size.score,
                "Market Growth": evaluation.market_growth.score,
                "Problem Severity": evaluation.problem_severity.score,
                "Clear Wedge": evaluation.clear_wedge.score,
                "Unique Insight": evaluation.unique_insight.score,
                "Data Moat": evaluation.data_moat.score,
                "Workflow Lock-in": evaluation.workflow_lockin.score,
                "Distribution Advantage": evaluation.distribution_advantage.score,
                "Network Effects": evaluation.network_effects.score,
                "Platform Potential": evaluation.platform_potential.score,
                "Competition Intensity": evaluation.competition_intensity.score,
                "Founder Advantage": evaluation.founder_advantage.score,
            }.items() if v == 1
        ]
        weaknesses = [
            k for k, v in {
                "Market Size": evaluation.market_size.score,
                "Market Growth": evaluation.market_growth.score,
                "Problem Severity": evaluation.problem_severity.score,
                "Clear Wedge": evaluation.clear_wedge.score,
                "Unique Insight": evaluation.unique_insight.score,
                "Data Moat": evaluation.data_moat.score,
                "Workflow Lock-in": evaluation.workflow_lockin.score,
                "Distribution Advantage": evaluation.distribution_advantage.score,
                "Network Effects": evaluation.network_effects.score,
                "Platform Potential": evaluation.platform_potential.score,
                "Competition Intensity": evaluation.competition_intensity.score,
                "Founder Advantage": evaluation.founder_advantage.score,
            }.items() if v == 0
        ]

        user_message = f"""Write a 1-2 sentence Key Insight for this startup analysis:

Company: {research.name}
Summary: {research.summary}
AI Stack Layer: {layer.layer}
Base Score: {score.base_score}/12
Layer Adjustment: {score.layer_adjustment:+d} ({layer.layer})
Wrapper Risk: {wrapper.risk_level} (penalty: {score.wrapper_penalty:+d})
Final Score: {score.final_score}
Verdict: {verdict_label}

Strengths (scored 1): {", ".join(strengths) if strengths else "None"}
Weaknesses (scored 0): {", ".join(weaknesses) if weaknesses else "None"}

Write a single, precise Key Insight that captures WHY this startup received this verdict.
Reference the most important signal — positive or negative."""

        raw_insight = self._llm.call(VERDICT_INSIGHT_SYSTEM_PROMPT, user_message, max_tokens=200)
        key_insight = raw_insight.strip().strip('"').strip("'")

        return VerdictResult(
            verdict=verdict_label,
            key_insight=key_insight,
        )
