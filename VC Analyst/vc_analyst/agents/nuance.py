"""
Step 7 — Nuance Agent (Enrichment Layer)
Produces TAM estimates, competitive landscape, risk factors, moat analysis,
and an optional investment memo for Watch/Strong Opportunity verdicts.
"""

from __future__ import annotations
import logging

from .base import BaseAgent
from ..core.llm_client import LLMClient
from ..models.schemas import (
    StartupAnalysis,
    NuanceReport,
    TAMEstimate,
    RiskFactor,
    MoatAnalysis,
    CompetitiveLandscape,
)
from ..config.prompts import (
    NUANCE_TAM_COMPETITIVE_PROMPT,
    NUANCE_RISK_MOAT_PROMPT,
    NUANCE_MEMO_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

# Only generate investment memo for these verdicts
MEMO_VERDICTS = {"Watch", "Strong Opportunity"}


class NuanceAgent(BaseAgent):
    """
    Enrichment agent that adds deep-dive analysis on top of the core evaluation.
    Makes up to 3 LLM calls:
      1. TAM + Competitive Landscape
      2. Risk Factors + Moat Analysis
      3. Investment Memo (conditional on verdict)
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(llm_client)

    def run(self, analysis: StartupAnalysis) -> NuanceReport:
        """
        Args:
            analysis: The assembled StartupAnalysis from prior pipeline steps.

        Returns:
            NuanceReport with all enrichment layers populated.
        """
        # Build a comprehensive context string for all sub-calls
        context = self._build_context(analysis)

        # Sub-call 1: TAM + Competitive Landscape
        tam_data, competitive_data = self._run_tam_competitive(context)

        # Sub-call 2: Risk Factors + Moat Analysis
        risks, moat = self._run_risk_moat(context)

        # Sub-call 3: Investment Memo (conditional)
        memo = None
        if analysis.verdict.verdict in MEMO_VERDICTS:
            memo = self._run_investment_memo(context, analysis.verdict.verdict)

        return NuanceReport(
            tam_estimate=tam_data,
            traction_summary=_extract_traction(analysis),
            top_risks=risks,
            moat_analysis=moat,
            competitive_landscape=competitive_data,
            investment_memo=memo,
        )

    # ── Sub-call 1: TAM + Competitive Landscape ───────────────────────────────

    def _run_tam_competitive(
        self, context: str
    ) -> tuple[TAMEstimate, CompetitiveLandscape]:
        user_message = f"""Analyze this startup for market sizing and competitive positioning:

{context}

Return the JSON object as instructed."""

        raw = self._llm.call(NUANCE_TAM_COMPETITIVE_PROMPT, user_message, max_tokens=1500)
        data = self._parse_json(raw)

        tam_raw = data.get("tam_estimate", {})
        comp_raw = data.get("competitive_landscape", {})

        # Ensure key_competitors is a list
        competitors = comp_raw.get("key_competitors", [])
        if isinstance(competitors, str):
            competitors = [c.strip() for c in competitors.split(",") if c.strip()]

        tam = TAMEstimate(
            tam=str(tam_raw.get("tam", "unknown")),
            sam=str(tam_raw.get("sam", "unknown")),
            reasoning=str(tam_raw.get("reasoning", "")),
        )
        competitive = CompetitiveLandscape(
            key_competitors=competitors,
            differentiation=str(comp_raw.get("differentiation", "")),
            strategic_position=str(comp_raw.get("strategic_position", "unknown")),
        )
        return tam, competitive

    # ── Sub-call 2: Risk Factors + Moat Analysis ──────────────────────────────

    def _run_risk_moat(self, context: str) -> tuple[list[RiskFactor], MoatAnalysis]:
        user_message = f"""Analyze the investment risks and competitive moat for this startup:

{context}

Return the JSON object as instructed."""

        raw = self._llm.call(NUANCE_RISK_MOAT_PROMPT, user_message, max_tokens=1500)
        data = self._parse_json(raw)

        risks_raw = data.get("top_risks", [])
        moat_raw = data.get("moat_analysis", {})

        risks = []
        for r in risks_raw[:3]:  # cap at 3
            if isinstance(r, dict):
                risks.append(RiskFactor(
                    risk=str(r.get("risk", "Unknown Risk")),
                    severity=str(r.get("severity", "Medium")),
                    description=str(r.get("description", "")),
                ))

        moat_types = moat_raw.get("moat_type", [])
        if isinstance(moat_types, str):
            moat_types = [t.strip() for t in moat_types.split(",") if t.strip()]

        moat = MoatAnalysis(
            moat_type=moat_types,
            moat_strength=str(moat_raw.get("moat_strength", "Weak")),
            assessment=str(moat_raw.get("assessment", "")),
        )
        return risks, moat

    # ── Sub-call 3: Investment Memo ────────────────────────────────────────────

    def _run_investment_memo(self, context: str, verdict: str) -> str:
        user_message = f"""Write a structured investment memo for this {verdict} startup:

{context}

Follow the memo format exactly as instructed."""

        return self._llm.call(
            NUANCE_MEMO_SYSTEM_PROMPT, user_message, max_tokens=600
        ).strip()

    # ── Context Builder ────────────────────────────────────────────────────────

    def _build_context(self, analysis: StartupAnalysis) -> str:
        """Build a rich context string from the full analysis for nuance sub-calls."""
        eval_ = analysis.evaluation
        score_ = analysis.scoring

        strengths = [
            label for label, field in [
                ("Market Size", eval_.market_size.score),
                ("Market Growth", eval_.market_growth.score),
                ("Problem Severity", eval_.problem_severity.score),
                ("Clear Wedge", eval_.clear_wedge.score),
                ("Unique Insight", eval_.unique_insight.score),
                ("Data Moat", eval_.data_moat.score),
                ("Workflow Lock-in", eval_.workflow_lockin.score),
                ("Distribution Advantage", eval_.distribution_advantage.score),
                ("Network Effects", eval_.network_effects.score),
                ("Platform Potential", eval_.platform_potential.score),
                ("Competition Intensity", eval_.competition_intensity.score),
                ("Founder Advantage", eval_.founder_advantage.score),
            ] if field == 1
        ]

        return f"""Company: {analysis.startup}
Website: {analysis.website}
Stage: {analysis.stage_estimate}
Summary: {analysis.summary}

AI Stack Layer: {analysis.stack_layer.layer}
Layer Reason: {analysis.stack_layer.reason}

Wrapper Risk: {analysis.wrapper_risk.risk_level}
Wrapper Reason: {analysis.wrapper_risk.reason}
Proprietary Signals: {", ".join(analysis.wrapper_risk.proprietary_signals) or "None"}

Base Score: {score_.base_score}/12
Layer Adjustment: {score_.layer_adjustment:+d}
Wrapper Penalty: {score_.wrapper_penalty:+d}
Final Score: {score_.final_score}
Verdict: {analysis.verdict.verdict}
Key Insight: {analysis.verdict.key_insight}

Strengths (scored 1): {", ".join(strengths) if strengths else "None"}

Evaluator Notes:
- Market: {eval_.market_size.rationale}
- Growth: {eval_.market_growth.rationale}
- Problem: {eval_.problem_severity.rationale}
- Moat: {eval_.data_moat.rationale}
- Founder: {eval_.founder_advantage.rationale}"""


def _extract_traction(analysis: StartupAnalysis) -> str:
    """Fallback traction extraction from summary."""
    summary = analysis.summary
    keywords = ["revenue", "users", "customers", "ARR", "MRR", "growth",
                "raised", "funded", "Series", "seed", "beta", "waitlist"]
    relevant = [line for line in summary.split(".") if any(k.lower() in line.lower() for k in keywords)]
    return ". ".join(relevant).strip() if relevant else "Traction signals not available."
