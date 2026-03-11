"""
Deterministic evaluators for the VC Analyst pipeline.
These checks compare pipeline outputs against golden dataset ground truth
without using an LLM (fast, cheap, reproducible).
"""

from __future__ import annotations
from dataclasses import dataclass, field

from ..models.schemas import StartupAnalysis


# ─── Result Models ────────────────────────────────────────────────────────────

@dataclass
class DeterministicResult:
    """Outcome of all deterministic checks for one test case."""
    case_id: str
    startup_name: str
    input_preview: str

    # Layer classification
    layer_correct: bool
    expected_layer: str
    actual_layer: str

    # Wrapper risk
    wrapper_correct: bool
    expected_wrapper_risk: str
    actual_wrapper_risk: str

    # Score range
    score_in_range: bool
    expected_score_range: list[int]
    actual_score: int

    # Verdict
    verdict_correct: bool
    expected_verdict_range: list[str]
    actual_verdict: str

    # Pipeline reliability
    pipeline_completed: bool
    error_message: str = ""

    # Computed pass
    overall_pass: bool = field(init=False)

    def __post_init__(self) -> None:
        self.overall_pass = (
            self.pipeline_completed
            and self.layer_correct
            and self.wrapper_correct
            and self.score_in_range
            and self.verdict_correct
        )


@dataclass
class EvalSummary:
    """Aggregated results across all test cases."""
    total_cases: int
    completed: int
    layer_correct: int
    wrapper_correct: int
    score_in_range: int
    verdict_correct: int
    all_pass: int

    # Per-category breakdown
    by_category: dict[str, dict] = field(default_factory=dict)
    by_difficulty: dict[str, dict] = field(default_factory=dict)

    # Computed rates
    completion_rate: float = field(init=False)
    layer_accuracy: float = field(init=False)
    wrapper_accuracy: float = field(init=False)
    score_pass_rate: float = field(init=False)
    verdict_accuracy: float = field(init=False)
    overall_pass_rate: float = field(init=False)

    def __post_init__(self) -> None:
        n = self.completed or 1  # avoid div/0
        self.completion_rate = self.completed / self.total_cases
        self.layer_accuracy = self.layer_correct / n
        self.wrapper_accuracy = self.wrapper_correct / n
        self.score_pass_rate = self.score_in_range / n
        self.verdict_accuracy = self.verdict_correct / n
        self.overall_pass_rate = self.all_pass / n


# ─── Evaluators ───────────────────────────────────────────────────────────────

def eval_layer_classification(
    analysis: StartupAnalysis,
    expected_layer: str,
) -> bool:
    """
    Check if the AI stack layer classification is correct.
    Exact string match against the expected layer.
    """
    return analysis.stack_layer.layer.strip() == expected_layer.strip()


def eval_wrapper_risk(
    analysis: StartupAnalysis,
    expected_risk: str,
) -> bool:
    """
    Check if the wrapper risk level is correct.
    Exact match: LOW / MEDIUM / HIGH.
    """
    return analysis.wrapper_risk.risk_level.upper().strip() == expected_risk.upper().strip()


def eval_score_range(
    analysis: StartupAnalysis,
    expected_range: list[int],
) -> bool:
    """
    Check if the final adjusted score falls within the expected [min, max] range.
    """
    if len(expected_range) != 2:
        return False
    low, high = expected_range
    return low <= analysis.scoring.final_score <= high


def eval_verdict(
    analysis: StartupAnalysis,
    expected_verdicts: list[str],
) -> bool:
    """
    Check if the verdict label is in the list of acceptable verdicts.
    Multiple acceptable verdicts are supported (e.g., ["Watch", "Strong Opportunity"]).
    """
    return analysis.verdict.verdict in expected_verdicts


def eval_no_hallucination(analysis: StartupAnalysis) -> tuple[bool, list[str]]:
    """
    Heuristic checks for obvious hallucinations:
    - Key fields should not be empty strings
    - Scores should be 0 or 1
    - Score total should equal sum of individual criteria
    - Final score = base + adjustments
    """
    issues: list[str] = []

    # Check required string fields
    for field_name, value in [
        ("startup name", analysis.startup),
        ("summary", analysis.summary),
        ("stack layer reason", analysis.stack_layer.reason),
        ("key insight", analysis.verdict.key_insight),
    ]:
        if not value or value.strip() in ("", "unknown", "N/A"):
            issues.append(f"Empty or missing field: {field_name}")

    # Check individual criterion scores are 0 or 1
    e = analysis.evaluation
    for name, crit in [
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
    ]:
        if crit.score not in (0, 1):
            issues.append(f"Criterion {name} has invalid score: {crit.score}")

    # Check total consistency
    computed_total = sum([
        e.market_size.score, e.market_growth.score, e.problem_severity.score,
        e.clear_wedge.score, e.unique_insight.score, e.data_moat.score,
        e.workflow_lockin.score, e.distribution_advantage.score,
        e.network_effects.score, e.platform_potential.score,
        e.competition_intensity.score, e.founder_advantage.score,
    ])
    if e.total != computed_total:
        issues.append(f"Total score mismatch: stored={e.total}, computed={computed_total}")

    # Check final score math
    s = analysis.scoring
    expected_final = s.base_score + s.layer_adjustment + s.wrapper_penalty
    expected_final = max(0, expected_final)
    if s.final_score != expected_final:
        issues.append(
            f"Final score math error: {s.base_score} + {s.layer_adjustment} + "
            f"{s.wrapper_penalty} = {expected_final}, got {s.final_score}"
        )

    return len(issues) == 0, issues


