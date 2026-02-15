#!/usr/bin/env python3
"""Benchmark runner for 3dprint-pipeline CadQuery code generation.

Uses `claude` CLI (covered by Max subscription) to generate CadQuery code
for each test prompt, executes it, and records automated quality metrics.

Usage:
    python3 benchmark/run_benchmark.py                      # run all
    python3 benchmark/run_benchmark.py --resume              # skip completed
    python3 benchmark/run_benchmark.py --filter simple       # run one tier
    python3 benchmark/run_benchmark.py --prompt-id simple_001  # run single
    python3 benchmark/run_benchmark.py --dry-run             # print prompts only
"""
import json
import os
import subprocess
import re
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime

# === CONFIGURATION ===
BENCHMARK_DIR = Path(__file__).parent
PROMPTS_FILE = BENCHMARK_DIR / "prompts.json"
RESULTS_DIR = BENCHMARK_DIR / "results"
SKILLS_DIR = BENCHMARK_DIR.parent / "skills"

MODEL = "sonnet"  # claude CLI alias
EXEC_TIMEOUT = 60  # [s] CadQuery execution timeout
CLAUDE_TIMEOUT = 120  # [s] claude CLI timeout per prompt
RETRY_MAX = 2
DELAY_BETWEEN = 1  # [s] between prompts

# SKILL.md files that form the system prompt
# NOTE: cadquery-validate excluded — it instructs execution/validation which
# causes Claude to try running code via tools instead of outputting it
SKILL_FILES = [
    SKILLS_DIR / "spatial-reasoning" / "SKILL.md",
    SKILLS_DIR / "cadquery-codegen" / "SKILL.md",
]

# Measurement code appended to user's CadQuery script
MEASUREMENT_CODE = """
# === BENCHMARK MEASUREMENT ===
_r = result
_bb = _r.val().BoundingBox()
_vol = _r.val().Volume()
_solids = len(_r.val().Solids())
print(f"BBOX:{_bb.xmin:.2f},{_bb.ymin:.2f},{_bb.zmin:.2f},{_bb.xmax:.2f},{_bb.ymax:.2f},{_bb.zmax:.2f}")
print(f"SIZE:{_bb.xlen:.2f}x{_bb.ylen:.2f}x{_bb.zlen:.2f}")
print(f"VOLUME:{_vol:.2f}")
print(f"SOLIDS:{_solids}")
"""

# Export code appended for file generation
EXPORT_CODE = """
# === BENCHMARK EXPORT ===
import os as _os
_out = _os.environ.get("BENCHMARK_OUT_DIR", ".")
import cadquery as _cq
_cq.exporters.export(result, _os.path.join(_out, "output.step"))
_cq.exporters.export(result, _os.path.join(_out, "output.stl"))
try:
    _cq.exporters.export(result, _os.path.join(_out, "output.svg"), exportType="SVG")
except Exception:
    pass  # SVG export can fail on complex shapes
"""


def load_system_prompt() -> str:
    """Load and concatenate SKILL.md files into the system prompt."""
    parts = []
    for path in SKILL_FILES:
        if not path.exists():
            print(f"WARNING: Skill file not found: {path}", file=sys.stderr)
            continue
        content = path.read_text()
        # Strip frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()
        skill_name = path.parent.name
        parts.append(f"# === SKILL: {skill_name} ===\n\n{content}")
    return "\n\n---\n\n".join(parts)


def extract_python_code(response_text: str) -> str | None:
    """Extract the first Python code block from Claude's response."""
    # Try ```python ... ``` first
    match = re.search(r"```python\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try generic ``` ... ```
    match = re.search(r"```\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        code = match.group(1).strip()
        if "import cadquery" in code:
            return code
    # Fallback: look for import cadquery in raw text
    if "import cadquery" in response_text:
        lines = response_text.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if "import cadquery" in line:
                in_code = True
            if in_code:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines)
    return None


def parse_metrics(stdout: str) -> dict:
    """Parse BBOX, SIZE, VOLUME, SOLIDS from CadQuery output."""
    metrics = {
        "bounding_box": None,
        "size": None,
        "volume": None,
        "solid_count": None,
    }
    bbox_match = re.search(
        r"BBOX:([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)",
        stdout,
    )
    if bbox_match:
        metrics["bounding_box"] = {
            "min": [float(bbox_match.group(i)) for i in range(1, 4)],
            "max": [float(bbox_match.group(i)) for i in range(4, 7)],
        }
    size_match = re.search(r"SIZE:([-\d.]+)x([-\d.]+)x([-\d.]+)", stdout)
    if size_match:
        metrics["size"] = [float(size_match.group(i)) for i in range(1, 4)]
    vol_match = re.search(r"VOLUME:([-\d.]+)", stdout)
    if vol_match:
        metrics["volume"] = float(vol_match.group(1))
    sol_match = re.search(r"SOLIDS:(\d+)", stdout)
    if sol_match:
        metrics["solid_count"] = int(sol_match.group(1))
    return metrics


def execute_cadquery(code: str, work_dir: Path) -> dict:
    """Execute CadQuery code and return execution results + metrics."""
    work_dir.mkdir(parents=True, exist_ok=True)
    script_path = work_dir / "code.py"

    # Write the code + measurement + export
    full_code = code + "\n" + MEASUREMENT_CODE + "\n" + EXPORT_CODE
    script_path.write_text(full_code)

    try:
        proc = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT,
            env={**os.environ, "BENCHMARK_OUT_DIR": str(work_dir)},
        )
        success = proc.returncode == 0
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired:
        success = False
        stdout = ""
        stderr = f"TIMEOUT: Execution exceeded {EXEC_TIMEOUT}s"

    # Write just the user's code (without measurement/export appended)
    script_path.write_text(code)

    metrics = parse_metrics(stdout) if success else {
        "bounding_box": None,
        "size": None,
        "volume": None,
        "solid_count": None,
    }

    return {
        "success": success,
        "stdout": stdout,
        "stderr": stderr,
        "metrics": metrics,
    }


