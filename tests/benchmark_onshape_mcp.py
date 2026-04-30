"""Benchmark: prompt → Onshape regen for the Jarvis MCP path.

Measures end-to-end wall-clock from the moment we hand a prompt to Claude
Code (via `claude --print` with MCP config) to the moment the Onshape
document microversion advances (= Onshape cloud finished regenerating and
the browser will reflect the change on next poll).

Why microversion as the stop signal: it is the canonical "the document
changed" event in Onshape. From the user's browser perspective, the regen
arrives within ~100 ms after the microversion bump.

Comparison with the legacy CadQuery iframe path: the legacy service was
disabled on 2026-04-30 (see ../onshape-extension/legacy/README.md) and the
last successful uploads recorded in `journalctl -u onshape-cadgen` showed
20–40 s wall-clock for simple parts, with a known `Derived feature
status=ERROR` failure mode. We cite those numbers as historical baseline
rather than re-running the broken path.

Run on nativedev:

    cd /home/tommaso/projects/3dprint-pipeline
    python3 tests/benchmark_onshape_mcp.py \
        --document-id <DID> --workspace-id <WID> --element-id <EID> \
        --runs 5

The Onshape document/workspace/element IDs identify a Part Studio that the
benchmark is allowed to mutate. Use a throwaway document. Each prompt
appends features; reset the document between prompt families if needed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx

ONSHAPE_API_BASE = "https://cad.onshape.com/api/v6"

# 5 prompts spanning simple → complex → iterative → FeatureScript.
PROMPTS: list[dict] = [
    {
        "id": "P1_simple_cube",
        "label": "Cubo 30mm con foro centrale 10mm",
        "prompt": (
            "In the current Onshape Part Studio, create a 30 mm cube centered at the origin, "
            "then cut a 10 mm diameter hole through it along the Z axis."
        ),
        "expected_features": 3,
    },
    {
        "id": "P2_l_bracket",
        "label": "Bracket L 60×40×4mm con 4 fori M3 ai vertici",
        "prompt": (
            "Create an L-shaped bracket: 60 mm × 40 mm × 4 mm thick. "
            "Add four M3 through-holes (Ø3.4 mm) at the four corners of the larger flange, 5 mm in from the edges."
        ),
        "expected_features": 5,
    },
    {
        "id": "P3_enclosure_snap",
        "label": "Enclosure 80×60×40 walls 2 con coperchio snap-fit",
        "prompt": (
            "Design a snap-fit enclosure: outer 80×60×40 mm, walls 2 mm. "
            "Bottom shell with a 1 mm lip; top lid with matching 1 mm groove for press-fit assembly."
        ),
        "expected_features": 8,
    },
    {
        "id": "P4_iterative_height",
        "label": "Modifica del precedente: alza di 10mm",
        "prompt": "Increase the enclosure height by 10 mm (from 40 to 50 mm).",
        "expected_features": 1,  # one variable change OR one feature edit
        "iterative_after": "P3_enclosure_snap",
    },
    {
        "id": "P5_gear_featurescript",
        "label": "Ruota dentata 30 denti modulo 1mm",
        "prompt": (
            "Generate an involute spur gear: 30 teeth, module 1.0 mm, pressure angle 20°, "
            "face width 6 mm, bore 5 mm. Use FeatureScript if the standard Onshape gear "
            "feature is not available."
        ),
        "expected_features": 3,
    },
]


@dataclass
class RunResult:
    prompt_id: str
    run_index: int
    wall_clock_s: float
    success: bool
    feature_delta: int = 0
    error: str | None = None


@dataclass
class PromptStats:
    prompt_id: str
    label: str
    runs: list[RunResult] = field(default_factory=list)

    @property
    def successful(self) -> list[RunResult]:
        return [r for r in self.runs if r.success]

    @property
    def median_s(self) -> float | None:
        ok = [r.wall_clock_s for r in self.successful]
        return statistics.median(ok) if ok else None

    @property
    def p95_s(self) -> float | None:
        ok = sorted(r.wall_clock_s for r in self.successful)
        if not ok:
            return None
        idx = max(0, int(round(0.95 * (len(ok) - 1))))
        return ok[idx]


# ---------------------------------------------------------------------------
# Onshape microversion polling
# ---------------------------------------------------------------------------

def _load_onshape_keys() -> tuple[str, str]:
    """Read keys from the systemd-managed env file (mode 600)."""
    env_path = Path.home() / ".config" / "onshape-mcp" / "jarvis.env"
    if not env_path.exists():
        sys.exit(f"Onshape keys not found at {env_path}")
    ak = sk = None
    for line in env_path.read_text().splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k == "ONSHAPE_API_KEY":
            ak = v
        elif k == "ONSHAPE_API_SECRET":
            sk = v
    if not (ak and sk):
        sys.exit("ONSHAPE_API_KEY/SECRET missing from jarvis.env")
    return ak, sk


async def _get_microversion(client: httpx.AsyncClient, auth, did: str, wid: str) -> str:
    url = f"{ONSHAPE_API_BASE}/documents/d/{did}/w/{wid}/currentmicroversion"
    resp = await client.get(url, auth=auth, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()["microversion"]


async def _count_features(client: httpx.AsyncClient, auth, did: str, wid: str, eid: str) -> int:
    url = f"{ONSHAPE_API_BASE}/partstudios/d/{did}/w/{wid}/e/{eid}/features"
    resp = await client.get(url, auth=auth, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return len(resp.json().get("features", []))


# ---------------------------------------------------------------------------
# Claude Code invocation with MCP config
# ---------------------------------------------------------------------------

def _build_mcp_config(sse_url: str, tmp_dir: Path) -> Path:
    """Write a minimal mcp.json that points at the local Jarvis SSE endpoint.

    On nativedev we can hit the loopback URL directly (same machine) — no
    Tailscale hop. From a remote laptop, the Tailscale URL is used; both
    work because mcp-remote handles the bridge.
    """
    cfg = {
        "mcpServers": {
            "onshape": {
                "command": "npx",
                "args": ["-y", "mcp-remote", sse_url],
            }
        }
    }
    cfg_path = tmp_dir / "mcp_bench.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    return cfg_path


def _run_claude(prompt: str, mcp_config: Path, model: str, timeout: int) -> tuple[bool, str]:
    """Run `claude --print` with the given prompt + MCP config. Returns (ok, output)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [
        "claude",
        "--print",
        "--model", model,
        "--mcp-config", str(mcp_config),
        "--no-session-persistence",
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env,
        )
        return (proc.returncode == 0, proc.stdout + proc.stderr)
    except subprocess.TimeoutExpired:
        return (False, f"TIMEOUT after {timeout}s")


