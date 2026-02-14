# 3D Print Pipeline for Claude Code

**AI-powered 3D model generation pipeline — from natural language to print-ready STEP + STL files.**

A complete system of Claude Code skills and MCP servers that turns text descriptions (or images) into parametric, validated, FDM-printable 3D models using CadQuery.

## Features

- **Natural language to 3D model** — Describe what you need, get a print-ready file
- **Full parametric output** — Every dimension is a named variable with `[mm]` units
- **Dual export** — STEP (for CAD import) + STL (for slicer) on every run
- **Automatic validation** — Up to 5 fix attempts with a 20-error diagnosis catalog
- **15 materials database** — PLA to PA-CF, with printer compatibility matrix
- **Image input** — Analyze photos, sketches, or technical drawings
- **Spatial reasoning first** — Mandatory 4-phase geometric reasoning before any code

## Architecture

```
INPUT (text / image / combo)
|
+-- [image-to-3d]         Image analysis & spec extraction
+-- [print-profiles]      Material selection & constraints
+-- [spatial-reasoning]    4-phase geometric reasoning
+-- [cadquery-codegen]     Parametric Python code generation
+-- [cadquery-validate]    Execution, validation & auto-fix loop
|
OUTPUT: .py + .step + .stl + report
```

## Skills

| Skill | Description |
|-------|-------------|
| `spatial-reasoning` | Mandatory 4-phase spatial reasoning protocol |
| `cadquery-codegen` | CadQuery code generation with 6 templates |
| `cadquery-validate` | Validation loop with 20-error fix catalog |
| `image-to-3d` | Image/sketch analysis to structured specs |
| `print-profiles` | 15 materials + 9 printers database |
| `3d-print-orchestrator` | Master orchestrator for the full pipeline |

## MCP Servers

| Server | Description |
|--------|-------------|
| `mcp-cadquery-server` | CadQuery execution, validation & export |
| `mcp-openscad-server` | OpenSCAD compilation & preview (fallback) |

## Quick Start

### 1. Install as Claude Code skills

```bash
# Clone the repository
git clone https://github.com/tommasobbianchi/3dprint-pipeline.git
cd 3dprint-pipeline

# Start Claude Code
claude

# Load the orchestrator
> Read skills/3d-print-orchestrator/SKILL.md
```

### 2. Try a simple part

```
Create a box 80x60x40mm in PETG with a lid and snap-fit closure.
```

### 3. Quick commands

| Command | Description |
|---------|-------------|
| `/box 80x60x40 PETG` | Parametric box with lid |
| `/bracket PC` | L-bracket with ribs |
| `/enclosure "Arduino Uno" PETG` | PCB enclosure |
| `/snap` | Snap-fit demo module |
| `/thread M3` | Heat insert hole |
| `/material ASA` | Show material properties |
| `/validate script.py` | Validate existing script |

## Templates

Six ready-to-use parametric templates in `skills/cadquery-codegen/templates/`:

- `parametric_box.py` — Box with lid and snap-fit
- `bracket_l.py` — L-bracket with ribs and holes
- `enclosure.py` — PCB enclosure with standoffs
- `snap_fit.py` — Cantilever snap-fit module
- `threaded_insert.py` — M2-M5 heat insert bosses
- `hinge.py` — 2-part pin & knuckle hinge

All templates are standalone — run with `python3 template.py` to get STEP + STL output.

## Materials

15 materials with full specs in `skills/print-profiles/materials.json`:

PLA, PLA-CF, PETG, PETG-CF, ABS, ASA, PC, PC-CF, PA6, PA12, PA-CF, TPU 85A, TPU 95A, Tullomer, PVA, HIPS

Each material includes: service temperature, nozzle/bed temps, wall minimum, shrinkage, density, mechanical properties, printer requirements, and usage notes.

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.8+ with [CadQuery](https://cadquery.readthedocs.io/) installed
- Node.js 18+ (for MCP servers)

## Example Prompts

See [EXAMPLE-PROMPTS.md](EXAMPLE-PROMPTS.md) for 18 example prompts across 6 difficulty levels.

## License

MIT
