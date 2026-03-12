"""
VC Analyst — Main Pipeline Orchestrator
Runs the full 7-step evaluation pipeline for one or more startups.
Also contains the output formatter that renders structured markdown.
"""

from __future__ import annotations
import os
import logging
from typing import Callable

from .llm_client import LLMClient
from .tracer import get_tracer
from ..agents import (
    ResearcherAgent,
    ClassifierAgent,
    EvaluatorAgent,
    WrapperDetectorAgent,
    ScorerAgent,
    VerdictAgent,
    NuanceAgent,
)
from ..models.schemas import StartupAnalysis
from ..config.frameworks import CRITERIA_LABELS

logger = logging.getLogger(__name__)


def _use_browser_research() -> bool:
    """Check if browser research mode is enabled via env var."""
    return os.getenv("USE_BROWSER_RESEARCH", "0").strip().lower() in ("1", "true", "yes")


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def analyze_startup(
    input_text: str,
    progress_callback: Callable[[str], None] | None = None,
    llm_client: LLMClient | None = None,
) -> StartupAnalysis:
    """
    Run the full VC Analyst pipeline for a single startup.

    Args:
        input_text: URL or text description of the startup.
        progress_callback: Optional function called with status strings.
        llm_client: Optional shared LLMClient instance (reused across agents).

    Returns:
        StartupAnalysis with all evaluation results.
    """
    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    client = llm_client or LLMClient()
    label = input_text.strip()[:50]
    tracer = get_tracer()

    with tracer.start_as_current_span("startup_analysis") as root_span:
        root_span.set_attribute("input", label)
        root_span.set_attribute("browser_research", _use_browser_research())

        # Step 1: Research (basic httpx scraper OR browser + web search)
        with tracer.start_as_current_span("step.research"):
            if _use_browser_research():
                from ..agents.browser_researcher import BrowserResearchAgent
                researcher = BrowserResearchAgent(client)
                caps = researcher.capabilities
                _progress(f"🌐 Browser Research ({caps['mode']}) — Researching {label}…")
            else:
                researcher = ResearcherAgent(client)
                _progress(f"🔍 Researching {label}…")
            research = researcher.run(input_text)
            root_span.set_attribute("startup.name", research.name)

        # Step 2: AI Stack Layer Classification
        with tracer.start_as_current_span("step.classify"):
            _progress(f"🏗️  Classifying AI stack layer for {research.name}…")
            classifier = ClassifierAgent(client)
            layer = classifier.run(research)

        # Step 3: 12-Point Evaluation
        with tracer.start_as_current_span("step.evaluate"):
            _progress(f"📊 Running 12-point evaluation for {research.name}…")
            evaluator = EvaluatorAgent(client)
            evaluation = evaluator.run(research, layer)

        # Step 4: Wrapper Risk Detection
        with tracer.start_as_current_span("step.wrapper_detect"):
            _progress(f"🛡️  Detecting AI wrapper risk for {research.name}…")
            wrapper_detector = WrapperDetectorAgent(client)
            wrapper = wrapper_detector.run(research, evaluation)

        # Step 5: Signal Scoring (no LLM)
        with tracer.start_as_current_span("step.score"):
            _progress(f"🧮 Calculating final score for {research.name}…")
            scorer = ScorerAgent(client)
            score = scorer.run(evaluation, layer, wrapper)

        # Step 6: Investment Verdict
        with tracer.start_as_current_span("step.verdict"):
            _progress(f"⚖️  Generating investment verdict for {research.name}…")
            verdict_agent = VerdictAgent(client)
            verdict = verdict_agent.run(score, research, evaluation, layer, wrapper)

        # Assemble partial analysis for nuance enrichment
        partial = StartupAnalysis(
            startup=research.name,
            website=research.website,
            summary=research.summary,
            stage_estimate=research.stage_estimate,
            stack_layer=layer,
            evaluation=evaluation,
            wrapper_risk=wrapper,
            scoring=score,
            verdict=verdict,
            nuance=None,
        )

        # Step 7: Nuance Enrichment (TAM, risks, moat, memo)
        with tracer.start_as_current_span("step.nuance"):
            _progress(f"🔬 Running deep-dive analysis for {research.name}…")
            nuance_agent = NuanceAgent(client)
            nuance_report = nuance_agent.run(partial)

        # Fix traction_summary using the researcher output
        from ..models.schemas import NuanceReport
        nuance_report = NuanceReport(
            tam_estimate=nuance_report.tam_estimate,
            traction_summary=research.traction_signals,
            top_risks=nuance_report.top_risks,
            moat_analysis=nuance_report.moat_analysis,
            competitive_landscape=nuance_report.competitive_landscape,
            investment_memo=nuance_report.investment_memo,
        )

        # Record final result attributes on root span
        root_span.set_attribute("result.final_score", score.final_score)
        root_span.set_attribute("result.verdict", verdict.verdict)
        root_span.set_attribute("result.layer", layer.layer)
        root_span.set_attribute("result.wrapper_risk", wrapper.risk_level)

        return StartupAnalysis(
            startup=research.name,
            website=research.website,
            summary=research.summary,
            stage_estimate=research.stage_estimate,
            stack_layer=layer,
            evaluation=evaluation,
            wrapper_risk=wrapper,
            scoring=score,
            verdict=verdict,
            nuance=nuance_report,
        )


