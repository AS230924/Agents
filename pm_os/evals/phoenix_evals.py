"""
Phoenix-powered evaluation suite for PM OS agents.

Three eval layers:
  1. Intent classification accuracy    — deterministic (golden dataset)
  2. Agent output quality (LLM-judge)  — llm_classify with per-agent rubrics
  3. Trace-based cost/latency analysis — reads from Phoenix trace store

Usage:
    # Run all evals
    python -m pm_os.evals.phoenix_evals

    # Run a specific eval
    python -m pm_os.evals.phoenix_evals --eval intent
    python -m pm_os.evals.phoenix_evals --eval quality
    python -m pm_os.evals.phoenix_evals --eval traces

Prerequisites:
    pip install arize-phoenix arize-phoenix-evals
    Phoenix must be running (init_phoenix() or `phoenix serve`).
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
GOLDEN_PATH = Path(__file__).resolve().parent.parent / "golden_dataset.json"

# ------------------------------------------------------------------
# 1. INTENT CLASSIFICATION EVAL (deterministic — no LLM judge cost)
# ------------------------------------------------------------------

def eval_intent_classification(
    dataset_path: str | Path | None = None,
    sample_size: int | None = None,
) -> dict:
    """
    Run the golden dataset through the classifier and log results to Phoenix.

    This wraps the existing test_router logic but stores results as a
    Phoenix Dataset + Experiment so you can compare across runs.
    """
    path = Path(dataset_path) if dataset_path else GOLDEN_PATH
    with open(path) as f:
        dataset = json.load(f)

    if sample_size:
        dataset = dataset[:sample_size]

    # Build a dataframe for Phoenix
    rows = []
    for case in dataset:
        rows.append({
            "id": case["id"],
            "test_type": case.get("test_type", "unknown"),
            "category": case.get("category", "unknown"),
            "difficulty": case.get("difficulty", "unknown"),
            "user_query": case["user_query"],
            "expected_intent": case["expected_intent"],
            "ecommerce_context": case.get("ecommerce_context", "general"),
        })

    df = pd.DataFrame(rows)

    # Run classifier on each row
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from pm_os.core.intent_classifier import classify

    results = []
    import time

    for _, row in df.iterrows():
        result = classify({"query": row["user_query"]})
        results.append({
            "predicted_intent": result["intent"],
            "confidence": result["confidence"],
            "reasoning": result["reasoning"],
            "correct": result["intent"] == row["expected_intent"],
        })
        time.sleep(0.3)  # rate limit

    results_df = pd.DataFrame(results)
    df = pd.concat([df, results_df], axis=1)

    # Summary stats
    accuracy = df["correct"].mean() * 100
    by_type = df.groupby("test_type")["correct"].mean() * 100
    by_difficulty = df.groupby("difficulty")["correct"].mean() * 100

    print("\n" + "=" * 60)
    print("PHOENIX INTENT CLASSIFICATION EVAL")
    print("=" * 60)
    print(f"\nOverall accuracy: {accuracy:.1f}% ({df['correct'].sum()}/{len(df)})")
    print("\nBy test type:")
    for ttype, acc in by_type.items():
        print(f"  {ttype:20s} {acc:.1f}%")
    print("\nBy difficulty:")
    for diff, acc in by_difficulty.items():
        print(f"  {diff:20s} {acc:.1f}%")

    # Log to Phoenix as a dataset if available
    _try_log_dataset(df, "intent_classification_eval")

    failures = df[~df["correct"]]
    if len(failures) > 0:
        print(f"\nFAILURES ({len(failures)}):")
        for _, f in failures.head(20).iterrows():
            print(f"  {f['id']}: expected={f['expected_intent']}, "
                  f"got={f['predicted_intent']} ({f['confidence']:.0%})")
            print(f"    Query: {f['user_query'][:80]}...")
            print(f"    Reason: {f['reasoning'][:100]}")
            print()

    return {
        "accuracy": accuracy,
        "total": len(df),
        "correct": int(df["correct"].sum()),
        "by_type": by_type.to_dict(),
        "by_difficulty": by_difficulty.to_dict(),
    }


# ------------------------------------------------------------------
# 2. AGENT OUTPUT QUALITY EVAL (LLM-as-judge via Phoenix llm_classify)
# ------------------------------------------------------------------

# Per-agent evaluation rubrics
AGENT_EVAL_TEMPLATES = {
    "Framer": {
        "template": """You are evaluating the output of an AI problem-diagnosis agent
