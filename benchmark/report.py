#!/usr/bin/env python3
"""Report generator for benchmark results.

Reads all metrics and human reviews, generates a markdown summary report.

Usage:
    python3 benchmark/report.py                  # print to stdout + save
    python3 benchmark/report.py --output path    # save to specific file
"""
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

BENCHMARK_DIR = Path(__file__).parent
RESULTS_DIR = BENCHMARK_DIR / "results"


def load_all_results() -> list[dict]:
    """Load all metrics + review pairs."""
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

        review = None
        review_path = p_dir / "review.json"
        if review_path.exists():
            try:
                with open(review_path) as f:
                    review = json.load(f)
            except json.JSONDecodeError:
                pass

        results.append({
            "metrics": metrics,
            "review": review,
        })

    return results


def compute_stats(results: list[dict]) -> dict:
    """Compute comprehensive statistics."""
    total = len(results)
    if total == 0:
        return {"total": 0}

    # Automated pass rate
    auto_pass = sum(1 for r in results if r["metrics"].get("success"))
    auto_fail = total - auto_pass

    # Human review stats
    reviewed = [r for r in results if r["review"]]
    human_pass = sum(
        1 for r in reviewed if r["review"].get("verdict") in ("pass", "acceptable")
    )
    human_fail = sum(1 for r in reviewed if r["review"].get("verdict") == "fail")

    # By complexity
    by_complexity = {}
    for tier in ["simple", "medium", "complex"]:
        tier_results = [r for r in results if r["metrics"].get("complexity") == tier]
        tier_reviewed = [r for r in tier_results if r["review"]]
        tier_auto_pass = sum(1 for r in tier_results if r["metrics"].get("success"))
        tier_human_pass = sum(
            1 for r in tier_reviewed
            if r["review"].get("verdict") in ("pass", "acceptable")
        )
        tier_human_fail = sum(
            1 for r in tier_reviewed if r["review"].get("verdict") == "fail"
        )
        tier_solid_issues = sum(
            1 for r in tier_results
            if r["metrics"].get("checks", {}).get("single_solid", {}).get("pass") is False
        )
        by_complexity[tier] = {
            "total": len(tier_results),
            "auto_pass": tier_auto_pass,
            "auto_fail": len(tier_results) - tier_auto_pass,
            "reviewed": len(tier_reviewed),
            "human_pass": tier_human_pass,
            "human_fail": tier_human_fail,
            "solid_issues": tier_solid_issues,
        }

    # By automated check
    check_names = ["execution", "bounding_box", "volume", "single_solid", "fill_ratio"]
    by_check = {}
    for check in check_names:
        check_pass = sum(
            1 for r in results
            if r["metrics"].get("checks", {}).get(check, {}).get("pass", False)
        )
        by_check[check] = {"pass": check_pass, "fail": total - check_pass}

    # Failure mode analysis (from human reviews)
    failure_categories = Counter()
    failure_details = defaultdict(list)
    for r in reviewed:
        if r["review"].get("verdict") == "fail":
            cat = r["review"].get("category", "unknown")
            failure_categories[cat] += 1
            failure_details[cat].append({
                "id": r["metrics"].get("prompt_id"),
                "notes": r["review"].get("notes"),
            })

    # Auto-fail reasons (from checks)
    auto_fail_reasons = Counter()
    for r in results:
        if not r["metrics"].get("success"):
            checks = r["metrics"].get("checks", {})
            if checks:
                for name, check in checks.items():
                    if not check.get("pass"):
                        auto_fail_reasons[name] += 1
            else:
                auto_fail_reasons["no_code_extracted"] += 1

    return {
        "total": total,
        "auto_pass": auto_pass,
        "auto_fail": auto_fail,
        "auto_pass_pct": round(auto_pass / total * 100, 1),
        "reviewed": len(reviewed),
        "human_pass": human_pass,
        "human_fail": human_fail,
        "human_pass_pct": round(human_pass / len(reviewed) * 100, 1) if reviewed else 0,
        "by_complexity": by_complexity,
        "by_check": by_check,
        "failure_categories": dict(failure_categories.most_common()),
        "failure_details": dict(failure_details),
        "auto_fail_reasons": dict(auto_fail_reasons.most_common()),
    }


