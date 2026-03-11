"""
LLM-as-Judge for VC Analyst output quality evaluation.
Uses Grok (primary) or Claude Haiku (fallback) to score analysis quality on 1–5 rubrics.
"""

from __future__ import annotations
import json
import re
import logging
from dataclasses import dataclass, field

from ..core.llm_client import LLMClient
from ..models.schemas import StartupAnalysis

logger = logging.getLogger(__name__)


# ─── Judge Result ─────────────────────────────────────────────────────────────

@dataclass
class JudgeScore:
    """A single judge evaluation with score and reasoning."""
    dimension: str
    score: float          # 1.0–5.0
    reasoning: str
    passed: bool = field(init=False)

    def __post_init__(self) -> None:
        self.passed = self.score >= 3.0  # 3+ = acceptable quality


@dataclass
class QualityReport:
    """Aggregated quality evaluation for one startup analysis."""
    startup_name: str
    rationale_quality: JudgeScore
    insight_quality: JudgeScore
    tam_quality: JudgeScore
    memo_quality: JudgeScore | None        # None if memo was not generated
    average_score: float = field(init=False)
    overall_pass: bool = field(init=False)

    def __post_init__(self) -> None:
        scores = [
            self.rationale_quality.score,
            self.insight_quality.score,
            self.tam_quality.score,
        ]
        if self.memo_quality:
            scores.append(self.memo_quality.score)
        self.average_score = round(sum(scores) / len(scores), 2)
        self.overall_pass = all(
            s.passed for s in [self.rationale_quality, self.insight_quality, self.tam_quality]
            + ([self.memo_quality] if self.memo_quality else [])
        )


# ─── Judge Prompts ────────────────────────────────────────────────────────────

_RATIONALE_JUDGE_PROMPT = """You are a senior venture capital analyst evaluating the quality of an AI startup analysis.

Score the quality of the 12-point evaluation criterion rationales on a 1-5 scale:

5 = Excellent: All rationales are specific, evidence-based, and directly tied to observable startup signals. Scores are rigorously justified.
4 = Good: Most rationales are specific and well-justified. Minor instances of generic reasoning.
3 = Acceptable: Rationales are present but mix specific observations with generic statements. Scores are defensible.
2 = Poor: Many rationales are vague, generic, or inconsistent with the stated score. Multiple unsupported claims.
1 = Failing: Rationales are missing, hallucinated, contradictory, or show no engagement with the startup's actual characteristics.

Return ONLY a JSON object: {"score": <1-5>, "reasoning": "<2-3 sentences explaining the score>"}"""

_INSIGHT_JUDGE_PROMPT = """You are a venture capital partner evaluating the quality of an investment key insight.

Score the Key Insight on a 1-5 scale:

5 = Excellent: Investor-grade, specific, non-obvious, directly tied to the final score and verdict. Captures the single most important signal.
4 = Good: Specific and relevant. Correctly identifies the primary driver of the verdict. Slightly formulaic but grounded.
3 = Acceptable: Makes a valid point about the startup but is somewhat generic or misses the most critical signal.
2 = Poor: Vague, generic ("promising startup with good market potential"), or inconsistent with the verdict.
1 = Failing: Irrelevant, hallucinated, or contradicts the analysis.

Return ONLY a JSON object: {"score": <1-5>, "reasoning": "<2-3 sentences explaining the score>"}"""

_TAM_JUDGE_PROMPT = """You are a venture capital analyst evaluating market sizing quality.

Score the TAM/SAM estimate on a 1-5 scale:

5 = Excellent: TAM and SAM figures are specific, defensible, and accompanied by clear reasoning. Methodology is sound (bottom-up or well-reasoned top-down).
4 = Good: Reasonable estimates with adequate justification. Minor imprecision in methodology.
3 = Acceptable: Plausible figures with basic reasoning. May use round numbers without full justification.
2 = Poor: Vague ("large market", "multi-billion"), inconsistent TAM/SAM relationship, or weak reasoning.
1 = Failing: Missing, obviously wrong (e.g., $1T TAM for a niche tool), or no reasoning provided.

Return ONLY a JSON object: {"score": <1-5>, "reasoning": "<2-3 sentences explaining the score>"}"""

_MEMO_JUDGE_PROMPT = """You are a venture capital partner evaluating the quality of an investment memo.

Score the Investment Memo on a 1-5 scale:

5 = Excellent: All 6 sections present (Thesis, Market, Product, Moat, Risks, Verdict). 150-250 words. Investor-grade prose. Specific, actionable, and consistent with the full analysis.
4 = Good: All key sections present, well-written, specific. Minor length or structure issues.
3 = Acceptable: Most sections present. Some generic language. Consistent with the analysis overall.
2 = Poor: Missing major sections, overly generic, or inconsistent with the verdict/scores.
1 = Failing: Does not follow format, hallucinated facts, or contradicts the analysis.

Return ONLY a JSON object: {"score": <1-5>, "reasoning": "<2-3 sentences explaining the score>"}"""


# ─── Judge Class ──────────────────────────────────────────────────────────────

