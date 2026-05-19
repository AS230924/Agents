from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import StartupAnalysis, ComparableAnalysis
from ..config.prompts import COMPARABLE_FINDER_SYSTEM_PROMPT
from ..core.web_search import web_search, format_search_results


class ComparableFinderAgent(BaseAgent):
    def run(self, analysis: StartupAnalysis) -> ComparableAnalysis:
        q1 = f"{analysis.startup} competitors funded startups 2024 2025 seed series a"
        q2 = f"{analysis.stack_layer.layer} {analysis.summary[:120]} funded startups"
        search_blob = format_search_results(web_search(q1, 6) + web_search(q2, 6), max_chars=3500)

        user_message = f"""Startup: {analysis.startup}
Website: {analysis.website}
Summary: {analysis.summary}
Market: {analysis.evaluation}
Layer: {analysis.stack_layer.layer}

Web research:
{search_blob}
"""
        raw = self._llm.call(COMPARABLE_FINDER_SYSTEM_PROMPT, user_message, max_tokens=2200)
        return ComparableAnalysis(**self._parse_json(raw))