def load_previous_summary() -> dict | None:
    """Load previous summary for comparison."""
    prev_path = RESULTS_DIR / "previous_summary.json"
    if prev_path.exists():
        try:
            with open(prev_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return None


def generate_report(stats: dict, previous: dict | None = None) -> str:
    """Generate markdown report."""
    lines = []
    lines.append(f"# Benchmark Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Summary
    lines.append("## Overall Results")
    lines.append("")
    lines.append(f"- **Automated pass rate:** {stats['auto_pass']}/{stats['total']} ({stats['auto_pass_pct']}%)")
    if stats["reviewed"] > 0:
        lines.append(f"- **Human pass rate:** {stats['human_pass']}/{stats['reviewed']} ({stats['human_pass_pct']}%)")
    else:
        lines.append(f"- **Human review:** not yet completed")

    # Solid count specifically
    sol = stats["by_check"].get("single_solid", {})
    if sol:
        sol_pct = round(sol["pass"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        lines.append(f"- **Single solid rate:** {sol['pass']}/{stats['total']} ({sol_pct}%)")

    lines.append("")

    # By complexity table
    lines.append("## By Complexity")
    lines.append("")
    lines.append("| Tier | Total | Auto Pass | Human Pass | Solid Issues |")
    lines.append("|------|-------|-----------|------------|--------------|")
    for tier in ["simple", "medium", "complex"]:
        s = stats["by_complexity"].get(tier, {})
        if not s:
            continue
        auto_pct = round(s["auto_pass"] / s["total"] * 100) if s["total"] > 0 else 0
        human_str = f"{s['human_pass']}/{s['reviewed']}" if s["reviewed"] > 0 else "—"
        human_pct = f" ({round(s['human_pass']/s['reviewed']*100)}%)" if s["reviewed"] > 0 else ""
        lines.append(
            f"| {tier} | {s['total']} | {s['auto_pass']} ({auto_pct}%) "
            f"| {human_str}{human_pct} | {s['solid_issues']} |"
        )
    lines.append("")

    # Automated check breakdown
    lines.append("## Automated Check Breakdown")
    lines.append("")
    lines.append("| Check | Pass | Fail | Rate |")
    lines.append("|-------|------|------|------|")
    for check, s in stats["by_check"].items():
        pct = round(s["pass"] / stats["total"] * 100) if stats["total"] > 0 else 0
        lines.append(f"| {check} | {s['pass']} | {s['fail']} | {pct}% |")
    lines.append("")

    # Auto-fail reasons
    if stats["auto_fail_reasons"]:
        lines.append("## Auto-Fail Reasons")
        lines.append("")
        for reason, count in sorted(stats["auto_fail_reasons"].items(), key=lambda x: -x[1]):
            lines.append(f"- **{reason}**: {count} occurrences")
        lines.append("")

    # Human failure analysis
    if stats["failure_categories"]:
        lines.append("## Human-Identified Failure Modes")
        lines.append("")
        for cat, count in sorted(stats["failure_categories"].items(), key=lambda x: -x[1]):
            lines.append(f"### {cat} ({count} occurrences)")
            details = stats["failure_details"].get(cat, [])
            for d in details:
                notes = f" — {d['notes']}" if d.get("notes") else ""
                lines.append(f"- `{d['id']}`{notes}")
            lines.append("")

    # Comparison with previous
    if previous:
        lines.append("## Comparison with Previous Run")
        lines.append("")
        prev_pass_pct = previous.get("pass_rate_pct", 0)
        delta = stats["auto_pass_pct"] - prev_pass_pct
        direction = "+" if delta >= 0 else ""
        lines.append(f"| Metric | Previous | Current | Delta |")
        lines.append(f"|--------|----------|---------|-------|")
        lines.append(f"| Auto pass rate | {prev_pass_pct}% | {stats['auto_pass_pct']}% | {direction}{delta:.1f}% |")
        prev_total = previous.get("total", 0)
        if prev_total:
            lines.append(f"| Total prompts | {prev_total} | {stats['total']} | {stats['total']-prev_total:+d} |")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    if stats["auto_pass_pct"] >= 90:
        lines.append("- Pipeline quality is HIGH (>90% auto pass). Focus on edge cases.")
    elif stats["auto_pass_pct"] >= 70:
        lines.append("- Pipeline quality is MODERATE (70-90%). Review failure patterns below.")
    else:
        lines.append("- Pipeline quality needs IMPROVEMENT (<70%). Major failure modes must be addressed.")

    sol_check = stats["by_check"].get("single_solid", {})
    if sol_check.get("fail", 0) > 0:
        lines.append(f"- **Solid connectivity issues detected** ({sol_check['fail']} failures). "
                     f"Review XZ workplane direction and coordinate alignment in generated code.")

    exec_check = stats["by_check"].get("execution", {})
    if exec_check.get("fail", 0) > 2:
        lines.append(f"- **Execution failures** ({exec_check['fail']}). "
                     f"Review error catalog and auto-fix loop effectiveness.")

    complex_stats = stats["by_complexity"].get("complex", {})
    if complex_stats and complex_stats["total"] > 0:
        complex_pass = round(complex_stats["auto_pass"] / complex_stats["total"] * 100)
        if complex_pass < 60:
            lines.append(f"- **Complex prompts struggling** ({complex_pass}% pass). "
                         f"Consider adding more templates or improving spatial reasoning.")

    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark report")
    parser.add_argument("--output", help="Output file path (default: results/report.md)")
    args = parser.parse_args()

    results = load_all_results()
    if not results:
        print("No benchmark results found. Run: python3 benchmark/run_benchmark.py")
        return

    stats = compute_stats(results)
    previous = load_previous_summary()
    report = generate_report(stats, previous)

    # Save report
    output_path = Path(args.output) if args.output else RESULTS_DIR / "report.md"
    output_path.write_text(report)

    # Also save current summary as JSON (for future comparisons)
    summary_path = RESULTS_DIR / "summary.json"
    # Load existing summary if present
    summary = {}
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                summary = json.load(f)
        except json.JSONDecodeError:
            pass
    # Add human review stats
    summary["human_reviewed"] = stats["reviewed"]
    summary["human_pass"] = stats["human_pass"]
    summary["human_fail"] = stats["human_fail"]
    summary["human_pass_pct"] = stats["human_pass_pct"]
    summary_path.write_text(json.dumps(summary, indent=2))

    # Print report
    print(report)
    print(f"\n  Report saved to: {output_path}")


if __name__ == "__main__":
    main()
