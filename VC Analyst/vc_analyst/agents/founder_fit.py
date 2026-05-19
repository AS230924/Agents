from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import StartupAnalysis, FounderFitAnalysis
from ..config.prompts import FOUNDER_FIT_SYSTEM_PROMPT
from ..core.web_search import web_search, format_search_results


class FounderFitAgent(BaseAgent):
    def run(self, analysis: StartupAnalysis) -> FounderFitAnalysis:
        q1 = f"{analysis.startup} founders background LinkedIn"
        q2 = f"{analysis.startup} founder prior company"
        search_blob = format_search_results(web_search(q1, 5) + web_search(q2, 5), max_chars=2500)

        user_message = f"""Startup: {analysis.startup}
Team signals: {analysis.summary}
Base verdict: {analysis.verdict.verdict}
Base score: {analysis.scoring.final_score}

Web research:
{search_blob}
"""
        raw = self._llm.call(FOUNDER_FIT_SYSTEM_PROMPT, user_message, max_tokens=2200)
        return FounderFitAnalysis(**self._parse_json(raw))
