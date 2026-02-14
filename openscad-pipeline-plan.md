# AI -> 3D Print Pipeline: Skills Development Plan for Claude CLI

## Objective

Reproduce and surpass the Gemini Deep Think pipeline for generating functional, 3D-printable OpenSCAD code, implemented as a system of skills + MCP server for Claude Code CLI (Opus).

---

## System Architecture

```
+-------------------------------------------------------------+
|                    CLAUDE CODE CLI                            |
|                                                              |
|  +----------+  +----------+  +----------+  +---------+      |
|  | Skill 1  |  | Skill 2  |  | Skill 3  |  | Skill 4 |     |
|  | Spatial   |->| OpenSCAD |->| Validate |->| Export  |     |
|  | Reasoning |  | CodeGen  |  | & Fix    |  | & Slice |     |
|  +----------+  +----------+  +----------+  +---------+      |
|       ^                                         |            |
|  +----------+                              +---------+       |
|  | Skill 5  |                              | MCP     |       |
|  | Image    |                              | Server  |       |
|  | Analyze  |                              |OpenSCAD |       |
|  +----------+                              +---------+       |
+-------------------------------------------------------------+
```

---

## Development Plan: 6 Skills + 1 MCP Server

### PHASE 1 — Foundations (Skills 1-2)

#### Skill 1: `spatial-reasoning` — Structured Spatial Reasoning
**Purpose:** Force Claude to reason step-by-step about 3D geometry before writing code.

**Key content:**
- "Spatial thinking" template with explicit coordinates
- CSG (Constructive Solid Geometry) decomposition into atomic steps
- Pre-code dimensional validation checklist
- Catalog of OpenSCAD primitives and boolean operations
- Axis orientation rules (Z-up for 3D printing)

**Deliverable:** `skills/spatial-reasoning/SKILL.md`

---

#### Skill 2: `openscad-codegen` — OpenSCAD Code Generation
**Purpose:** Generate parametric, clean, and printable OpenSCAD code.

**Key content:**
- Library of OpenSCAD patterns (holes, threads, snap-fit, walls, ribs)
- Code rules: mandatory parametric variables, no magic numbers
- Structured template: parameter header -> modules -> assembly -> render
- FDM printing constraints (minimum wall thickness, overhang angles, bridging)
- Standard tolerances for fits (press-fit, slip-fit, clearance)
- `$fn` rules for curve quality vs render time
- Anti-patterns to avoid (unrolled loops, direct mesh, unsupported loft)

**Deliverable:** `skills/openscad-codegen/SKILL.md` + `skills/openscad-codegen/templates/`

---

### PHASE 2 — Validation (Skill 3 + MCP Server)

#### Skill 3: `openscad-validate` — Iterative Validation and Correction
**Purpose:** Automatic loop of compilation, error analysis, and fix.

**Key content:**
- Workflow: generate -> compile -> analyze stderr -> fix -> recompile
- Parsing common OpenSCAD errors and fix strategies
- Manifold validation (closed mesh, no self-intersection)
- Output dimension check (reasonable bounding box)
- Max 5 automatic fix iterations, then escalation to user

**Deliverable:** `skills/openscad-validate/SKILL.md`

---

#### MCP Server: `openscad-mcp` — OpenSCAD CLI Bridge
**Purpose:** Give Claude direct access to OpenSCAD via MCP.

**Exposed tools:**
```
openscad.render     -> Compile .scad -> .stl + error log
openscad.preview    -> Generate PNG preview of the model
openscad.validate   -> Manifold check + bounding box
openscad.export     -> Export STL/3MF/AMF
openscad.version    -> Version info and capabilities
```

**Deliverable:** `mcp-openscad-server/` (Node.js or Python)

---

### PHASE 3 — Advanced Inputs (Skills 4-5)

#### Skill 4: `image-to-3d` — From Image/Sketch to Model
**Purpose:** Analyze images (photos, sketches, technical drawings) and extract geometry.

**Key content:**
- Image analysis prompt: identify shapes, relative dimensions, symmetries
- Workflow sketch -> structured description -> OpenSCAD
- Dimension estimation from reference objects in the image
- Multi-view handling (front, side, top)
- Template for visual reverse-engineering

**Deliverable:** `skills/image-to-3d/SKILL.md`

---

#### Skill 5: `print-profiles` — Print Profiles and Materials
**Purpose:** Adapt the design to material and printer constraints.

**Key content:**
- Materials database (PLA, PETG, ABS, ASA, PC, Nylon, TPU, composites)
- Per-material constraints: temp, shrinkage, anisotropy, layer adhesion
- Common printer profiles (Bambu, Prusa, Ender, Voron)
- Design rules per material (e.g., PC requires generous fillets)
- Tullomer/PC wrapping parameters (specific to your workflow)

**Deliverable:** `skills/print-profiles/SKILL.md` + `skills/print-profiles/materials.json`

---

### PHASE 4 — Orchestration (Skill 6)

#### Skill 6: `3d-print-orchestrator` — Complete Pipeline
**Purpose:** Master skill that orchestrates all others in sequence.

**Orchestrated workflow:**
```
1. Receive request (text and/or image)
2. -> [image-to-3d] if an image is present
3. -> [spatial-reasoning] geometric decomposition
4. -> [print-profiles] select material constraints
5. -> [openscad-codegen] generate parametric code
6. -> [openscad-validate] compile + fix loop via MCP
7. -> Final STL export + report
```

**Deliverable:** `skills/3d-print-orchestrator/SKILL.md`

---

## Final Directory Structure

```
~/.claude/skills/
+-- spatial-reasoning/
|   +-- SKILL.md
+-- openscad-codegen/
|   +-- SKILL.md
|   +-- templates/
|       +-- enclosure.scad
|       +-- bracket.scad
|       +-- snap-fit.scad
|       +-- parametric-box.scad
+-- openscad-validate/
|   +-- SKILL.md
+-- image-to-3d/
|   +-- SKILL.md
+-- print-profiles/
|   +-- SKILL.md
|   +-- materials.json
+-- 3d-print-orchestrator/
    +-- SKILL.md

~/.claude/mcp-servers/
+-- openscad-mcp/
    +-- package.json
    +-- src/
    |   +-- index.ts
    +-- README.md
```

---

## Implementation Order and Dependencies

```
Phase 1 (parallel):    Skill 1 + Skill 2          [no dependencies]
Phase 2 (sequential):  MCP Server -> Skill 3       [depends on MCP]
Phase 3 (parallel):    Skill 4 + Skill 5           [no dependencies]
Phase 4:               Skill 6                      [depends on all]
```

**Estimated time:** ~2-3 intensive Claude CLI sessions to complete everything.

---

## Validation Test Cases

| # | Test | Complexity | Skills Tested |
|---|------|------------|---------------|
| 1 | Parametric box with lid | Low | 1, 2, 3 |
| 2 | Phone holder | Medium | 1, 2, 3, 5 |
| 3 | Arduino Uno enclosure | Medium | 1, 2, 3, 5 |
| 4 | From photo of broken part -> replacement | High | 1, 2, 3, 4 |
| 5 | Composite bracket for 80C (Tullomer/PC) | High | 1, 2, 3, 5 |
| 6 | From hand sketch -> functional part | High | All |
