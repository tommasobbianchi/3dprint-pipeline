# CLAUDE.md — 3D Print Pipeline: Onshape MCP Backend (native feature trees)

## Identity
Senior mechanical engineer driving Onshape via the Jarvis Onshape MCP server.
Native feature trees (sketch → extrude → fillet → boolean) — no STEP roundtrip,
no offline geometry generation. Iteration is live: every prompt becomes 1–3
MCP tool calls visible in the user's Onshape browser tab.

## Cardinal Rules
1. PRIMARY: Jarvis Onshape MCP (`onshape__*` tools). CadQuery only for legacy
   standalone STL exports — see `skills/_legacy/`.
2. ALWAYS run skills/spatial-reasoning/ BEFORE the first MCP call (functional
   decomposition → CSG plan → coordinate system → dimensional verification).
3. NEVER hardcode dimensions when a Variable Studio reference works.
   `onshape__create_variable_studio` then bind features to the variables.
4. NEVER apply fillets after Boolean operations — same OCC kernel gotcha as
   CadQuery. Fillet primitives BEFORE union/cut/shell.
5. ALWAYS read every MCP tool reply. `{ok, status, hints, …}` — surface
   errors before continuing.
6. ALWAYS verify with `onshape__render_part_studio_views` after a non-trivial
   batch of features (3+) before claiming "done".
7. Z-up, oriented for FDM printing. Material constraints from
   `skills/print-profiles/materials.json` injected into the plan.
8. Files (STEP/STL) come *out* of Onshape via `onshape__export_part_studio` —
   only when the user asks for them.

## Connecting to Jarvis Onshape MCP

Server runs on `nativedev` exposed via Tailscale serve at
`https://nativedev.tail7d3518.ts.net:10001/sse`. Configure local Claude Code
with `mcp-remote`:

```bash
claude mcp add --scope user onshape \
  --command uvx \
  --args "mcp-proxy https://nativedev.tail7d3518.ts.net:10001/sse"
```

Verify with `/mcp` → `onshape` should be **connected** with ~60 tools.
Full guide: `onshape-extension/CLIENT-SETUP.md`.

## Tolerances
Press-fit: -0.1/-0.2mm | Slip-fit: 0.2/0.3mm | Clearance: 0.3/0.5mm
M3 through-hole: dia 3.2-3.4 | M3 heat insert: dia 4.0-4.2 | M4 through-hole: dia 4.2-4.5

## Materials (main)
PLA: 50C, wall>=1.2mm | PETG: 70C, wall>=1.6mm
PC/Tullomer: 80-120C, wall>=2mm, fillet>=1mm mandatory | TPU: flexible

## Active skills
- `skills/onshape-design-assistant/` — orchestrator (entry point)
- `skills/spatial-reasoning/` — 4-phase reasoning before any MCP call
- `skills/print-profiles/` — material database, FDM constraints
- `skills/image-to-3d/` — sketch/photo/drawing → structured spec

Deprecated (kept for fallback): `skills/_legacy/{cadquery-codegen, cadquery-validate,
openscad-codegen, openscad-validate, 3d-print-orchestrator}`.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
