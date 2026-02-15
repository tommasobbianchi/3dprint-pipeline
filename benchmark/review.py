#!/usr/bin/env python3
"""Interactive CLI reviewer for benchmark results.

Iterates through benchmark results, shows prompt + metrics + SVG preview,
and collects human pass/fail judgments.

Usage:
    python3 benchmark/review.py                           # review all unreviewed
    python3 benchmark/review.py --filter failures          # review only auto-failures
    python3 benchmark/review.py --filter solid-issues      # review only solid count issues
    python3 benchmark/review.py --filter complex           # review only complex tier
    python3 benchmark/review.py --prompt-id medium_001     # review single prompt
"""
import json
import subprocess
import argparse
import sys
from pathlib import Path
from datetime import datetime

BENCHMARK_DIR = Path(__file__).parent
RESULTS_DIR = BENCHMARK_DIR / "results"

FAILURE_CATEGORIES = [
    "wrong_shape",
    "detached_parts",
    "missing_features",
    "incorrect_dimensions",
    "code_error",
    "poor_quality",
    "other",
]


def load_results(filter_type: str | None = None, prompt_id: str | None = None) -> list[dict]:
    """Load benchmark results, optionally filtered."""
    results = []
    for p_dir in sorted(RESULTS_DIR.iterdir()):
        if not p_dir.is_dir():
            continue
        metrics_path = p_dir / "metrics.json"
        if not metrics_path.exists():
            continue
        try:
            with open(metrics_path) as f:
                metrics = json.load(f)
        except json.JSONDecodeError:
            continue

        review_path = p_dir / "review.json"
        has_review = review_path.exists()

        if prompt_id and metrics.get("prompt_id") != prompt_id:
            continue

        if filter_type == "unreviewed" and has_review:
            continue
        elif filter_type == "failures" and metrics.get("success", True):
            continue
        elif filter_type == "solid-issues":
            checks = metrics.get("checks", {})
            if checks and checks.get("single_solid", {}).get("pass", True):
                continue
        elif filter_type == "complex" and metrics.get("complexity") != "complex":
            continue
        elif filter_type == "medium" and metrics.get("complexity") != "medium":
            continue
        elif filter_type == "simple" and metrics.get("complexity") != "simple":
            continue

        results.append({
            "dir": p_dir,
            "metrics": metrics,
            "has_review": has_review,
        })

    return results


def display_result(result: dict):
    """Display a result's metrics in the terminal."""
    m = result["metrics"]
    d = result["dir"]

    print(f"\n{'='*60}")
    print(f"  {m.get('prompt_id', '?')} [{m.get('complexity', '?')}]")
    print(f"{'='*60}")
    print(f"\n  Prompt: {m.get('prompt_text', '?')}\n")

    # Automated checks
    checks = m.get("checks", {})
    if checks:
        print("  Automated Checks:")
        for name, check in checks.items():
            icon = "PASS" if check.get("pass") else "FAIL"
            print(f"    [{icon}] {name}: {check.get('detail', '')}")
    else:
        print("  Automated Checks: N/A")

    # Metrics
    metrics = m.get("metrics", {})
    if metrics:
        size = metrics.get("size")
        if size:
            print(f"\n  Size: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm")
        vol = metrics.get("volume")
        if vol:
            print(f"  Volume: {vol:.0f} mm3")
        solids = metrics.get("solid_count")
        if solids:
            print(f"  Solid count: {solids}")

    # Error snippet
    stderr = m.get("stderr_snippet")
    if stderr and stderr.strip():
        print(f"\n  Error: {stderr[:200]}")

    # Files
    files = m.get("files", {})
    if files:
        print(f"\n  Files: {', '.join(files.keys())}")
    else:
        print(f"\n  Files: none exported")

    # Previous review
    if result["has_review"]:
        try:
            with open(d / "review.json") as f:
                prev = json.load(f)
            print(f"\n  Previous review: {prev.get('verdict', '?')} "
                  f"({prev.get('category', '')}) {prev.get('notes', '')}")
        except (json.JSONDecodeError, FileNotFoundError):
            pass


