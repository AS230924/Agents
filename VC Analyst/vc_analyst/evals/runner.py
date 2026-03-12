"""
VC Analyst — Evaluation Runner
Orchestrates the full evaluation pipeline: loads golden dataset, runs each
test case through the pipeline, applies deterministic + LLM-as-Judge checks,
and generates a structured report.
"""

from __future__ import annotations
import json
import time
import logging
import traceback
from pathlib import Path
from dataclasses import dataclass, field

from ..core.pipeline import analyze_startup
from ..core.llm_client import LLMClient
from ..core.tracer import get_tracer
from ..models.schemas import StartupAnalysis
from .evaluators import (
    DeterministicResult,
    EvalSummary,
    build_deterministic_result,
    compute_summary,
    eval_no_hallucination,
)
from .judge import LLMJudge, QualityReport

logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"

# Delay between cases to avoid API rate limits
RATE_LIMIT_DELAY_SECONDS = 1.5


# ─── Eval Case Result ─────────────────────────────────────────────────────────

@dataclass
class CaseResult:
    """Complete evaluation result for one golden dataset case."""
    case_id: str
    category: str
    difficulty: str
    test_type: str
    analysis: StartupAnalysis | None
    deterministic: DeterministicResult
    hallucination_issues: list[str]
    quality: QualityReport | None   # None if pipeline failed or quality eval skipped
    duration_seconds: float


# ─── Runner ───────────────────────────────────────────────────────────────────

