from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import StartupAnalysis, CategoryInsight
from ..config.prompts import CATEGORY_RESEARCHER_SYSTEM_PROMPT
from ..core.web_search import web_search, format_search_results


class CategoryResearcherAgent(BaseAgent):
    def run(self, analysis: StartupAnalysis) -> CategoryInsight:
        q1 = f"{analysis.stack_layer.layer} {analysis.startup} market trends 2024 2025"
        q2 = f"{analysis.summary[:120]} venture investment thesis"
        search_blob = format_search_results(web_search(q1, 6) + web_search(q2, 6), max_chars=3500)

        user_message = f"""Startup: {analysis.startup}
Summary: {analysis.summary}
Layer: {analysis.stack_layer.layer}
Score: {analysis.scoring.final_score}
Wrapper risk: {analysis.wrapper_risk.risk_level}

Web research:
{search_blob}
"""
        raw = self._llm.call(CATEGORY_RESEARCHER_SYSTEM_PROMPT, user_message, max_tokens=1800)
        return CategoryInsight(**self._parse_json(raw))