for an e-commerce product manager.

The user asked: {query}

The agent produced this output:
{agent_output}

Evaluate the quality of the diagnosis. Consider:
- Does it identify root causes, not just symptoms?
- Does it use structured analysis (5 Whys, causal chains)?
- Are hypotheses specific and testable?
- Does it avoid jumping to solutions prematurely?

Classify the quality as one of:
- strong_diagnosis: Clear root cause analysis with testable hypotheses
- weak_diagnosis: Surface-level analysis, vague hypotheses
- missing_hypothesis: Fails to identify plausible root causes""",
        "rails": ["strong_diagnosis", "weak_diagnosis", "missing_hypothesis"],
    },
    "Strategist": {
        "template": """You are evaluating the output of an AI strategy/decision agent
for an e-commerce product manager.

The user asked: {query}

The agent produced this output:
{agent_output}

Evaluate the quality of the strategic analysis. Consider:
- Does it use a clear decision framework (RICE, cost-benefit, weighted scoring)?
- Are trade-offs explicitly stated?
- Is the recommendation backed by evidence?
- Are risks identified with mitigations?

Classify the quality as one of:
- sound_framework: Clear framework, explicit trade-offs, backed recommendation
- shallow_analysis: Missing framework or vague trade-offs
- wrong_framework: Inappropriate framework for the problem type""",
        "rails": ["sound_framework", "shallow_analysis", "wrong_framework"],
    },
    "Executor": {
        "template": """You are evaluating the output of an AI execution-planning agent
for an e-commerce product manager.

The user asked: {query}

The agent produced this output:
{agent_output}

Evaluate the quality of the execution plan. Consider:
- Is the MVP scope clearly defined (in/out)?
- Are phases realistic with clear deliverables?
- Are dependencies identified?
- Is the launch checklist comprehensive?

Classify the quality as one of:
- complete_plan: Clear scope, realistic phases, identified dependencies
- missing_fields: Key sections missing (no scope, no phases, no checklist)
- vague_scope: Scope defined but too vague to be actionable""",
        "rails": ["complete_plan", "missing_fields", "vague_scope"],
    },
    "Aligner": {
        "template": """You are evaluating the output of an AI stakeholder-alignment agent
for an e-commerce product manager.

The user asked: {query}

The agent produced this output:
{agent_output}

Evaluate the quality of the alignment plan. Consider:
- Does it identify specific stakeholders and their concerns?
- Are talking points tailored to each audience?
- Does it anticipate objections with responses?
- Is the ask/decision framed clearly?

Classify the quality as one of:
- strong_alignment: Specific stakeholders, tailored points, objection handling
- generic_points: Talking points are generic, not stakeholder-specific
- missing_stakeholders: Fails to identify key stakeholders""",
        "rails": ["strong_alignment", "generic_points", "missing_stakeholders"],
    },
    "Narrator": {
        "template": """You are evaluating the output of an AI executive-summary agent
for an e-commerce product manager.

The user asked: {query}

The agent produced this output:
{agent_output}

Evaluate the quality of the executive summary. Consider:
- Is there a clear TLDR?
- Does it follow What/Why/Ask structure?
- Is supporting data referenced?
- Is it concise enough for leadership?

Classify the quality as one of:
- clear_narrative: Strong TLDR, structured, concise, data-backed
- too_verbose: Good content but too long for executive audience
- missing_ask: No clear ask or decision request for leadership""",
        "rails": ["clear_narrative", "too_verbose", "missing_ask"],
    },
    "Scout": {
        "template": """You are evaluating the output of an AI competitive-intelligence agent
for an e-commerce product manager.

The user asked: {query}

The agent produced this output:
{agent_output}

Evaluate the quality of the competitive analysis. Consider:
- Are specific competitors identified?
- Is the analysis based on observable signals, not speculation?
- Are strategic implications drawn from the intel?
- Does it include actionable recommendations?

