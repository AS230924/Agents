"""
Step 4 — Wrapper Detector Agent
Assesses whether the startup is primarily an AI wrapper (LOW / MEDIUM / HIGH risk).
"""

from __future__ import annotations
import logging

from .base import BaseAgent
from ..core.llm_client import LLMClient
from ..models.schemas import StartupData, TwelvePointResult, WrapperRiskResult
from ..config.prompts import WRAPPER_DETECTOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}


class WrapperDetectorAgent(BaseAgent):
    """
    Detects AI wrapper risk: LOW / MEDIUM / HIGH.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)

    def run(
        self,
        research: StartupData,
        evaluation: TwelvePointResult,
    ) -> WrapperRiskResult:
        """
        Args:
            research: Startup data from ResearcherAgent.
            evaluation: 12-point scores to provide additional context.

        Returns:
            WrapperRiskResult with risk level and reasoning.
        """
        # Build context summary from evaluation scores
        eval_context = (
            f"Data Moat score: {evaluation.data_moat.score}/1 — {evaluation.data_moat.rationale}\n"
            f"Unique Insight score: {evaluation.unique_insight.score}/1 — {evaluation.unique_insight.rationale}\n"
            f"Workflow Lock-in score: {evaluation.workflow_lockin.score}/1 — {evaluation.workflow_lockin.rationale}\n"
            f"Network Effects score: {evaluation.network_effects.score}/1 — {evaluation.network_effects.rationale}"
        )

        user_message = f"""Assess the AI wrapper risk for this startup:

Company: {research.name}
Summary: {research.summary}
Tech Stack: {research.tech_stack}
Business Model: {research.business_model}
Traction Signals: {research.traction_signals}

Key Evaluation Signals:
{eval_context}

Return the JSON object as instructed. Be precise — hype does not equal proprietary technology."""

        raw = self._llm.call(WRAPPER_DETECTOR_SYSTEM_PROMPT, user_message)
        data = self._parse_json(raw)

        # Normalize risk level
        risk_level = str(data.get("risk_level", "MEDIUM")).upper().strip()
        if risk_level not in VALID_RISK_LEVELS:
            logger.warning(f"Invalid wrapper risk level '{risk_level}', defaulting to MEDIUM")
            risk_level = "MEDIUM"

        # Ensure list fields are actually lists
        proprietary_signals = data.get("proprietary_signals", [])
        wrapper_signals = data.get("wrapper_signals", [])
        if not isinstance(proprietary_signals, list):
            proprietary_signals = [str(proprietary_signals)]
        if not isinstance(wrapper_signals, list):
            wrapper_signals = [str(wrapper_signals)]

        return WrapperRiskResult(
            risk_level=risk_level,
            reason=str(data.get("reason", "")),
            proprietary_signals=proprietary_signals,
            wrapper_signals=wrapper_signals,
        )