# ---------------------------------------------------------------------------
# Main benchmark loop
# ---------------------------------------------------------------------------

async def _run_one(
    prompt_def: dict,
    run_idx: int,
    sse_url: str,
    document_id: str,
    workspace_id: str,
    element_id: str,
    model: str,
    timeout: int,
    mcp_config: Path,
    auth,
    client: httpx.AsyncClient,
) -> RunResult:
    pre_mv = await _get_microversion(client, auth, document_id, workspace_id)
    pre_features = await _count_features(client, auth, document_id, workspace_id, element_id)

    # Inject document context into the prompt so Claude knows where to act.
    full_prompt = (
        f"Use the onshape MCP tools. Target document_id={document_id}, "
        f"workspace_id={workspace_id}, element_id={element_id}.\n\n"
        f"Task: {prompt_def['prompt']}"
    )

    t0 = time.perf_counter()
    ok, out = await asyncio.to_thread(_run_claude, full_prompt, mcp_config, model, timeout)
    t_claude = time.perf_counter() - t0

    # Poll microversion until it advances (cap at +30s after Claude returns).
    deadline = time.perf_counter() + 30
    post_mv = pre_mv
    while time.perf_counter() < deadline:
        post_mv = await _get_microversion(client, auth, document_id, workspace_id)
        if post_mv != pre_mv:
            break
        await asyncio.sleep(0.2)
    t_total = time.perf_counter() - t0

    post_features = await _count_features(client, auth, document_id, workspace_id, element_id)
    feature_delta = post_features - pre_features

    success = ok and post_mv != pre_mv
    error = None
    if not ok:
        error = "claude_cli_failed"
    elif post_mv == pre_mv:
        error = "no_microversion_change"

    print(
        f"  [{prompt_def['id']} run {run_idx}] "
        f"claude={t_claude:.2f}s total={t_total:.2f}s "
        f"Δfeat={feature_delta:+d} "
        f"{'OK' if success else 'FAIL: ' + (error or '')}"
    )

    return RunResult(
        prompt_id=prompt_def["id"],
        run_index=run_idx,
        wall_clock_s=t_total,
        success=success,
        feature_delta=feature_delta,
        error=error,
    )