def run_automated_checks(exec_result: dict, expected_solid_count: int = 1) -> dict:
    """Run automated validation checks on execution results."""
    m = exec_result["metrics"]
    checks = {}

    # Check 1: Execution success
    checks["execution"] = {
        "pass": exec_result["success"],
        "detail": "OK" if exec_result["success"] else exec_result["stderr"][:200],
    }

    # Check 2: Bounding box valid
    if m["size"]:
        bb_ok = all(0.1 < s < 500 for s in m["size"])
        checks["bounding_box"] = {
            "pass": bb_ok,
            "detail": f"{m['size'][0]:.1f} x {m['size'][1]:.1f} x {m['size'][2]:.1f} mm",
        }
    else:
        checks["bounding_box"] = {"pass": False, "detail": "No bounding box data"}

    # Check 3: Volume valid
    if m["volume"] is not None:
        vol_ok = m["volume"] > 0
        checks["volume"] = {
            "pass": vol_ok,
            "detail": f"{m['volume']:.0f} mm3",
        }
    else:
        checks["volume"] = {"pass": False, "detail": "No volume data"}

    # Check 4: Single solid (no detached parts)
    if m["solid_count"] is not None:
        sol_ok = m["solid_count"] == expected_solid_count
        checks["single_solid"] = {
            "pass": sol_ok,
            "detail": f"{m['solid_count']} solid(s) (expected {expected_solid_count})",
        }
    else:
        checks["single_solid"] = {"pass": False, "detail": "No solid count data"}

    # Check 5: Fill ratio
    if m["size"] and m["volume"]:
        bb_vol = m["size"][0] * m["size"][1] * m["size"][2]
        fill_ratio = m["volume"] / bb_vol if bb_vol > 0 else 0
        checks["fill_ratio"] = {
            "pass": fill_ratio > 0.001,
            "detail": f"{fill_ratio:.4f}",
        }
    else:
        checks["fill_ratio"] = {"pass": False, "detail": "No data"}

    all_pass = all(c["pass"] for c in checks.values())

    return {
        "all_pass": all_pass,
        "checks": checks,
    }


CODE_WRAPPER = """You are a CadQuery code generator. Generate ONLY a complete, runnable Python CadQuery script.

CRITICAL RULES:
- Output ONLY Python code inside a single ```python``` block
- Do NOT explain, validate, execute, or export — just output the code
- The script must assign the final shape to a variable named `result`
- Include proper parametric variables with [mm] comments
- Export to "output.step" and "output.stl" at the end
- Follow all CadQuery best practices from your system prompt

User request:
"""