class LLMJudge:
    """
    Evaluates the quality of VC Analyst outputs using LLM-as-Judge.
    Uses Grok (via LLMClient) for judgements.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()

    def evaluate(self, analysis: StartupAnalysis) -> QualityReport:
        """Run all quality evaluations for a single StartupAnalysis."""
        rationale_score = self._eval_rationale_quality(analysis)
        insight_score = self._eval_insight_quality(analysis)
        tam_score = self._eval_tam_quality(analysis)
        memo_score = (
            self._eval_memo_quality(analysis)
            if analysis.nuance and analysis.nuance.investment_memo
            else None
        )

        return QualityReport(
            startup_name=analysis.startup,
            rationale_quality=rationale_score,
            insight_quality=insight_score,
            tam_quality=tam_score,
            memo_quality=memo_score,
        )

    # ── Individual Evaluators ─────────────────────────────────────────────────

    def _eval_rationale_quality(self, analysis: StartupAnalysis) -> JudgeScore:
        e = analysis.evaluation
        rationales_block = "\n".join([
            f"- Market Size ({e.market_size.score}/1): {e.market_size.rationale}",
            f"- Market Growth ({e.market_growth.score}/1): {e.market_growth.rationale}",
            f"- Problem Severity ({e.problem_severity.score}/1): {e.problem_severity.rationale}",
            f"- Clear Wedge ({e.clear_wedge.score}/1): {e.clear_wedge.rationale}",
            f"- Unique Insight ({e.unique_insight.score}/1): {e.unique_insight.rationale}",
            f"- Data Moat ({e.data_moat.score}/1): {e.data_moat.rationale}",
            f"- Workflow Lock-in ({e.workflow_lockin.score}/1): {e.workflow_lockin.rationale}",
            f"- Distribution Advantage ({e.distribution_advantage.score}/1): {e.distribution_advantage.rationale}",
            f"- Network Effects ({e.network_effects.score}/1): {e.network_effects.rationale}",
            f"- Platform Potential ({e.platform_potential.score}/1): {e.platform_potential.rationale}",
            f"- Competition Intensity ({e.competition_intensity.score}/1): {e.competition_intensity.rationale}",
            f"- Founder Advantage ({e.founder_advantage.score}/1): {e.founder_advantage.rationale}",
        ])

        user_msg = f"""Startup: {analysis.startup}
Summary: {analysis.summary}

12-Point Evaluation Rationales:
{rationales_block}

Score the quality of these rationales."""

        return self._call_judge("rationale_quality", _RATIONALE_JUDGE_PROMPT, user_msg)

    def _eval_insight_quality(self, analysis: StartupAnalysis) -> JudgeScore:
        user_msg = f"""Startup: {analysis.startup}
Summary: {analysis.summary}
Final Score: {analysis.scoring.final_score}
Verdict: {analysis.verdict.verdict}

Key Insight to evaluate:
"{analysis.verdict.key_insight}"

Score the quality of this Key Insight."""

        return self._call_judge("insight_quality", _INSIGHT_JUDGE_PROMPT, user_msg)

    def _eval_tam_quality(self, analysis: StartupAnalysis) -> JudgeScore:
        if not analysis.nuance:
            return JudgeScore(
                dimension="tam_quality",
                score=1.0,
                reasoning="No nuance report available. TAM could not be evaluated.",
            )

        tam = analysis.nuance.tam_estimate
        user_msg = f"""Startup: {analysis.startup}
Market: {analysis.summary}

TAM Estimate to evaluate:
- TAM: {tam.tam}
- SAM: {tam.sam}
- Reasoning: {tam.reasoning}

Score the quality of this market sizing."""

        return self._call_judge("tam_quality", _TAM_JUDGE_PROMPT, user_msg)

    def _eval_memo_quality(self, analysis: StartupAnalysis) -> JudgeScore:
        memo = analysis.nuance.investment_memo if analysis.nuance else None
        if not memo:
            return JudgeScore(
                dimension="memo_quality",
                score=1.0,
                reasoning="No investment memo generated.",
            )

        user_msg = f"""Startup: {analysis.startup}
Verdict: {analysis.verdict.verdict}
Final Score: {analysis.scoring.final_score}

Investment Memo to evaluate:
{memo}

Score the quality of this investment memo."""

        return self._call_judge("memo_quality", _MEMO_JUDGE_PROMPT, user_msg)

    # ── LLM Call Helper ───────────────────────────────────────────────────────

    def _call_judge(
        self,
        dimension: str,
        system_prompt: str,
        user_message: str,
    ) -> JudgeScore:
        """Call the LLM judge and parse the response."""
        try:
            raw = self._llm.call(system_prompt, user_message, max_tokens=300)
            data = self._parse_judge_json(raw)
            score = float(data.get("score", 1.0))
            score = max(1.0, min(5.0, score))
            reasoning = str(data.get("reasoning", "No reasoning provided."))
        except Exception as e:
            logger.error(f"Judge call failed for {dimension}: {e}")
            score = 1.0
            reasoning = f"Judge evaluation failed: {e}"

        return JudgeScore(
            dimension=dimension,
            score=score,
            reasoning=reasoning,
        )

    def _parse_judge_json(self, text: str) -> dict:
        """Parse JSON from judge response, handling markdown fences."""
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        return json.loads(text)