def analyze_multiple(
    inputs: list[str],
    progress_callback: Callable[[str], None] | None = None,
) -> list[StartupAnalysis]:
    """
    Analyze multiple startups and return them ranked by final score (highest first).
    """
    client = LLMClient()
    results: list[StartupAnalysis] = []

    for i, inp in enumerate(inputs):
        inp = inp.strip()
        if not inp:
            continue
        def cb(msg: str, idx: int = i + 1, total: int = len(inputs)) -> None:
            if progress_callback:
                progress_callback(f"({idx}/{total}) {msg}")

        try:
            result = analyze_startup(inp, progress_callback=cb, llm_client=client)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to analyze '{inp}': {e}")
            if progress_callback:
                progress_callback(f"❌ Error analyzing '{inp[:40]}': {e}")

    return sorted(results, key=lambda x: x.scoring.final_score, reverse=True)


# ─── Output Formatter ─────────────────────────────────────────────────────────

def _score_bar(score: int, max_score: int = 1) -> str:
    """Visual indicator for 0/1 scores."""
    return "✅" if score == 1 else "❌"


def format_analysis(analysis: StartupAnalysis) -> str:
    """
    Render a StartupAnalysis as structured markdown for display in Gradio.
    """
    e = analysis.evaluation
    s = analysis.scoring
    n = analysis.nuance

    # ── Header ─────────────────────────────────────────────────────────────
    lines = [
        "---",
        f"## 🏢 {analysis.startup}",
        f"**Website:** {analysis.website}  |  **Stage:** {analysis.stage_estimate}",
        "",
        f"**Summary:** {analysis.summary}",
        "",
    ]

    # ── AI Stack Layer ─────────────────────────────────────────────────────
    lines += [
        "### 🏗️ AI Stack Layer",
        f"**{analysis.stack_layer.layer}**",
        f"> {analysis.stack_layer.reason}",
        "",
    ]

    # ── 12-Point Evaluation ────────────────────────────────────────────────
    lines += [
        "### 📊 12-Point Venture Evaluation",
        "",
        "| Criterion | Score | Rationale |",
        "|-----------|:-----:|-----------|",
    ]

    criteria_fields = [
        ("market_size", e.market_size),
        ("market_growth", e.market_growth),
        ("problem_severity", e.problem_severity),
        ("clear_wedge", e.clear_wedge),
        ("unique_insight", e.unique_insight),
        ("data_moat", e.data_moat),
        ("workflow_lockin", e.workflow_lockin),
        ("distribution_advantage", e.distribution_advantage),
        ("network_effects", e.network_effects),
        ("platform_potential", e.platform_potential),
        ("competition_intensity", e.competition_intensity),
        ("founder_advantage", e.founder_advantage),
    ]
    for key, criterion in criteria_fields:
        label = CRITERIA_LABELS.get(key, key.replace("_", " ").title())
        icon = _score_bar(criterion.score)
        lines.append(f"| {label} | {icon} {criterion.score}/1 | {criterion.rationale} |")

    lines += [
        "",
        f"**Total Base Score: {e.total}/12**",
        "",
    ]

    # ── Wrapper Risk ───────────────────────────────────────────────────────
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(
        analysis.wrapper_risk.risk_level, "⚪"
    )
    lines += [
        "### 🛡️ AI Wrapper Risk",
        f"{risk_emoji} **{analysis.wrapper_risk.risk_level}** — {analysis.wrapper_risk.reason}",
    ]
    if analysis.wrapper_risk.proprietary_signals:
        lines.append(
            "- ✅ **Proprietary signals:** "
            + " | ".join(analysis.wrapper_risk.proprietary_signals)
        )
    if analysis.wrapper_risk.wrapper_signals:
        lines.append(
            "- ⚠️ **Wrapper signals:** "
            + " | ".join(analysis.wrapper_risk.wrapper_signals)
        )
    lines.append("")

    # ── Scoring Breakdown ─────────────────────────────────────────────────
    adj_sign = "+" if s.layer_adjustment >= 0 else ""
    pen_sign = "+" if s.wrapper_penalty >= 0 else ""
    lines += [
        "### 🧮 Scoring Breakdown",
        "",
        f"| Component | Value |",
        f"|-----------|-------|",
        f"| Base Score (12-point) | {s.base_score}/12 |",
        f"| Layer Adjustment ({analysis.stack_layer.layer}) | {adj_sign}{s.layer_adjustment} |",
        f"| Wrapper Penalty ({analysis.wrapper_risk.risk_level}) | {pen_sign}{s.wrapper_penalty} |",
        f"| **Final Adjusted Score** | **{s.final_score}** |",
        "",
    ]

    # ── Verdict ────────────────────────────────────────────────────────────
    verdict_emoji = {
        "Ignore": "🚫",
        "Weak Signal": "⚡",
        "Watch": "👀",
        "Strong Opportunity": "🚀",
    }.get(analysis.verdict.verdict, "❓")

    lines += [
        "### ⚖️ Investment Verdict",
        f"## {verdict_emoji} {analysis.verdict.verdict}",
        f"**Key Insight:** {analysis.verdict.key_insight}",
        "",
    ]

    # ── Deep Dive (Nuance) ─────────────────────────────────────────────────
    if n:
        lines += ["---", "### 🔬 Deep Dive Analysis", ""]

        # TAM
        lines += [
            "#### 📈 Market Sizing",
            f"- **TAM:** {n.tam_estimate.tam}",
            f"- **SAM:** {n.tam_estimate.sam}",
            f"- *{n.tam_estimate.reasoning}*",
            "",
        ]

        # Traction
        if n.traction_summary and n.traction_summary.lower() != "unknown":
            lines += [
                "#### 🏃 Traction Signals",
                f"{n.traction_summary}",
                "",
            ]

        # Competitive Landscape
        lines += [
            "#### ⚔️ Competitive Landscape",
            f"**Position:** {n.competitive_landscape.strategic_position}",
            f"**Key Competitors:** {', '.join(n.competitive_landscape.key_competitors) or 'None identified'}",
            f"**Differentiation:** {n.competitive_landscape.differentiation}",
            "",
        ]

        # Moat Analysis
        moat_strength_emoji = {"Weak": "🔓", "Moderate": "🔐", "Strong": "🔒"}.get(
            n.moat_analysis.moat_strength, "🔓"
        )
        lines += [
            "#### 🏰 Moat Analysis",
            f"{moat_strength_emoji} **Strength: {n.moat_analysis.moat_strength}**",
            f"**Types:** {', '.join(n.moat_analysis.moat_type) or 'None identified'}",
            f"{n.moat_analysis.assessment}",
            "",
        ]

        # Top Risks
        if n.top_risks:
            lines += ["#### ⚠️ Top Investment Risks", ""]
            for i, risk in enumerate(n.top_risks, 1):
                sev_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk.severity, "⚪")
                lines.append(
                    f"{i}. **{risk.risk}** {sev_emoji} _{risk.severity}_ — {risk.description}"
                )
            lines.append("")

        # Investment Memo
        if n.investment_memo:
            lines += [
                "---",
                "### 📋 Investment Memo",
                "",
                n.investment_memo,
                "",
            ]

    lines.append("---")
    return "\n".join(lines)


def format_comparison_table(analyses: list[StartupAnalysis]) -> str:
    """
    Render a ranked comparison table for multiple startups.
    """
    verdict_emoji = {
        "Ignore": "🚫",
        "Weak Signal": "⚡",
        "Watch": "👀",
        "Strong Opportunity": "🚀",
    }
    wrapper_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}

    lines = [
        "## 📊 Startup Comparison (Ranked by Score)",
        "",
        "| Rank | Startup | Stage | AI Layer | Score | Wrapper | Verdict |",
        "|:----:|---------|-------|----------|:-----:|:-------:|---------|",
    ]

    for i, a in enumerate(analyses, 1):
        v_emoji = verdict_emoji.get(a.verdict.verdict, "❓")
        w_emoji = wrapper_emoji.get(a.wrapper_risk.risk_level, "⚪")
        lines.append(
            f"| #{i} | **{a.startup}** | {a.stage_estimate} | "
            f"{a.stack_layer.layer} | **{a.scoring.final_score}** | "
            f"{w_emoji} {a.wrapper_risk.risk_level} | {v_emoji} {a.verdict.verdict} |"
        )

    lines += ["", "---", ""]
    return "\n".join(lines)