def call_claude(
    system_prompt: str,
    user_prompt: str,
    prompt_id: str,
    model: str = MODEL,
) -> str:
    """Call Claude via CLI in print mode with tools disabled. Returns response text."""
    env = {k: v for k, v in os.environ.items()}
    # Unset CLAUDECODE to allow nested invocation
    env.pop("CLAUDECODE", None)

    # Wrap user prompt to force code-only output
    full_prompt = CODE_WRAPPER + user_prompt

    for attempt in range(1, RETRY_MAX + 1):
        try:
            proc = subprocess.run(
                [
                    "claude",
                    "-p", full_prompt,
                    "--model", model,
                    "--system-prompt", system_prompt,
                    "--output-format", "text",
                    "--no-session-persistence",
                    "--tools", "",
                ],
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT,
                env=env,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout
            if attempt < RETRY_MAX:
                print(f"  Retry {attempt} for {prompt_id} (exit={proc.returncode})")
                stderr_snippet = proc.stderr[:200] if proc.stderr else ""
                if stderr_snippet:
                    print(f"    stderr: {stderr_snippet}")
                time.sleep(2)
        except subprocess.TimeoutExpired:
            if attempt < RETRY_MAX:
                print(f"  Timeout on {prompt_id}, retrying...")

    raise RuntimeError(
        f"claude CLI failed after {RETRY_MAX} attempts for {prompt_id}"
    )


def run_single_prompt(
    system_prompt: str,
    prompt: dict,
    results_dir: Path,
    model: str = MODEL,
) -> dict:
    """Run a single benchmark prompt end-to-end."""
    prompt_id = prompt["id"]
    work_dir = results_dir / prompt_id
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [{prompt['complexity']}] {prompt_id}: {prompt['text'][:60]}...")

    # Step 1: Call Claude CLI
    t0 = time.time()
    response_text = call_claude(
        system_prompt, prompt["text"], prompt_id, model=model
    )
    api_time = time.time() - t0

    # Save response
    (work_dir / "response.txt").write_text(response_text)

    # Step 2: Extract Python code
    code = extract_python_code(response_text)
    if not code:
        result = {
            "prompt_id": prompt_id,
            "complexity": prompt["complexity"],
            "prompt_text": prompt["text"],
            "success": False,
            "error": "No Python code extracted from response",
            "api_time_s": round(api_time, 1),
            "exec_result": None,
            "checks": None,
            "files": {},
        }
        (work_dir / "metrics.json").write_text(json.dumps(result, indent=2))
        return result

    # Step 3: Execute CadQuery
    t1 = time.time()
    exec_result = execute_cadquery(code, work_dir)
    exec_time = time.time() - t1

    # Step 4: Automated checks
    expected_solids = prompt.get("expected_solid_count", 1)
    check_result = run_automated_checks(exec_result, expected_solids)

    # Step 5: Check exported files
    files = {}
    for fmt in ["step", "stl", "svg"]:
        fpath = work_dir / f"output.{fmt}"
        if fpath.exists() and fpath.stat().st_size > 0:
            files[fmt] = str(fpath)

    result = {
        "prompt_id": prompt_id,
        "complexity": prompt["complexity"],
        "prompt_text": prompt["text"],
        "material": prompt.get("material", "PLA"),
        "success": check_result["all_pass"],
        "error": None if check_result["all_pass"] else "Automated checks failed",
        "api_time_s": round(api_time, 1),
        "exec_time_s": round(exec_time, 1),
        "metrics": exec_result["metrics"],
        "checks": check_result["checks"],
        "files": files,
        "stderr_snippet": exec_result["stderr"][:500] if exec_result["stderr"] else None,
    }
    (work_dir / "metrics.json").write_text(json.dumps(result, indent=2))
    return result


def generate_summary(all_results: list[dict], run_time: float, model_name: str = MODEL) -> dict:
    """Generate summary statistics from all results."""
    total = len(all_results)
    passed = sum(1 for r in all_results if r["success"])
    failed = total - passed

    by_complexity = {}
    for tier in ["simple", "medium", "complex"]:
        tier_results = [r for r in all_results if r["complexity"] == tier]
        tier_pass = sum(1 for r in tier_results if r["success"])
        by_complexity[tier] = {
            "total": len(tier_results),
            "pass": tier_pass,
            "fail": len(tier_results) - tier_pass,
        }

    by_check = {}
    check_names = ["execution", "bounding_box", "volume", "single_solid", "fill_ratio"]
    for check in check_names:
        check_pass = sum(
            1 for r in all_results
            if r["checks"] and r["checks"].get(check, {}).get("pass", False)
        )
        by_check[check] = {"pass": check_pass, "fail": total - check_pass}

    return {
        "run_date": datetime.now().isoformat(),
        "model": model_name,
        "total": total,
        "pass": passed,
        "fail": failed,
        "pass_rate_pct": round(passed / total * 100, 1) if total > 0 else 0,
        "by_complexity": by_complexity,
        "by_check": by_check,
        "total_time_s": round(run_time, 0),
    }


def main():
    parser = argparse.ArgumentParser(description="3dprint-pipeline benchmark runner")
    parser.add_argument("--resume", action="store_true", help="Skip completed prompts")
    parser.add_argument("--filter", choices=["simple", "medium", "complex"], help="Run only one tier")
    parser.add_argument("--prompt-id", help="Run a single prompt by ID")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts, don't run")
    parser.add_argument("--model", default=MODEL, help=f"Claude model (default: {MODEL})")
    args = parser.parse_args()

    model = args.model

    # Check CadQuery availability
    try:
        subprocess.run(
            ["python3", "-c", "import cadquery"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: CadQuery not available. Install with: pip install cadquery", file=sys.stderr)
        sys.exit(1)

    # Check claude CLI availability
    try:
        env = {k: v for k, v in os.environ.items()}
        env.pop("CLAUDECODE", None)
        proc = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if proc.returncode != 0:
            raise FileNotFoundError
        print(f"  Claude CLI: {proc.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("ERROR: claude CLI not available. Install Claude Code first.", file=sys.stderr)
        sys.exit(1)

    # Load prompts
    with open(PROMPTS_FILE) as f:
        data = json.load(f)
    prompts = data["prompts"]

    # Filter
    if args.prompt_id:
        prompts = [p for p in prompts if p["id"] == args.prompt_id]
        if not prompts:
            print(f"ERROR: Prompt '{args.prompt_id}' not found", file=sys.stderr)
            sys.exit(1)
    elif args.filter:
        prompts = [p for p in prompts if p["complexity"] == args.filter]

    # Resume: skip completed
    if args.resume:
        remaining = []
        for p in prompts:
            metrics_path = RESULTS_DIR / p["id"] / "metrics.json"
            if metrics_path.exists():
                print(f"  Skipping {p['id']} (already completed)")
            else:
                remaining.append(p)
        prompts = remaining

    print(f"\n{'='*60}")
    print(f"  3dprint-pipeline Benchmark")
    print(f"  Engine: claude CLI (Max subscription)")
    print(f"  Model: {model}")
    print(f"  Prompts: {len(prompts)}")
    print(f"  Output: {RESULTS_DIR}/")
    print(f"{'='*60}\n")

    if args.dry_run:
        for p in prompts:
            print(f"  [{p['complexity']:7}] {p['id']:15} {p['text'][:70]}...")
        print(f"\nDry run complete. {len(prompts)} prompts would be executed.")
        return

    # Load system prompt
    print("Loading system prompt from SKILL.md files...")
    system_prompt = load_system_prompt()
    print(f"  System prompt: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Run
    all_results = []
    t_start = time.time()

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}]", end=" ")
        try:
            result = run_single_prompt(system_prompt, prompt, RESULTS_DIR, model=model)
            status = "PASS" if result["success"] else "FAIL"
            detail = ""
            if not result["success"] and result["checks"]:
                failed_checks = [k for k, v in result["checks"].items() if not v["pass"]]
                detail = f" ({', '.join(failed_checks)})"
            elif not result["success"]:
                detail = f" ({result.get('error', 'unknown')})"
            print(f"  -> {status}{detail}")
            all_results.append(result)
        except Exception as e:
            print(f"  -> ERROR: {e}")
            all_results.append({
                "prompt_id": prompt["id"],
                "complexity": prompt["complexity"],
                "prompt_text": prompt["text"],
                "success": False,
                "error": str(e),
                "checks": None,
                "files": {},
            })

        # Small delay between prompts
        if i < len(prompts):
            time.sleep(DELAY_BETWEEN)

    run_time = time.time() - t_start

    # Generate and save summary
    summary = generate_summary(all_results, run_time, model_name=model)

    # Also load any previously completed results not in this run
    if args.resume or args.filter or args.prompt_id:
        existing_results = []
        for p_dir in sorted(RESULTS_DIR.iterdir()):
            if p_dir.is_dir() and (p_dir / "metrics.json").exists():
                if any(r["prompt_id"] == p_dir.name for r in all_results):
                    continue
                try:
                    with open(p_dir / "metrics.json") as f:
                        existing_results.append(json.load(f))
                except json.JSONDecodeError:
                    pass
        if existing_results:
            combined = existing_results + all_results
            summary = generate_summary(combined, run_time, model_name=model)

    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    # Print summary
    print(f"\n{'='*60}")
    print(f"  BENCHMARK COMPLETE")
    print(f"{'='*60}")
    print(f"  Total:     {summary['total']}")
    print(f"  Pass:      {summary['pass']} ({summary['pass_rate_pct']}%)")
    print(f"  Fail:      {summary['fail']}")
    print(f"  Time:      {summary['total_time_s']:.0f}s")
    print()
    for tier, stats in summary["by_complexity"].items():
        pct = round(stats["pass"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {tier:8}: {stats['pass']}/{stats['total']} ({pct}%)")
    print()
    print(f"  Checks:")
    for check, stats in summary["by_check"].items():
        pct = round(stats["pass"] / summary["total"] * 100) if summary["total"] > 0 else 0
        print(f"    {check:15}: {stats['pass']}/{summary['total']} ({pct}%)")
    print(f"\n  Results: {summary_path}")
    print(f"  Review:  python3 benchmark/review.py")


if __name__ == "__main__":
    main()
