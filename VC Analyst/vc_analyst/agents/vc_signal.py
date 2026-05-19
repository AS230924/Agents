from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import StartupAnalysis, CategoryInsight, VCLandscape
from ..config.prompts import VC_SIGNAL_SYSTEM_PROMPT
from ..core.web_search import web_search, format_search_results


class VCSignalAgent(BaseAgent):
    def run(self, analysis: StartupAnalysis, category: CategoryInsight) -> VCLandscape:
        queries = [
            f"YC {category.category_name} startup W24 W25",
            f"Antler {category.category_name} portfolio",
            f"a16z Sequoia General Catalyst {category.category_name} investment",
        ]
        results = []
        for q in queries:
            results.extend(web_search(q, 5))
        search_blob = format_search_results(results, max_chars=3800)
        user_message = f"""Startup: {analysis.startup}
Category: {category.category_name}
Category momentum: {category.momentum}
Summary: {analysis.summary}

Web research:
{search_blob}
"""
        raw = self._llm.call(VC_SIGNAL_SYSTEM_PROMPT, user_message, max_tokens=2200)
        return VCLandscape(**self._parse_json(raw))
