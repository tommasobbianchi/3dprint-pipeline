# Migration: CadQuery iframe → Jarvis Onshape MCP

## Why

The old iframe extension generated CadQuery code, executed it locally, and
imported the resulting STEP file into Onshape via the Translations API +
Derived feature. Wall-clock latency: 25–90 s. The Derived-feature step was
fragile (last attempt at 2026-03-10 returned `featureStatus=ERROR`), the
service was using the server's Claude subscription (not the user's), and
every prompt spawned a fresh `claude --print` subprocess (no iterative
context).

Jarvis Onshape MCP drives Onshape directly via REST: each natural-language
turn becomes 1–3 MCP tool calls (`create_sketch_*`, `create_extrude`,
`create_fillet`, …). No CadQuery, no STEP roundtrip, no Translation poll.
Iterative edits keep the same Claude session, so context is preserved.

## What changed

| Component | Before | After |
|-----------|--------|-------|
| Chat surface | Iframe in Onshape, FastAPI backend | Claude Code on user's laptop |
| Auth (Claude) | Server's subscription (subprocess) | User's `claude login` (Max/Pro) |
| Auth (Onshape) | API keys on nativedev (single set) | Per-user keys via systemd template |
| Geometry path | CadQuery → STEP → Translation API → Derived | Direct Onshape REST via MCP |
| Network | iframe POST → backend → cloud | Claude Code → SSE on nativedev → cloud |
| Latency p50 | 25–40 s | ~5–8 s (estimated, see Phase 5 benchmark) |
| Iterative edits | Re-runs full pipeline each turn | Same Claude session, ~1.5 s/turn |

## Rollout

1. **Phase 1 — server (DONE)**
   - `~/projects/jarvis-onshape-mcp/` v1.2.0
   - `/etc/systemd/system/onshape-mcp@.service` (canonical: `onshape-extension/deploy/`)
   - `~/.config/onshape-mcp/jarvis.env` (mode 600)
   - `tailscale serve --https=10001 → 127.0.0.1:3000`

2. **Phase 2 — client docs (DONE)**
   - See `CLIENT-SETUP.md`.

3. **Phase 3 — skill consolidation (PENDING)**
   - Move CadQuery/OpenSCAD skills to `skills/_legacy/`.
   - Replace `3d-print-orchestrator/` with `onshape-design-assistant/`.
   - Update `CLAUDE.md` cardinal rules.

4. **Phase 4 — deprecate iframe (PENDING)**
   - `systemctl disable --now onshape-cadgen`.
   - Move `onshape-extension/{backend,frontend}` → `onshape-extension/legacy/`.

5. **Phase 5 — benchmark (PENDING)**
   - `tests/benchmark_onshape_mcp.py` — 5 prompts × 5 runs, A/B vs legacy.

## Rollback plan

The iframe extension is **not deleted**, only deprecated:

```bash
# Re-enable the legacy iframe
sudo systemctl enable --now onshape-cadgen
# Disable the new MCP path
sudo systemctl disable --now onshape-mcp@tommaso
tailscale serve --https=10001 off
```

Both paths can coexist on the same nativedev (different ports: 8420 iframe,
3000 MCP). Disable only what's blocking.

## Why Tailscale serve, not Funnel

The MCP server has no built-in authentication. Funnel would expose it
publicly to the internet. Tailscale serve restricts access to authenticated
tailnet members — the user's laptops, no one else.
