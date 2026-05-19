from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import DeepStartupAnalysis, PassDecision
from ..config.prompts import PASS_DECISION_SYSTEM_PROMPT


class PassDecisionAgent(BaseAgent):
    def run(self, deep: DeepStartupAnalysis) -> PassDecision:
        base = deep.base
        user_message = f"""Startup: {base.startup}
Summary: {base.summary}
Score: {base.scoring.final_score}
Verdict: {base.verdict.verdict}
Wrapper: {base.wrapper_risk.risk_level}
Comparables: {deep.comparables}
Category insight: {deep.category_insight}
VC landscape: {deep.vc_landscape}
Founder fit: {deep.founder_fit}
Sector classification: {deep.sector_classification}
"""
        raw = self._llm.call(PASS_DECISION_SYSTEM_PROMPT, user_message, max_tokens=2200)
        return PassDecision(**self._parse_json(raw))