def open_preview(result_dir: Path):
    """Open SVG preview in default viewer."""
    svg_path = result_dir / "output.svg"
    if svg_path.exists():
        try:
            subprocess.Popen(
                ["xdg-open", str(svg_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"  -> Opened: {svg_path}")
        except FileNotFoundError:
            print(f"  -> SVG at: {svg_path} (xdg-open not available)")
    else:
        stl_path = result_dir / "output.stl"
        if stl_path.exists():
            print(f"  -> No SVG. STL at: {stl_path}")
        else:
            print(f"  -> No preview files available")


def get_review() -> dict | None:
    """Prompt user for review verdict."""
    print(f"\n  [P]ass  [F]ail  [A]cceptable  [S]kip  [Q]uit")
    while True:
        choice = input("  Verdict: ").strip().lower()
        if choice in ("q", "quit"):
            return None
        if choice in ("s", "skip"):
            return "skip"
        if choice in ("p", "pass"):
            verdict = "pass"
            break
        if choice in ("a", "acceptable"):
            verdict = "acceptable"
            break
        if choice in ("f", "fail"):
            verdict = "fail"
            break
        print("  Invalid choice. Use P/F/A/S/Q")

    category = None
    if verdict == "fail":
        print(f"\n  Failure category:")
        for i, cat in enumerate(FAILURE_CATEGORIES, 1):
            print(f"    {i}. {cat}")
        while True:
            cat_input = input("  Category (number): ").strip()
            try:
                idx = int(cat_input) - 1
                if 0 <= idx < len(FAILURE_CATEGORIES):
                    category = FAILURE_CATEGORIES[idx]
                    break
            except ValueError:
                if cat_input in FAILURE_CATEGORIES:
                    category = cat_input
                    break
            print("  Invalid. Enter a number 1-7")

    notes = input("  Notes (optional, Enter to skip): ").strip() or None

    return {
        "verdict": verdict,
        "category": category,
        "notes": notes,
        "reviewed_at": datetime.now().isoformat(),
        "reviewer": "human",
    }


def main():
    parser = argparse.ArgumentParser(description="Review benchmark results")
    parser.add_argument(
        "--filter",
        choices=["unreviewed", "failures", "solid-issues", "simple", "medium", "complex"],
        default="unreviewed",
        help="Filter results (default: unreviewed)",
    )
    parser.add_argument("--prompt-id", help="Review a single prompt")
    parser.add_argument("--no-preview", action="store_true", help="Don't open SVG previews")
    args = parser.parse_args()

    filter_type = None if args.prompt_id else args.filter
    results = load_results(filter_type=filter_type, prompt_id=args.prompt_id)

    if not results:
        print("No results to review with the given filter.")
        if args.filter == "unreviewed":
            print("  All results have been reviewed, or no results exist yet.")
            print("  Run: python3 benchmark/run_benchmark.py")
        return

    print(f"\n  {len(results)} results to review (filter: {args.filter or 'all'})\n")

    reviewed = 0
    skipped = 0
    for i, result in enumerate(results, 1):
        print(f"\n  --- {i}/{len(results)} ---")
        display_result(result)

        if not args.no_preview:
            open_preview(result["dir"])

        review = get_review()

        if review is None:
            print("\n  Quitting review.")
            break
        if review == "skip":
            skipped += 1
            continue

        # Save review
        review_path = result["dir"] / "review.json"
        with open(review_path, "w") as f:
            json.dump(review, f, indent=2)
        reviewed += 1
        print(f"  -> Saved: {review['verdict']}")

    print(f"\n  Review session: {reviewed} reviewed, {skipped} skipped")
    if reviewed > 0:
        print(f"  Generate report: python3 benchmark/report.py")


if __name__ == "__main__":
    main()
