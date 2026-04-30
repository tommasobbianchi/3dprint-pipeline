"""Benchmark v2: prompt → Onshape regen for the Jarvis MCP path.

Improvements over v1 (2026-04-30):
- Default --timeout 600 s (was 240 s; complex prompts on Sonnet legitimately
  needed 200+ s).
- Per-run subprocess logs in tests/reports/runs_<ts>/<prompt>_run<n>.log so
  failures can be investigated post-hoc.
- Session sharing for iterative prompts: prompts with `iterative_after` reuse
  the predecessor's session via `claude --session-id <uuid>`. Cuts cold
  context-discovery cost on follow-ups (the realistic interactive case).
- Fresh Part Studio per prompt family. Independent prompts (P1, P2, P5) each
  get a brand-new Part Studio so their state doesn't leak across runs.
  Iterative chains (P3 → P4) share a Part Studio.

Wall-clock = `claude --print` invocation start → first Onshape
`currentmicroversion` change after that invocation. Microversion is the
canonical "document changed" event; the user's browser reflects the regen
within ~100 ms after the bump.

Run:

    cd /home/tommaso/projects/3dprint-pipeline
    python3 tests/benchmark_onshape_mcp.py \
        --document-id <DID> --workspace-id <WID> \
        --runs 3

The element ID is no longer required from the CLI — the script creates a
fresh Part Studio per prompt family in the given document/workspace. Use
a throwaway document.
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
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx

ONSHAPE_API_BASE = "https://cad.onshape.com/api/v6"

# 5 prompts spanning simple → complex → iterative → FeatureScript.
# `family_key` groups prompts that share a Part Studio (and a Claude session).
PROMPTS: list[dict] = [
    {
        "id": "P1_simple_cube",
        "label": "Cubo 30mm con foro centrale 10mm",
        "prompt": (
            "In the current Onshape Part Studio, create a 30 mm cube centered at the origin, "
            "then cut a 10 mm diameter hole through it along the Z axis."
        ),
        "family_key": "P1",
    },
    {
        "id": "P2_l_bracket",
        "label": "Bracket L 60×40×4mm con 4 fori M3",
        "prompt": (
            "Create an L-shaped bracket: 60 mm × 40 mm × 4 mm thick. "
            "Add four M3 through-holes (Ø3.4 mm) at the four corners of the larger flange, 5 mm in from the edges."
        ),
        "family_key": "P2",
    },
    {
        "id": "P3_enclosure_snap",
        "label": "Enclosure 80×60×40 walls 2 snap-fit",
        "prompt": (
            "Design a snap-fit enclosure: outer 80×60×40 mm, walls 2 mm. "
            "Bottom shell with a 1 mm lip; top lid with matching 1 mm groove for press-fit assembly."
        ),
        "family_key": "P3",
    },
    {
        "id": "P4_iterative_height",
        "label": "P3 + alza di 10mm (iterativo)",
        "prompt": "Increase the enclosure height by 10 mm (from 40 to 50 mm).",
        "family_key": "P3",  # share Part Studio + session with P3
        "iterative_after": "P3_enclosure_snap",
    },
    {
        "id": "P5_gear_featurescript",
        "label": "Gear 30 denti modulo 1mm",
        "prompt": (
            "Generate an involute spur gear: 30 teeth, module 1.0 mm, pressure angle 20°, "
            "face width 6 mm, bore 5 mm. Use FeatureScript if the standard Onshape gear "
            "feature is not available."
        ),
        "family_key": "P5",
    },
]


@dataclass
class RunResult:
    prompt_id: str
    run_index: int
    wall_clock_s: float
    claude_s: float
    success: bool
    feature_delta: int = 0
    error: str | None = None
    log_path: str | None = None


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
# Onshape API helpers
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


async def _create_part_studio(client: httpx.AsyncClient, auth, did: str, wid: str, name: str) -> str:
    """Create a fresh Part Studio in the given workspace. Returns its element ID."""
    url = f"{ONSHAPE_API_BASE}/partstudios/d/{did}/w/{wid}"
    resp = await client.post(
        url, auth=auth,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"name": name},
    )
    resp.raise_for_status()
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Claude Code invocation
# ---------------------------------------------------------------------------

def _build_mcp_config(sse_url: str, tmp_dir: Path) -> Path:
    """Write a minimal mcp.json that points at the Jarvis SSE endpoint."""
    cfg = {
        "mcpServers": {
            "onshape": {
                "command": "uvx",
                "args": ["mcp-proxy", sse_url],
            }
        }
    }
    cfg_path = tmp_dir / "mcp_bench.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    return cfg_path


def _run_claude(
    prompt: str,
    mcp_config: Path,
    model: str,
    timeout: int,
    session_id: str,
    log_path: Path,
    is_resume: bool,
) -> tuple[bool, str]:
    """Run `claude --print` with the given prompt + MCP config.

    First invocation in a session: `--session-id <uuid>` pins a fresh
    session that Claude Code persists to disk.
    Follow-up (is_resume=True): `--resume <uuid>` continues the saved
    transcript. `--session-id` cannot be reused once a session exists —
    Claude rejects it with "Session ID is already in use."
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = ["claude", "--print", "--model", model,
           "--mcp-config", str(mcp_config),
           "--allowedTools", "mcp__onshape__*"]
    if is_resume:
        cmd += ["--resume", session_id]
    else:
        cmd += ["--session-id", session_id]
    cmd.append(prompt)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as logf:
        logf.write(f"# Command: {' '.join(repr(c) if ' ' in c else c for c in cmd[:-1])} <prompt>\n")
        logf.write(f"# Prompt: {prompt!r}\n")
        logf.write(f"# Session ID: {session_id}  (resume={is_resume})\n")
        logf.write("# --- output ---\n")
        logf.flush()
        try:
            proc = subprocess.run(
                cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=timeout, env=env, text=True,
            )
            return (proc.returncode == 0, "")
        except subprocess.TimeoutExpired:
            logf.write(f"\n# --- TIMEOUT after {timeout}s ---\n")
            return (False, f"TIMEOUT after {timeout}s")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def _run_one(
    prompt_def: dict,
    run_idx: int,
    document_id: str,
    workspace_id: str,
    element_id: str,
    session_id: str,
    is_resume: bool,
    model: str,
    timeout: int,
    mcp_config: Path,
    auth,
    client: httpx.AsyncClient,
    log_dir: Path,
) -> RunResult:
    pre_mv = await _get_microversion(client, auth, document_id, workspace_id)
    pre_features = await _count_features(client, auth, document_id, workspace_id, element_id)

    full_prompt = (
        f"Use the onshape MCP tools. Target document_id={document_id}, "
        f"workspace_id={workspace_id}, element_id={element_id}.\n\n"
        f"Task: {prompt_def['prompt']}"
    )

    log_path = log_dir / f"{prompt_def['id']}_run{run_idx}.log"

    t0 = time.perf_counter()
    ok, err_msg = await asyncio.to_thread(
        _run_claude, full_prompt, mcp_config, model, timeout,
        session_id, log_path, is_resume,
    )
    t_claude = time.perf_counter() - t0

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
        error = "claude_cli_failed_or_timeout"
    elif post_mv == pre_mv:
        error = "no_microversion_change"

    print(
        f"  [{prompt_def['id']} run {run_idx}] "
        f"claude={t_claude:.1f}s total={t_total:.1f}s "
        f"Δfeat={feature_delta:+d} "
        f"{'OK' if success else 'FAIL: ' + (error or '')} "
        f"log={log_path.name}",
        flush=True,
    )

    return RunResult(
        prompt_id=prompt_def["id"],
        run_index=run_idx,
        wall_clock_s=t_total,
        claude_s=t_claude,
        success=success,
        feature_delta=feature_delta,
        error=error,
        log_path=str(log_path),
    )


