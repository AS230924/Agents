"""
VC Analyst — Evaluation CLI
Run the full evaluation suite against the golden dataset.

Usage:
    python run_evals.py                          # Full eval suite
    python run_evals.py --no-quality             # Skip LLM-as-Judge (faster, cheaper)
    python run_evals.py --id GD-APP-001          # Single case
    python run_evals.py --category "Vertical AI" # Filter by category
    python run_evals.py --difficulty easy        # Filter by difficulty
    python run_evals.py --max 5                  # Only first 5 cases
    python run_evals.py --output report.txt      # Save report to file
    python run_evals.py --list                   # List all case IDs
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VC Analyst Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="Skip LLM-as-Judge quality evaluations (faster and cheaper)",
    )
    parser.add_argument(
        "--id",
        type=str,
        nargs="+",
        metavar="CASE_ID",
        help="Run only specific case ID(s), e.g. --id GD-APP-001 GD-VERT-001",
    )
    parser.add_argument(
        "--category",
        type=str,
        metavar="CATEGORY",
        help='Filter by category, e.g. --category "Vertical AI"',
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "medium", "hard"],
        help="Filter by difficulty level",
    )
    parser.add_argument(
        "--max",
        type=int,
        metavar="N",
        help="Run at most N cases",
    )
    parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="Save report to a file (e.g. --output report.txt)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available case IDs and exit",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        metavar="PATH",
        help="Path to custom golden dataset JSON (default: built-in)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-case progress output",
    )
    return parser.parse_args()


def list_cases(dataset_path: Path | None = None) -> None:
    """Print all available case IDs."""
    from vc_analyst.evals.runner import GOLDEN_DATASET_PATH, load_dataset
    path = Path(dataset_path) if dataset_path else GOLDEN_DATASET_PATH
    cases = load_dataset(path)

    print(f"\n{'ID':<16} {'Category':<35} {'Difficulty':<10} {'Type'}")
    print("─" * 78)
    for c in cases:
        print(
            f"{c['id']:<16} {c.get('category',''):<35} "
            f"{c.get('difficulty',''):<10} {c.get('test_type','')}"
        )
    print(f"\nTotal: {len(cases)} cases")


def main() -> None:
    args = parse_args()

    # ── List mode ─────────────────────────────────────────────────────────────
    if args.list:
        list_cases(args.dataset)
        sys.exit(0)

    # ── Validate API keys ─────────────────────────────────────────────────────
    import os
    if not os.getenv("XAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "❌ No API keys found.\n"
            "Set XAI_API_KEY (Grok) or ANTHROPIC_API_KEY (Claude) in your .env file."
        )
        sys.exit(1)

    # ── Run evals ─────────────────────────────────────────────────────────────
    from vc_analyst.evals.runner import run_evals, format_report, save_report
    from pathlib import Path as _Path

    dataset_path = _Path(args.dataset) if args.dataset else None

    kwargs = dict(
        run_quality=not args.no_quality,
        filter_ids=args.id,
        filter_category=args.category,
        filter_difficulty=args.difficulty,
        max_cases=args.max,
        verbose=not args.quiet,
    )
    if dataset_path:
        kwargs["dataset_path"] = dataset_path

    try:
        case_results, summary = run_evals(**kwargs)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user.")
        sys.exit(1)

    # ── Format and output report ──────────────────────────────────────────────
    report = format_report(
        case_results,
        summary,
        include_quality=not args.no_quality,
    )

    print(report)

    if args.output:
        save_report(report, args.output)
        print(f"\n📄 Report saved to: {args.output}")

    # Exit with non-zero if overall pass rate < 70%
    if summary.overall_pass_rate < 0.70:
        print(f"\n⚠️  Overall pass rate {summary.overall_pass_rate:.0%} is below 70% threshold.")
        sys.exit(2)
    else:
        print(f"\n✅ Evaluation complete. Overall pass rate: {summary.overall_pass_rate:.0%}")
        sys.exit(0)


if __name__ == "__main__":
    main()