Classify the quality as one of:
- actionable_intel: Specific competitors, evidence-based, strategic implications
- surface_level: Names competitors but no depth or strategic insight
- speculative: Claims without evidence or observable signals""",
        "rails": ["actionable_intel", "surface_level", "speculative"],
    },
}


def eval_agent_quality(
    agent_outputs_path: str | Path | None = None,
    judge_model: str = "openai/gpt-4o-mini",
) -> dict:
    """
    Run LLM-as-judge evaluation on agent outputs using Phoenix llm_classify.

    Args:
        agent_outputs_path: Path to JSONL file with agent outputs.
            Each line: {"agent": "Framer", "query": "...", "agent_output": "..."}
            If None, attempts to export recent traces from Phoenix.
        judge_model: Model to use as judge (default: gpt-4o-mini for low cost).

    Returns:
        Dict with per-agent quality scores.
    """
    try:
        from phoenix.evals import OpenAIModel, llm_classify
    except ImportError:
        print("ERROR: arize-phoenix-evals not installed.")
        print("Run: pip install arize-phoenix-evals")
        return {}

    # Load agent outputs
    if agent_outputs_path:
        df = _load_agent_outputs(agent_outputs_path)
    else:
        df = _export_traces_as_eval_df()
        if df is None or df.empty:
            print("No agent outputs found. Either provide --outputs or run the app first.")
            return {}

    # Set up the judge model
    judge = OpenAIModel(model=judge_model)

    results = {}

    for agent_name, template_config in AGENT_EVAL_TEMPLATES.items():
        agent_df = df[df["agent"] == agent_name]
        if agent_df.empty:
            continue

        print(f"\nEvaluating {agent_name} ({len(agent_df)} outputs)...")

        eval_result = llm_classify(
            dataframe=agent_df,
            model=judge,
            template=template_config["template"],
            rails=template_config["rails"],
            provide_explanation=True,
            concurrency=5,
        )

        # Merge results
        agent_df = agent_df.copy()
        agent_df["label"] = eval_result["label"]
        agent_df["explanation"] = eval_result["explanation"]

        # Summary
        label_counts = agent_df["label"].value_counts()
        total = len(agent_df)
        top_label = label_counts.index[0] if len(label_counts) > 0 else "N/A"
        top_pct = label_counts.iloc[0] / total * 100 if total > 0 else 0

        print(f"  {agent_name} results:")
        for label, count in label_counts.items():
            pct = count / total * 100
            print(f"    {label}: {count}/{total} ({pct:.1f}%)")

        results[agent_name] = {
            "total": total,
            "distribution": label_counts.to_dict(),
            "top_label": top_label,
            "top_pct": top_pct,
        }

        # Log to Phoenix
        _try_log_dataset(agent_df, f"{agent_name.lower()}_quality_eval")

    return results


# ------------------------------------------------------------------
# 3. TRACE ANALYSIS (cost, latency, fallback rates from Phoenix)
# ------------------------------------------------------------------

def eval_traces() -> dict:
    """
    Analyze traces stored in Phoenix for cost, latency, and fallback patterns.

    Requires Phoenix to be running with traces already collected.
    """
    try:
        import phoenix as px

        client = px.Client()
    except Exception as e:
        print(f"Cannot connect to Phoenix: {e}")
        print("Make sure Phoenix is running (init_phoenix() or `phoenix serve`)")
        return {}

    try:
        # Get spans from the default project
        spans_df = client.get_spans_dataframe(
            project_name=os.environ.get("PHOENIX_PROJECT_NAME", "pm-os"),
        )
    except Exception as e:
        print(f"Failed to fetch spans: {e}")
        return {}

    if spans_df is None or spans_df.empty:
        print("No traces found. Run the app first to generate traces.")
        return {}

    print("\n" + "=" * 60)
    print("PHOENIX TRACE ANALYSIS")
    print("=" * 60)

    print(f"\nTotal spans: {len(spans_df)}")

    # Latency stats
    if "latency_ms" in spans_df.columns:
        print(f"\nLatency (ms):")
        print(f"  Mean:   {spans_df['latency_ms'].mean():.0f}")
        print(f"  Median: {spans_df['latency_ms'].median():.0f}")
        print(f"  P95:    {spans_df['latency_ms'].quantile(0.95):.0f}")
        print(f"  P99:    {spans_df['latency_ms'].quantile(0.99):.0f}")

    # Token usage
    for col in ["llm.token_count.prompt", "llm.token_count.completion", "llm.token_count.total"]:
        if col in spans_df.columns:
            label = col.split(".")[-1]
            total = spans_df[col].sum()
            print(f"\n  Total {label} tokens: {total:,.0f}")

    # Fallback detection (look for pm_os.fallback attribute)
    if "attributes.pm_os.fallback" in spans_df.columns:
        fallbacks = spans_df["attributes.pm_os.fallback"].sum()
        total_calls = len(spans_df)
        print(f"\n  Fallback events: {fallbacks}/{total_calls} "
              f"({fallbacks / total_calls * 100:.1f}%)")

    # Per-caller breakdown
    if "attributes.pm_os.caller" in spans_df.columns:
        print("\nBy caller:")
        by_caller = spans_df.groupby("attributes.pm_os.caller").agg(
            count=("name", "size"),
        )
        for caller, row in by_caller.iterrows():
            print(f"  {caller}: {row['count']} calls")

    return {"total_spans": len(spans_df)}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _load_agent_outputs(path: str | Path) -> pd.DataFrame:
    """Load agent outputs from a JSONL file."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)