def build_deterministic_result(
    case: dict,
    analysis: StartupAnalysis | None,
    error: str = "",
) -> DeterministicResult:
    """
    Build a DeterministicResult from a golden dataset case and a pipeline output.
    If analysis is None (pipeline failed), all checks fail.
    """
    if analysis is None:
        return DeterministicResult(
            case_id=case["id"],
            startup_name=case.get("input", "")[:40],
            input_preview=case.get("input", "")[:80],
            layer_correct=False,
            expected_layer=case["expected_layer"],
            actual_layer="ERROR",
            wrapper_correct=False,
            expected_wrapper_risk=case["expected_wrapper_risk"],
            actual_wrapper_risk="ERROR",
            score_in_range=False,
            expected_score_range=case["expected_score_range"],
            actual_score=-1,
            verdict_correct=False,
            expected_verdict_range=case["expected_verdict_range"],
            actual_verdict="ERROR",
            pipeline_completed=False,
            error_message=error,
        )

    return DeterministicResult(
        case_id=case["id"],
        startup_name=analysis.startup,
        input_preview=case.get("input", "")[:80],
        layer_correct=eval_layer_classification(analysis, case["expected_layer"]),
        expected_layer=case["expected_layer"],
        actual_layer=analysis.stack_layer.layer,
        wrapper_correct=eval_wrapper_risk(analysis, case["expected_wrapper_risk"]),
        expected_wrapper_risk=case["expected_wrapper_risk"],
        actual_wrapper_risk=analysis.wrapper_risk.risk_level,
        score_in_range=eval_score_range(analysis, case["expected_score_range"]),
        expected_score_range=case["expected_score_range"],
        actual_score=analysis.scoring.final_score,
        verdict_correct=eval_verdict(analysis, case["expected_verdict_range"]),
        expected_verdict_range=case["expected_verdict_range"],
        actual_verdict=analysis.verdict.verdict,
        pipeline_completed=True,
        error_message=error,
    )


def compute_summary(
    results: list[DeterministicResult],
    cases: list[dict],
) -> EvalSummary:
    """Compute aggregate metrics from a list of deterministic results."""
    total = len(results)
    completed = sum(1 for r in results if r.pipeline_completed)

    summary = EvalSummary(
        total_cases=total,
        completed=completed,
        layer_correct=sum(1 for r in results if r.layer_correct),
        wrapper_correct=sum(1 for r in results if r.wrapper_correct),
        score_in_range=sum(1 for r in results if r.score_in_range),
        verdict_correct=sum(1 for r in results if r.verdict_correct),
        all_pass=sum(1 for r in results if r.overall_pass),
    )

    # Per-category breakdown
    case_by_id = {c["id"]: c for c in cases}
    categories: dict[str, list[DeterministicResult]] = {}
    for r in results:
        c = case_by_id.get(r.case_id, {})
        cat = c.get("category", "Unknown")
        categories.setdefault(cat, []).append(r)

    for cat, cat_results in categories.items():
        n = len(cat_results)
        summary.by_category[cat] = {
            "total": n,
            "passed": sum(1 for r in cat_results if r.overall_pass),
            "pass_rate": round(sum(1 for r in cat_results if r.overall_pass) / n, 2),
        }

    # Per-difficulty breakdown
    difficulties: dict[str, list[DeterministicResult]] = {}
    for r in results:
        c = case_by_id.get(r.case_id, {})
        diff = c.get("difficulty", "unknown")
        difficulties.setdefault(diff, []).append(r)

    for diff, diff_results in difficulties.items():
        n = len(diff_results)
        summary.by_difficulty[diff] = {
            "total": n,
            "passed": sum(1 for r in diff_results if r.overall_pass),
            "pass_rate": round(sum(1 for r in diff_results if r.overall_pass) / n, 2),
        }

    return summary
