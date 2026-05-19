from __future__ import annotations

from .base import BaseAgent
from ..models.schemas import StartupAnalysis, SectorClassificationResult
from ..config.prompts import SECTOR_CLASSIFIER_SYSTEM_PROMPT
from ..core.web_search import web_search, format_search_results


class SectorClassifierAgent(BaseAgent):
    """Deep-mode first step: classify startup across broad sectors and sub-sectors."""

    def run(self, analysis: StartupAnalysis) -> SectorClassificationResult:
        q = f"{analysis.startup} company category market segment"
        search_blob = format_search_results(web_search(q, 5), max_chars=1800)
        user_message = f"""Startup: {analysis.startup}
Website: {analysis.website}
Summary: {analysis.summary}
AI stack layer: {analysis.stack_layer.layer}

Web context:
{search_blob}
"""
        raw = self._llm.call(SECTOR_CLASSIFIER_SYSTEM_PROMPT, user_message, max_tokens=800)
        return SectorClassificationResult(**self._parse_json(raw))