def load_dataset(path: Path = GOLDEN_DATASET_PATH) -> list[dict]:
    """Load the golden dataset JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_evals(
    run_quality: bool = True,
    filter_ids: list[str] | None = None,
    filter_category: str | None = None,
    filter_difficulty: str | None = None,
    max_cases: int | None = None,
    verbose: bool = False,
    dataset_path: Path = GOLDEN_DATASET_PATH,
) -> tuple[list[CaseResult], EvalSummary]:
    """
    Run the full evaluation suite.

    Args:
        run_quality: Whether to run LLM-as-Judge quality evaluations (slower, costs tokens).
        filter_ids: If set, only run cases with these IDs.
        filter_category: If set, only run cases in this category.
        filter_difficulty: If set, only run cases of this difficulty.
        max_cases: Cap the number of cases to run.
        verbose: Print progress to stdout.
        dataset_path: Path to golden dataset JSON.

    Returns:
        (case_results, summary) tuple.
    """
    cases = load_dataset(dataset_path)

    # Apply filters
    if filter_ids:
        cases = [c for c in cases if c["id"] in filter_ids]
    if filter_category:
        cases = [c for c in cases if c.get("category") == filter_category]
    if filter_difficulty:
        cases = [c for c in cases if c.get("difficulty") == filter_difficulty]
    if max_cases:
        cases = cases[:max_cases]

    if not cases:
        raise ValueError("No cases match the specified filters.")

    client = LLMClient()
    judge = LLMJudge(client) if run_quality else None

    case_results: list[CaseResult] = []

    _log(f"\n{'='*60}", verbose)
    _log(f"  VC ANALYST EVALUATION — {len(cases)} cases", verbose)
    _log(f"{'='*60}\n", verbose)

    tracer = get_tracer()

    for i, case in enumerate(cases):
        case_id = case["id"]
        _log(f"[{i+1}/{len(cases)}] Running {case_id} ({case['category']}, {case['difficulty']})…", verbose)

        start = time.time()
        analysis: StartupAnalysis | None = None
        error_msg = ""

        with tracer.start_as_current_span("eval_case") as span:
            span.set_attribute("case.id", case_id)
            span.set_attribute("case.category", case.get("category", ""))
            span.set_attribute("case.difficulty", case.get("difficulty", ""))
            span.set_attribute("case.test_type", case.get("test_type", ""))
            span.set_attribute("case.input_type", case.get("input_type", ""))

            # Run pipeline
            try:
                analysis = analyze_startup(
                    case["input"],
                    llm_client=client,
                    progress_callback=lambda msg: _log(f"       {msg}", verbose),
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Pipeline failed for {case_id}: {e}")
                span.set_attribute("pipeline.error", error_msg)
                if verbose:
                    traceback.print_exc()

            duration = round(time.time() - start, 2)

            # Deterministic evaluation
            det_result = build_deterministic_result(case, analysis, error=error_msg)

            # Hallucination check
            hallucination_ok, hal_issues = (
                eval_no_hallucination(analysis) if analysis else (False, ["Pipeline failed"])
            )

            # Quality evaluation (LLM-as-Judge)
            quality: QualityReport | None = None
            if run_quality and analysis and judge:
                try:
                    quality = judge.evaluate(analysis)
                except Exception as e:
                    logger.error(f"Quality eval failed for {case_id}: {e}")

            # Record eval results as span attributes
            span.set_attribute("eval.layer_correct", det_result.layer_correct)
            span.set_attribute("eval.wrapper_correct", det_result.wrapper_correct)
            span.set_attribute("eval.score_in_range", det_result.score_in_range)
            span.set_attribute("eval.verdict_correct", det_result.verdict_correct)
            span.set_attribute("eval.hallucination_pass", hallucination_ok)
            span.set_attribute("eval.overall_pass", det_result.overall_pass)
            span.set_attribute("eval.duration_seconds", duration)
            if analysis:
                span.set_attribute("result.final_score", analysis.scoring.final_score)
                span.set_attribute("result.verdict", analysis.verdict.verdict)
                span.set_attribute("result.layer", analysis.stack_layer.layer)
            if quality:
                span.set_attribute("eval.quality_score", quality.average_score)
                span.set_attribute("eval.quality_pass", quality.overall_pass)

        # Log quick result
        status = "✅" if det_result.overall_pass else "❌"
        _log(
            f"       {status} Layer={det_result.layer_correct} | "
            f"Wrapper={det_result.wrapper_correct} | "
            f"Score={det_result.score_in_range} ({det_result.actual_score}) | "
            f"Verdict={det_result.verdict_correct} | "
            f"Time={duration}s",
            verbose,
        )
        if quality:
            _log(
                f"       🤖 Quality avg={quality.average_score:.1f}/5 "
                f"(Rationale={quality.rationale_quality.score:.1f} | "
                f"Insight={quality.insight_quality.score:.1f} | "
                f"TAM={quality.tam_quality.score:.1f}"
                + (f" | Memo={quality.memo_quality.score:.1f}" if quality.memo_quality else "")
                + ")",
                verbose,
            )
        if hal_issues:
            _log(f"       ⚠️  Hallucination issues: {hal_issues}", verbose)

        case_results.append(CaseResult(
            case_id=case_id,
            category=case.get("category", "Unknown"),
            difficulty=case.get("difficulty", "unknown"),
            test_type=case.get("test_type", "unknown"),
            analysis=analysis,
            deterministic=det_result,
            hallucination_issues=hal_issues,
            quality=quality,
            duration_seconds=duration,
        ))

        # Rate limit between cases
        if i < len(cases) - 1:
            time.sleep(RATE_LIMIT_DELAY_SECONDS)

    # Compute summary
    det_results = [r.deterministic for r in case_results]
    summary = compute_summary(det_results, cases)

    return case_results, summary


# ─── Report Formatter ─────────────────────────────────────────────────────────

def format_report(
    case_results: list[CaseResult],
    summary: EvalSummary,
    include_quality: bool = True,
) -> str:
    """
    Format the full evaluation report as a rich text string.
    """
    lines: list[str] = []

    _h = lambda t: f"\n{'─'*60}\n{t}\n{'─'*60}"

    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║         VC ANALYST — EVALUATION REPORT                  ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append("")

    # ── Deterministic Summary ─────────────────────────────────────────────────
    lines.append(_h("📊 DETERMINISTIC ACCURACY"))
    lines.append(f"  Pipeline Completion:      {summary.completed}/{summary.total_cases} ({summary.completion_rate:.0%})")
    lines.append(f"  Layer Classification:     {summary.layer_correct}/{summary.completed} ({summary.layer_accuracy:.0%})")
    lines.append(f"  Wrapper Risk Detection:   {summary.wrapper_correct}/{summary.completed} ({summary.wrapper_accuracy:.0%})")
    lines.append(f"  Score Range Pass Rate:    {summary.score_in_range}/{summary.completed} ({summary.score_pass_rate:.0%})")
    lines.append(f"  Verdict Match Rate:       {summary.verdict_correct}/{summary.completed} ({summary.verdict_accuracy:.0%})")
    lines.append(f"  ─────────────────────────────────────")
    lines.append(f"  Overall Pass (all checks): {summary.all_pass}/{summary.completed} ({summary.overall_pass_rate:.0%})")

    # ── Quality Summary ───────────────────────────────────────────────────────
    quality_results = [r.quality for r in case_results if r.quality is not None]
    if include_quality and quality_results:
        lines.append(_h("🤖 LLM-AS-JUDGE QUALITY SCORES (avg 1–5)"))

        avg = lambda attr: round(
            sum(getattr(q, attr).score for q in quality_results) / len(quality_results), 2
        )
        memo_results = [r.quality for r in case_results if r.quality and r.quality.memo_quality]
        avg_memo = (
            round(sum(q.memo_quality.score for q in memo_results) / len(memo_results), 2)
            if memo_results else None
        )

        lines.append(f"  Criterion Rationale:  {avg('rationale_quality')}/5")
        lines.append(f"  Key Insight:          {avg('insight_quality')}/5")
        lines.append(f"  TAM Estimate:         {avg('tam_quality')}/5")
        if avg_memo:
            lines.append(f"  Investment Memo:      {avg_memo}/5  (Watch/Strong Opportunity only)")
        avg_all = round(
            sum(q.average_score for q in quality_results) / len(quality_results), 2
        )
        lines.append(f"  ─────────────────────────────────────")
        lines.append(f"  Average Quality Score: {avg_all}/5")

    # ── Per-Category Breakdown ────────────────────────────────────────────────
    if summary.by_category:
        lines.append(_h("📁 BREAKDOWN BY CATEGORY"))
        for cat, stats in sorted(summary.by_category.items()):
            bar = "█" * int(stats["pass_rate"] * 10) + "░" * (10 - int(stats["pass_rate"] * 10))
            lines.append(
                f"  {cat:<35} {stats['passed']}/{stats['total']} [{bar}] {stats['pass_rate']:.0%}"
            )

    # ── Per-Difficulty Breakdown ──────────────────────────────────────────────
    if summary.by_difficulty:
        lines.append(_h("🎯 BREAKDOWN BY DIFFICULTY"))
        for diff, stats in sorted(summary.by_difficulty.items()):
            lines.append(
                f"  {diff:<10} {stats['passed']}/{stats['total']} ({stats['pass_rate']:.0%})"
            )

    # ── Per-Case Table ────────────────────────────────────────────────────────
    lines.append(_h("📋 CASE-BY-CASE RESULTS"))
    header = (
        f"  {'ID':<14} {'Startup':<20} {'Layer':^5} {'Wrap':^5} "
        f"{'Score':^6} {'Verdict':^7} {'Quality':^8} {'Time':>6}"
    )
    lines.append(header)
    lines.append("  " + "─" * 74)

    for r in case_results:
        d = r.deterministic
        q_avg = f"{r.quality.average_score:.1f}" if r.quality else "  —  "
        status = "✅" if d.overall_pass else "❌"
        l_icon = "✓" if d.layer_correct else "✗"
        w_icon = "✓" if d.wrapper_correct else "✗"
        s_icon = "✓" if d.score_in_range else "✗"
        v_icon = "✓" if d.verdict_correct else "✗"

        lines.append(
            f"  {status} {d.case_id:<12} {d.startup_name[:19]:<19} "
            f"{l_icon:^5} {w_icon:^5} "
            f"{s_icon}{d.actual_score:>2}  {v_icon:^7} "
            f"{q_avg:^8} {r.duration_seconds:>5.1f}s"
        )

    # ── Failures Detail ───────────────────────────────────────────────────────
    failures = [r for r in case_results if not r.deterministic.overall_pass]
    if failures:
        lines.append(_h(f"⚠️  FAILURES ({len(failures)} cases)"))
        for r in failures:
            d = r.deterministic
            lines.append(f"\n  Case: {d.case_id}  |  Startup: {d.startup_name}")
            if not d.pipeline_completed:
                lines.append(f"    ❌ Pipeline failed: {d.error_message}")
            if not d.layer_correct:
                lines.append(f"    ❌ Layer: expected '{d.expected_layer}', got '{d.actual_layer}'")
            if not d.wrapper_correct:
                lines.append(f"    ❌ Wrapper: expected '{d.expected_wrapper_risk}', got '{d.actual_wrapper_risk}'")
            if not d.score_in_range:
                lines.append(
                    f"    ❌ Score: expected {d.expected_score_range[0]}–{d.expected_score_range[1]}, "
                    f"got {d.actual_score}"
                )
            if not d.verdict_correct:
                lines.append(
                    f"    ❌ Verdict: expected one of {d.expected_verdict_range}, "
                    f"got '{d.actual_verdict}'"
                )
            if r.hallucination_issues:
                for issue in r.hallucination_issues:
                    lines.append(f"    ⚠️  Hallucination: {issue}")

    # ── Hallucination Summary ─────────────────────────────────────────────────
    total_hal_issues = sum(len(r.hallucination_issues) for r in case_results)
    if total_hal_issues:
        lines.append(_h(f"🔍 HALLUCINATION CHECK ({total_hal_issues} issues found)"))
        for r in case_results:
            if r.hallucination_issues:
                lines.append(f"  {r.case_id}:")
                for issue in r.hallucination_issues:
                    lines.append(f"    - {issue}")
    else:
        lines.append(f"\n  ✅ No hallucination issues detected across all cases.")

    # ── Timing Summary ────────────────────────────────────────────────────────
    times = [r.duration_seconds for r in case_results]
    if times:
        lines.append(_h("⏱️  TIMING"))
        lines.append(f"  Total wall time:  {sum(times):.1f}s")
        lines.append(f"  Mean per case:    {sum(times)/len(times):.1f}s")
        lines.append(f"  Fastest case:     {min(times):.1f}s")
        lines.append(f"  Slowest case:     {max(times):.1f}s")

    lines.append("\n" + "═" * 62)

    return "\n".join(lines)


def save_report(report_text: str, path: str = "eval_report.txt") -> None:
    """Save the formatted report to a text file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text)
    logger.info(f"Report saved to {path}")


def _log(msg: str, verbose: bool) -> None:
    """Conditional print."""
    if verbose:
        print(msg)
