#!/usr/bin/env python3
"""CADPrompt Benchmark Runner for the 3D Print Pipeline.

Modes:
  code-only   — Execute reference Python code from the CADPrompt dataset.
  end-to-end  — Generate CadQuery code from text prompts via generate_cadquery.py stub.

Usage:
  python tests/run_benchmark.py --mode code-only --limit 5
  python tests/run_benchmark.py --mode end-to-end --category simple
  python tests/run_benchmark.py --mode code-only --ids 00000007,00031303
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
DATASET_DIR = TESTS_DIR / "cadprompt_repo" / "CADPrompt"
RESULTS_DIR = TESTS_DIR / "results"
REPORTS_DIR = TESTS_DIR / "reports"
STRATIFICATION_XLSX = TESTS_DIR / "cadprompt_repo" / "Data_Stratification.xlsx"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_stratification() -> dict[str, dict]:
    """Load category info from the Excel stratification file.

    Returns:
        {sample_id_str: {"semantic": ..., "mesh": ..., "compilation": ...}}
    """
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not installed — all samples marked as 'unknown' category")
        return {}

    wb = openpyxl.load_workbook(STRATIFICATION_XLSX, read_only=True)
    ws = wb.active
    data: dict[str, dict] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        id_int, sem, mesh, comp = row
        sample_id = f"{id_int:08d}"
        data[sample_id] = {
            "semantic": sem.strip(),
            "mesh": mesh.strip(),
            "compilation": comp,
        }
    wb.close()
    return data


def discover_samples(
    category: str | None = None,
    ids: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Discover CADPrompt samples from the dataset directory.

    Args:
        category: Filter by mesh complexity ("simple" or "complex"). None = all.
        ids: Specific sample IDs to include. Overrides category/limit.
        limit: Maximum number of samples to return.

    Returns:
        List of dicts with keys: id, dir, prompt, prompt_measured, code, gt_stl,
        gt_json, semantic, mesh.
    """
    strat = load_stratification()
    samples = []

    if ids:
        folder_names = ids
    else:
        folder_names = sorted(
            d.name for d in DATASET_DIR.iterdir() if d.is_dir() and d.name.isdigit()
        )

    for name in folder_names:
        sample_dir = DATASET_DIR / name
        if not sample_dir.is_dir():
            logger.warning("Sample directory not found: %s", sample_dir)
            continue

        info = strat.get(name, {"semantic": "unknown", "mesh": "unknown", "compilation": 0})

        if category and info["mesh"].lower() != category.lower():
            continue

        prompt_file = sample_dir / "Natural_Language_Descriptions_Prompt.txt"
        prompt_measured_file = sample_dir / "Natural_Language_Descriptions_Prompt_with_specific_measurements.txt"
        code_file = sample_dir / "Python_Code.py"
        gt_stl = sample_dir / "Ground_Truth.stl"
        gt_json = sample_dir / "Ground_Truth.json"

        samples.append({
            "id": name,
            "dir": str(sample_dir),
            "prompt": prompt_file.read_text().strip() if prompt_file.exists() else "",
            "prompt_measured": prompt_measured_file.read_text().strip() if prompt_measured_file.exists() else "",
            "code": code_file.read_text() if code_file.exists() else "",
            "gt_stl": str(gt_stl) if gt_stl.exists() else None,
            "gt_json": str(gt_json) if gt_json.exists() else None,
            "semantic": info["semantic"],
            "mesh": info["mesh"],
        })

    if limit and not ids:
        samples = samples[:limit]

    logger.info("Discovered %d samples%s", len(samples),
                f" (category={category})" if category else "")
    return samples


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------

EXPORT_PATCH = '''
import cadquery as cq
_orig_export = cq.exporters.export

def _patched_export(shape, fname, *a, **kw):
    """Redirect exports to our output directory."""
    import os
    base = os.path.basename(fname)
    ext = os.path.splitext(base)[1].lower()
    if ext == ".step" or ext == ".stp":
        out = os.path.join("{output_dir}", "output.step")
    elif ext == ".stl":
        out = os.path.join("{output_dir}", "output.stl")
    else:
        out = os.path.join("{output_dir}", base)
    return _orig_export(shape, out, *a, **kw)

cq.exporters.export = _patched_export
'''