def _export_traces_as_eval_df() -> pd.DataFrame | None:
    """Try to export recent agent traces from Phoenix as a DataFrame."""
    try:
        import phoenix as px

        client = px.Client()
        spans_df = client.get_spans_dataframe(
            project_name=os.environ.get("PHOENIX_PROJECT_NAME", "pm-os"),
        )

        if spans_df is None or spans_df.empty:
            return None

        # Filter for agent LLM calls (those with pm_os.caller attribute)
        if "attributes.pm_os.caller" not in spans_df.columns:
            return None

        agent_spans = spans_df[
            spans_df["attributes.pm_os.caller"].isin(
                ["Framer", "Strategist", "Aligner", "Executor", "Narrator", "Scout"]
            )
        ].copy()

        if agent_spans.empty:
            return None

        # Build eval dataframe from span input/output
        rows = []
        for _, span in agent_spans.iterrows():
            rows.append({
                "agent": span.get("attributes.pm_os.caller", "unknown"),
                "query": span.get("attributes.input.value", ""),
                "agent_output": span.get("attributes.output.value", ""),
            })

        return pd.DataFrame(rows)

    except Exception as e:
        log.warning("Failed to export traces: %s", e)
        return None


def _try_log_dataset(df: pd.DataFrame, name: str):
    """Best-effort: upload a dataframe as a Phoenix Dataset for comparison."""
    try:
        import phoenix as px

        client = px.Client()
        client.upload_dataset(
            dataset_name=name,
            dataframe=df,
        )
        print(f"  → Logged to Phoenix dataset: {name}")
    except Exception as e:
        log.debug("Could not log to Phoenix dataset (non-fatal): %s", e)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PM OS Phoenix Evaluation Suite")
    parser.add_argument(
        "--eval",
        choices=["intent", "quality", "traces", "all"],
        default="all",
        help="Which eval to run (default: all)",
    )
    parser.add_argument(
        "--dataset", type=str, default=None,
        help="Path to golden dataset JSON (default: golden_dataset.json)",
    )
    parser.add_argument(
        "--outputs", type=str, default=None,
        help="Path to agent outputs JSONL for quality eval",
    )
    parser.add_argument(
        "--judge-model", type=str, default="openai/gpt-4o-mini",
        help="Model for LLM-as-judge (default: openai/gpt-4o-mini)",
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Limit intent eval to first N cases (for quick testing)",
    )

    args = parser.parse_args()

    if args.eval in ("intent", "all"):
        eval_intent_classification(
            dataset_path=args.dataset,
            sample_size=args.sample,
        )

    if args.eval in ("quality", "all"):
        eval_agent_quality(
            agent_outputs_path=args.outputs,
            judge_model=args.judge_model,
        )

    if args.eval in ("traces", "all"):
        eval_traces()


if __name__ == "__main__":
    main()
