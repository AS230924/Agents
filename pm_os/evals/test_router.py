"""
Evaluation script for the E-commerce PM OS Router.
Runs the intent classifier against the golden dataset and reports accuracy.
"""

import json
import sys
import time
from pathlib import Path

# Add parent to path so we can import pm_os as a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pm_os.core.intent_classifier import classify


GOLDEN_PATH = Path(__file__).resolve().parent.parent / "golden_dataset.json"


def run_eval(dataset_path: str | Path | None = None, verbose: bool = True):
    path = Path(dataset_path) if dataset_path else GOLDEN_PATH
    with open(path) as f:
        dataset = json.load(f)

    correct = 0
    total = 0
    results_by_type: dict[str, dict] = {}
    failures: list[dict] = []

    for case in dataset:
        expected = case["expected_intent"]
        test_type = case.get("test_type", "unknown")

        if test_type not in results_by_type:
            results_by_type[test_type] = {"correct": 0, "total": 0}

        # Skip None-intent cases for classification accuracy
        # (they test rejection, not classification)
        if expected == "None":
            result = classify({"query": case["user_query"]})
            is_correct = result["intent"] == "None"
            results_by_type[test_type]["total"] += 1
            total += 1
            if is_correct:
                correct += 1
                results_by_type[test_type]["correct"] += 1
            elif verbose:
                failures.append({
                    "id": case["id"],
                    "query": case["user_query"][:80],
                    "expected": expected,
                    "got": result["intent"],
                    "confidence": result["confidence"],
                    "reasoning": result["reasoning"][:100],
                })
            # Rate limit to avoid API throttling
            time.sleep(0.5)
            continue

        result = classify({"query": case["user_query"]})

        results_by_type[test_type]["total"] += 1
        total += 1

        if result["intent"] == expected:
            correct += 1
            results_by_type[test_type]["correct"] += 1
        else:
            if verbose:
                failures.append({
                    "id": case["id"],
                    "query": case["user_query"][:80],
                    "expected": expected,
                    "got": result["intent"],
                    "confidence": result["confidence"],
                    "reasoning": result["reasoning"][:100],
                })

        # Rate limit
        time.sleep(0.5)

    # Print results
    print("\n" + "=" * 60)
    print("E-COMMERCE PM OS ROUTER — EVAL RESULTS")
    print("=" * 60)

    for ttype, stats in sorted(results_by_type.items()):
        t = stats["total"]
        c = stats["correct"]
        pct = c / t * 100 if t > 0 else 0
        print(f"\n  {ttype:15s}  {c}/{t}  ({pct:.1f}%)")

    overall_pct = correct / total * 100 if total > 0 else 0
    print(f"\n  {'OVERALL':15s}  {correct}/{total}  ({overall_pct:.1f}%)")
    print("=" * 60)

    if failures and verbose:
        print(f"\nFAILURES ({len(failures)}):\n")
        for f in failures:
            print(f"  {f['id']}")
            print(f"    Query:    {f['query']}...")
            print(f"    Expected: {f['expected']}")
            print(f"    Got:      {f['got']} ({f['confidence']:.0%})")
            print(f"    Reason:   {f['reasoning']}")
            print()

    return {
        "correct": correct,
        "total": total,
        "accuracy": overall_pct,
        "by_type": results_by_type,
        "failures": failures,
    }


if __name__ == "__main__":
    run_eval()