def _families_in_order(selected: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group selected prompts by family_key, preserving prompt order within."""
    out: dict[str, list[dict]] = {}
    for p in selected:
        out.setdefault(p["family_key"], []).append(p)
    return list(out.items())


async def main_async(args) -> int:
    ak, sk = _load_onshape_keys()
    auth = httpx.BasicAuth(ak, sk)

    tmp_dir = Path("/tmp/3dpp_bench")
    tmp_dir.mkdir(exist_ok=True)
    mcp_config = _build_mcp_config(args.sse_url, tmp_dir)

    ts = time.strftime("%Y%m%d_%H%M%S")
    log_dir = Path("tests/reports") / f"runs_{ts}"
    log_dir.mkdir(parents=True, exist_ok=True)

    selected: list[dict] = list(PROMPTS)
    if args.only:
        wanted = set(args.only.split(","))
        selected = [p for p in PROMPTS if p["id"] in wanted]

    stats_by_prompt: dict[str, PromptStats] = {
        p["id"]: PromptStats(prompt_id=p["id"], label=p["label"]) for p in selected
    }

    # Each "family-run" is one independent design conversation:
    #   * fresh Part Studio
    #   * fresh Claude session_id
    #   * all prompts in the family run in sequence, sharing both
    # For independent prompts (P1, P2, P5) the family is a single prompt.
    # For chains (P3 → P4), the session built up by P3 is reused by P4.
    families = _families_in_order(selected)
    print(f"[setup] {len(families)} families × {args.runs} runs × prompts...", flush=True)

    async with httpx.AsyncClient(timeout=30) as client:
        for family_key, prompts in families:
            for run_idx in range(1, args.runs + 1):
                ps_name = f"bench_{family_key}_{ts}_r{run_idx}"
                element_id = await _create_part_studio(
                    client, auth, args.document_id, args.workspace_id, ps_name,
                )
                session_id = str(uuid.uuid4())
                print(
                    f"\n[family {family_key} run {run_idx}/{args.runs}] "
                    f"part_studio={element_id} session={session_id[:8]}…",
                    flush=True,
                )
                for prompt_def in prompts:
                    is_iter = bool(prompt_def.get("iterative_after"))
                    print(
                        f"  ({'iter' if is_iter else 'init'}) {prompt_def['id']}: "
                        f"{prompt_def['label']}",
                        flush=True,
                    )
                    result = await _run_one(
                        prompt_def, run_idx,
                        args.document_id, args.workspace_id, element_id,
                        session_id, is_iter,
                        args.model, args.timeout, mcp_config,
                        auth, client, log_dir,
                    )
                    stats_by_prompt[prompt_def["id"]].runs.append(result)

    _write_report(stats_by_prompt, args, log_dir)
    return 0


def _write_report(stats: dict[str, PromptStats], args, log_dir: Path) -> None:
    report_dir = Path("tests/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = report_dir / f"benchmark_{ts}.md"

    lines = [
        f"# Benchmark v2 — Jarvis Onshape MCP path",
        "",
        f"**When:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**SSE endpoint:** `{args.sse_url}`",
        f"**Model:** `{args.model}`",
        f"**Runs per prompt:** {args.runs} (iterative prompts capped at 1 run)",
        f"**Timeout:** {args.timeout}s per claude invocation",
        f"**Document:** `{args.document_id}` workspace `{args.workspace_id}`",
        f"**Per-run subprocess logs:** `{log_dir}/`",
        "",
        "Improvements over v1:",
        "- Default 600s timeout (was 240s) — complex prompts on Sonnet "
        "legitimately needed 200+s.",
        "- Fresh Part Studio per non-iterative run; iterative prompts "
        "(P4) share Part Studio + Claude session with their predecessor "
        "(P3) via `--session-id <uuid>`. Models the realistic "
        "interactive case.",
        "- Per-run subprocess logs in `tests/reports/runs_<ts>/`.",
        "",
        "## Results",
        "",
        "| Prompt | Successes | Median wall (s) | p95 (s) | Median Δfeatures |",
        "|--------|----------:|----------------:|--------:|-----------------:|",
    ]
    for pid, s in stats.items():
        ok_ratio = f"{len(s.successful)}/{len(s.runs)}"
        med = f"{s.median_s:.2f}" if s.median_s is not None else "—"
        p95 = f"{s.p95_s:.2f}" if s.p95_s is not None else "—"
        deltas = [r.feature_delta for r in s.successful]
        feat_med = statistics.median(deltas) if deltas else "—"
        lines.append(f"| {s.label[:38]} | {ok_ratio} | {med} | {p95} | {feat_med} |")

    lines += [
        "",
        "## Historical baseline — legacy CadQuery iframe path",
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
        "## Per-run details",
        "",
        "| Prompt | Run | Wall (s) | Claude (s) | Δfeat | Outcome | Log |",
        "|--------|----:|---------:|-----------:|------:|---------|-----|",
    ]
    for s in stats.values():
        for r in s.runs:
            outcome = "OK" if r.success else (r.error or "FAIL")
            log_name = Path(r.log_path).name if r.log_path else "—"
            lines.append(
                f"| {r.prompt_id} | {r.run_index} | {r.wall_clock_s:.1f} | "
                f"{r.claude_s:.1f} | {r.feature_delta:+d} | {outcome} | "
                f"`{log_name}` |"
            )

    out_path.write_text("\n".join(lines) + "\n")
    print(f"\nReport written to {out_path}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--document-id", required=True)
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--sse-url", default="http://127.0.0.1:3000/sse",
                    help="Jarvis MCP SSE URL.")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--only", help="Comma-separated subset of prompt IDs")
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