def execute_code(code: str, output_dir: Path, timeout: int = 30) -> dict:
    """Execute CadQuery code in a subprocess.

    Returns dict with: success, error, execution_time_s, stdout, stderr.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepend the export-redirect patch
    patched = EXPORT_PATCH.format(output_dir=str(output_dir)) + "\n" + code

    script_path = output_dir / "code.py"
    script_path.write_text(patched)

    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(output_dir),
        )
        elapsed = time.time() - t0
        success = proc.returncode == 0
        error = proc.stderr.strip() if not success else None

        # Also check that at least one output file was produced
        has_output = (output_dir / "output.stl").exists() or (output_dir / "output.step").exists()
        if success and not has_output:
            success = False
            error = "Script succeeded but no output files produced"

        return {
            "success": success,
            "error": error,
            "execution_time_s": round(elapsed, 3),
            "stdout": proc.stdout.strip()[:2000],
            "stderr": proc.stderr.strip()[:2000],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout ({timeout}s)",
            "execution_time_s": timeout,
            "stdout": "",
            "stderr": "",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "execution_time_s": time.time() - t0,
            "stdout": "",
            "stderr": "",
        }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_single(sample: dict, mode: str, output_dir: Path, timeout: int = 30) -> dict:
    """Run benchmark for a single sample.

    Returns a complete result dict for JSON serialization.
    """
    sample_output = output_dir / sample["id"]

    # Get the code to execute
    if mode == "code-only":
        code = sample["code"]
        if not code:
            return {
                "id": sample["id"],
                "category_semantic": sample["semantic"],
                "category_mesh": sample["mesh"],
                "prompt": sample["prompt_measured"],
                "mode": mode,
                "generated_code": "",
                "execution_success": False,
                "execution_error": "No reference code in dataset",
                "execution_time_s": 0,
                "chamfer_distance": None,
                "bbox_similarity": None,
                "volume_ratio": None,
                "gt_volume": None,
                "gen_volume": None,
            }
    elif mode == "end-to-end":
        from generate_cadquery import generate
        prompt = sample["prompt_measured"] or sample["prompt"]
        try:
            code = generate(prompt)
        except Exception as e:
            return {
                "id": sample["id"],
                "category_semantic": sample["semantic"],
                "category_mesh": sample["mesh"],
                "prompt": prompt,
                "mode": mode,
                "generated_code": "",
                "execution_success": False,
                "execution_error": f"Code generation failed: {e}",
                "execution_time_s": 0,
                "chamfer_distance": None,
                "bbox_similarity": None,
                "volume_ratio": None,
                "gt_volume": None,
                "gen_volume": None,
            }
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Execute
    exec_result = execute_code(code, sample_output, timeout=timeout)

    # Compute metrics if execution succeeded
    metrics_data: dict = {
        "chamfer_distance": None,
        "bbox_similarity": None,
        "volume_ratio": None,
        "gt_volume": None,
        "gen_volume": None,
        "gt_bbox": None,
        "gen_bbox": None,
    }

    if exec_result["success"] and sample.get("gt_stl"):
        gen_stl = sample_output / "output.stl"
        gt_stl = Path(sample["gt_stl"])

        if gen_stl.exists() and gt_stl.exists():
            try:
                from metrics import compute_all_metrics
                m = compute_all_metrics(gt_stl, gen_stl)
                metrics_data = {
                    "chamfer_distance": m.chamfer_distance,
                    "bbox_similarity": m.bbox_similarity,
                    "volume_ratio": m.volume_ratio,
                    "gt_volume": m.gt_volume,
                    "gen_volume": m.gen_volume,
                    "gt_bbox": m.gt_bbox,
                    "gen_bbox": m.gen_bbox,
                }
            except Exception as e:
                logger.warning("Metrics computation failed for %s: %s", sample["id"], e)

    result = {
        "id": sample["id"],
        "category_semantic": sample["semantic"],
        "category_mesh": sample["mesh"],
        "prompt": sample["prompt_measured"] or sample["prompt"],
        "mode": mode,
        "generated_code": code,
        "execution_success": exec_result["success"],
        "execution_error": exec_result["error"],
        "execution_time_s": exec_result["execution_time_s"],
        **metrics_data,
    }

    # Save individual result
    result_file = sample_output / "result.json"
    result_file.write_text(json.dumps(result, indent=2))

    return result


def run_benchmark(
    mode: str,
    category: str | None = None,
    ids: list[str] | None = None,
    limit: int | None = None,
    timeout: int = 30,
) -> list[dict]:
    """Run the full benchmark.

    Returns list of result dicts.
    """
    samples = discover_samples(category=category, ids=ids, limit=limit)
    if not samples:
        logger.error("No samples found!")
        return []

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RESULTS_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    n_pass = 0
    n_total = len(samples)

    for i, sample in enumerate(samples, 1):
        sid = sample["id"]
        logger.info("[%d/%d] Running %s (%s / %s)", i, n_total, sid,
                    sample["semantic"], sample["mesh"])

        result = run_single(sample, mode, output_dir, timeout=timeout)
        results.append(result)

        status = "PASS" if result["execution_success"] else "FAIL"
        if result["execution_success"]:
            n_pass += 1
            cd_str = f"CD={result['chamfer_distance']:.4f}" if result.get("chamfer_distance") is not None else "CD=N/A"
            logger.info("  %s  %s  time=%.1fs", status, cd_str, result["execution_time_s"])
        else:
            err_short = (result["execution_error"] or "")[:80]
            logger.info("  %s  %s", status, err_short)

    # Save summary
    summary = build_summary(results, mode, run_id)
    summary_file = output_dir / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))

    # Generate report
    report = generate_report(results, summary)
    report_file = REPORTS_DIR / f"report_{run_id}.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report)

    logger.info("Results saved to %s", output_dir)
    logger.info("Report saved to %s", report_file)

    # Print report to stdout
    print("\n" + report)

    return results


# ---------------------------------------------------------------------------
# Summary & Report
# ---------------------------------------------------------------------------

def build_summary(results: list[dict], mode: str, run_id: str) -> dict:
    """Build a summary dict from results."""
    total = len(results)
    executed = [r for r in results if r["execution_success"]]
    failed = [r for r in results if not r["execution_success"]]

    # Metrics for successful executions
    cds = [r["chamfer_distance"] for r in executed if r.get("chamfer_distance") is not None]
    bbs = [r["bbox_similarity"] for r in executed if r.get("bbox_similarity") is not None]
    vrs = [r["volume_ratio"] for r in executed if r.get("volume_ratio") is not None]

    def mean(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 5) if xs else None

    def median(xs: list[float]) -> float | None:
        if not xs:
            return None
        s = sorted(xs)
        n = len(s)
        return round(s[n // 2], 5) if n % 2 else round((s[n // 2 - 1] + s[n // 2]) / 2, 5)

    # By category (mesh complexity)
    by_mesh: dict[str, dict] = {}
    for r in results:
        cat = r.get("category_mesh", "unknown")
        if cat not in by_mesh:
            by_mesh[cat] = {"total": 0, "pass": 0, "cds": [], "bbs": [], "vrs": []}
        by_mesh[cat]["total"] += 1
        if r["execution_success"]:
            by_mesh[cat]["pass"] += 1
            if r.get("chamfer_distance") is not None:
                by_mesh[cat]["cds"].append(r["chamfer_distance"])
            if r.get("bbox_similarity") is not None:
                by_mesh[cat]["bbs"].append(r["bbox_similarity"])
            if r.get("volume_ratio") is not None:
                by_mesh[cat]["vrs"].append(r["volume_ratio"])

    by_mesh_summary = {}
    for cat, d in by_mesh.items():
        by_mesh_summary[cat] = {
            "total": d["total"],
            "pass": d["pass"],
            "pass_rate_pct": round(100 * d["pass"] / d["total"], 1) if d["total"] else 0,
            "mean_cd": mean(d["cds"]),
            "mean_bbox_sim": mean(d["bbs"]),
            "mean_vol_ratio": mean(d["vrs"]),
        }

    # By semantic complexity
    by_semantic: dict[str, dict] = {}
    for r in results:
        cat = r.get("category_semantic", "unknown")
        if cat not in by_semantic:
            by_semantic[cat] = {"total": 0, "pass": 0}
        by_semantic[cat]["total"] += 1
        if r["execution_success"]:
            by_semantic[cat]["pass"] += 1

    by_semantic_summary = {}
    for cat, d in by_semantic.items():
        by_semantic_summary[cat] = {
            "total": d["total"],
            "pass": d["pass"],
            "pass_rate_pct": round(100 * d["pass"] / d["total"], 1) if d["total"] else 0,
        }

    # Error breakdown
    error_types: dict[str, int] = {}
    for r in failed:
        err = r.get("execution_error", "unknown") or "unknown"
        # Classify the error
        if "Timeout" in err:
            etype = "timeout"
        elif "SyntaxError" in err:
            etype = "syntax_error"
        elif "ImportError" in err or "ModuleNotFoundError" in err:
            etype = "import_error"
        elif "StdFail_NotDone" in err:
            etype = "fillet_crash"
        elif "Wire not closed" in err or "not closed" in err.lower():
            etype = "wire_not_closed"
        elif "No reference code" in err:
            etype = "no_code"
        elif "No pending wires" in err:
            etype = "no_pending_wires"
        elif "no output files" in err.lower():
            etype = "no_output"
        else:
            etype = "other"
        error_types[etype] = error_types.get(etype, 0) + 1

    return {
        "run_id": run_id,
        "run_date": datetime.now().isoformat(),
        "mode": mode,
        "total": total,
        "pass": len(executed),
        "fail": len(failed),
        "invalid_rate_pct": round(100 * len(failed) / total, 1) if total else 0,
        "execution_success_pct": round(100 * len(executed) / total, 1) if total else 0,
        "mean_chamfer_distance": mean(cds),
        "median_chamfer_distance": median(cds),
        "mean_bbox_similarity": mean(bbs),
        "mean_volume_ratio": mean(vrs),
        "mean_execution_time_s": mean([r["execution_time_s"] for r in results]),
        "by_mesh_complexity": by_mesh_summary,
        "by_semantic_complexity": by_semantic_summary,
        "error_types": error_types,
    }


def generate_report(results: list[dict], summary: dict) -> str:
    """Generate a Markdown report from results and summary."""
    lines: list[str] = []
    a = lines.append

    a(f"# CADPrompt Benchmark Report — {summary['run_date'][:10]}")
    a("")
    a(f"**Mode:** {summary['mode']}  ")
    a(f"**Run ID:** {summary['run_id']}")
    a("")

    # Overall summary
    a("## Summary")
    a("")
    a(f"| Metric | Value |")
    a(f"|--------|-------|")
    a(f"| Total tests | {summary['total']} |")
    a(f"| Execution success | {summary['pass']}/{summary['total']} ({summary['execution_success_pct']}%) |")
    a(f"| Invalid Rate (IR) | {summary['invalid_rate_pct']}% |")
    a(f"| Mean Chamfer Distance | {_fmt(summary['mean_chamfer_distance'])} |")
    a(f"| Median Chamfer Distance | {_fmt(summary['median_chamfer_distance'])} |")
    a(f"| Mean BBox Similarity | {_fmt(summary['mean_bbox_similarity'], pct=True)} |")
    a(f"| Mean Volume Ratio | {_fmt(summary['mean_volume_ratio'])} |")
    a(f"| Mean Execution Time | {_fmt(summary['mean_execution_time_s'])}s |")
    a("")

    # By mesh complexity
    a("## By Mesh Complexity")
    a("")
    a("| Category | Total | Pass | Rate | Mean CD | Mean BBox Sim | Mean Vol Ratio |")
    a("|----------|-------|------|------|---------|---------------|----------------|")
    for cat in ["Simple", "Complex", "unknown"]:
        d = summary["by_mesh_complexity"].get(cat)
        if not d:
            continue
        a(f"| {cat} | {d['total']} | {d['pass']} | {d['pass_rate_pct']}% "
          f"| {_fmt(d['mean_cd'])} | {_fmt(d['mean_bbox_sim'], pct=True)} "
          f"| {_fmt(d['mean_vol_ratio'])} |")
    a("")

    # By semantic complexity
    a("## By Semantic Complexity")
    a("")
    a("| Category | Total | Pass | Rate |")
    a("|----------|-------|------|------|")
    for cat in ["Simple", "Moderate", "Complex", "Very Complex", "unknown"]:
        d = summary["by_semantic_complexity"].get(cat)
        if not d:
            continue
        a(f"| {cat} | {d['total']} | {d['pass']} | {d['pass_rate_pct']}% |")
    a("")

    # Error breakdown
    if summary["error_types"]:
        a("## Error Breakdown")
        a("")
        a("| Error Type | Count |")
        a("|------------|-------|")
        for etype, count in sorted(summary["error_types"].items(), key=lambda x: -x[1]):
            a(f"| {etype} | {count} |")
        a("")

    # Top 10 best by Chamfer Distance
    valid = [r for r in results if r["execution_success"] and r.get("chamfer_distance") is not None]
    if valid:
        a("## Top 10 Best (lowest Chamfer Distance)")
        a("")
        a("| ID | Semantic | Mesh | CD | BBox Sim | Vol Ratio |")
        a("|----|----------|------|----|----------|-----------|")
        for r in sorted(valid, key=lambda x: x["chamfer_distance"])[:10]:
            a(f"| {r['id']} | {r['category_semantic']} | {r['category_mesh']} "
              f"| {r['chamfer_distance']:.5f} | {_fmt(r.get('bbox_similarity'), pct=True)} "
              f"| {_fmt(r.get('volume_ratio'))} |")
        a("")

        a("## Top 10 Worst (highest Chamfer Distance)")
        a("")
        a("| ID | Semantic | Mesh | CD | BBox Sim | Vol Ratio |")
        a("|----|----------|------|----|----------|-----------|")
        for r in sorted(valid, key=lambda x: -x["chamfer_distance"])[:10]:
            a(f"| {r['id']} | {r['category_semantic']} | {r['category_mesh']} "
              f"| {r['chamfer_distance']:.5f} | {_fmt(r.get('bbox_similarity'), pct=True)} "
              f"| {_fmt(r.get('volume_ratio'))} |")
        a("")

    # Failed tests
    failed = [r for r in results if not r["execution_success"]]
    if failed:
        a("## Failed Tests")
        a("")
        a("| ID | Semantic | Mesh | Error |")
        a("|----|----------|------|-------|")
        for r in failed:
            err = (r.get("execution_error") or "unknown")[:60]
            a(f"| {r['id']} | {r['category_semantic']} | {r['category_mesh']} | {err} |")
        a("")

    return "\n".join(lines)


def _fmt(val, pct: bool = False) -> str:
    """Format a metric value for display."""
    if val is None:
        return "N/A"
    if pct:
        return f"{val * 100:.1f}%"
    return f"{val:.5f}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CADPrompt Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_benchmark.py --mode code-only --limit 5
  python tests/run_benchmark.py --mode code-only --category simple
  python tests/run_benchmark.py --mode code-only --ids 00000007,00031303
  python tests/run_benchmark.py --mode end-to-end --limit 10
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["code-only", "end-to-end"],
        default="code-only",
        help="Execution mode (default: code-only)",
    )
    parser.add_argument(
        "--category",
        choices=["simple", "complex"],
        help="Filter by mesh complexity category",
    )
    parser.add_argument(
        "--ids",
        type=str,
        help="Comma-separated sample IDs to run (overrides --category/--limit)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of samples to run",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-script execution timeout in seconds (default: 30)",
    )

    args = parser.parse_args()

    ids = [s.strip() for s in args.ids.split(",")] if args.ids else None

    results = run_benchmark(
        mode=args.mode,
        category=args.category,
        ids=ids,
        limit=args.limit,
        timeout=args.timeout,
    )

    if not results:
        sys.exit(1)

    # Exit code: 0 if >50% pass, 1 otherwise
    pass_rate = sum(1 for r in results if r["execution_success"]) / len(results)
    sys.exit(0 if pass_rate > 0.5 else 1)


if __name__ == "__main__":
    main()