async def main_async(args) -> int:
    ak, sk = _load_onshape_keys()
    auth = httpx.BasicAuth(ak, sk)

    tmp_dir = Path("/tmp/3dpp_bench")
    tmp_dir.mkdir(exist_ok=True)
    mcp_config = _build_mcp_config(args.sse_url, tmp_dir)

    stats_by_prompt: dict[str, PromptStats] = {
        p["id"]: PromptStats(prompt_id=p["id"], label=p["label"]) for p in PROMPTS
    }

    selected: Iterable[dict] = PROMPTS
    if args.only:
        wanted = set(args.only.split(","))
        selected = [p for p in PROMPTS if p["id"] in wanted]

    async with httpx.AsyncClient(timeout=30) as client:
        for prompt_def in selected:
            print(f"\n=== {prompt_def['id']}: {prompt_def['label']} ===")
            for i in range(args.runs):
                result = await _run_one(
                    prompt_def, i + 1,
                    args.sse_url,
                    args.document_id, args.workspace_id, args.element_id,
                    args.model, args.timeout, mcp_config,
                    auth, client,
                )
                stats_by_prompt[prompt_def["id"]].runs.append(result)

    _write_report(stats_by_prompt, args)
    return 0


def _write_report(stats: dict[str, PromptStats], args) -> None:
    report_dir = Path("tests/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = report_dir / f"benchmark_{ts}.md"

    lines = [
        f"# Benchmark — Jarvis Onshape MCP path",
        "",
        f"**When:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**SSE endpoint:** `{args.sse_url}`",
        f"**Model:** `{args.model}`",
        f"**Runs per prompt:** {args.runs}",
        f"**Document:** `{args.document_id}` workspace `{args.workspace_id}` element `{args.element_id}`",
        "",
        "Wall-clock = `claude --print` invocation start → first Onshape "
        "`currentmicroversion` change. Microversion is the canonical "
        "\"document changed\" event; the user's browser reflects the "
        "regen within ~100 ms after the bump.",
        "",
        "## Results",
        "",
        "| Prompt | Successes | Median (s) | p95 (s) | Δfeatures (median) |",
        "|--------|----------:|-----------:|--------:|-------------------:|",
    ]
    for pid, s in stats.items():
        ok_ratio = f"{len(s.successful)}/{len(s.runs)}"
        med = f"{s.median_s:.2f}" if s.median_s is not None else "—"
        p95 = f"{s.p95_s:.2f}" if s.p95_s is not None else "—"
        deltas = [r.feature_delta for r in s.successful]
        feat_med = statistics.median(deltas) if deltas else "—"
        lines.append(f"| {s.label[:40]} | {ok_ratio} | {med} | {p95} | {feat_med} |")

    lines += [
        "",
        "## Historical baseline — legacy CadQuery iframe path",
        "",
        "Sourced from `journalctl -u onshape-cadgen` (last successful runs",
        "before the service was disabled on 2026-04-30):",
        "",
        "| Phase | Time (s) |",
        "|-------|---------:|",
        "| Claude subprocess startup | 3–5 |",
        "| LLM thinking + CadQuery codegen | 5–10 |",
        "| CadQuery exec + STEP/STL export | 5–10 |",
        "| Onshape Translation API + polling | 5–10 |",
        "| Derived feature regen (often ERROR) | 1+ |",
        "| **Total wall-clock (when it worked)** | **~25–40 s** |",
        "",
        "## Failures detail",
        "",
    ]
    any_fail = False
    for s in stats.values():
        for r in s.runs:
            if not r.success:
                any_fail = True
                lines.append(f"- {r.prompt_id} run {r.run_index}: {r.error} (took {r.wall_clock_s:.1f}s)")
    if not any_fail:
        lines.append("(none)")

    out_path.write_text("\n".join(lines) + "\n")
    print(f"\nReport written to {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--document-id", required=True)
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--element-id", required=True, help="Part Studio element ID to mutate")
    ap.add_argument("--sse-url", default="http://127.0.0.1:3000/sse",
                    help="Jarvis MCP SSE URL. On nativedev use loopback to avoid Tailscale hop.")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--only", help="Comma-separated subset of prompt IDs (e.g. P1_simple_cube,P2_l_bracket)")
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
