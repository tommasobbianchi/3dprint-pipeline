---
name: 3d-print-orchestrator
description: Central orchestrator for AI-powered 3D print pipelines. Receives natural language requests (text and/or images), coordinates specialized skills (spatial reasoning, CadQuery codegen, validation, material selection), and produces print-ready STEP + STL output. Use when building end-to-end 3D printing workflows from natural language descriptions.
license: MIT
metadata:
  author: tommasobbianchi
  version: "1.0.0"
---

# SKILL: 3d-print-orchestrator — 3D Print Pipeline Orchestrator

## Identity
Central orchestrator of the 3D Print pipeline. Receives requests in natural language
(text and/or images), coordinates all specialized skills, and produces print-ready output.

---

## 1. Complete Workflow

```
INPUT (text / image / combo)
|
+-- [if image attached]
|   +-- skills/image-to-3d/SKILL.md
|      -> Input classification (sketch/photo/technical drawing/screenshot/product)
|      -> Structured specification (shapes, dimensions, features, suggested material)
|
+-- [if material specified or to be selected]
|   +-- skills/print-profiles/SKILL.md
|      -> Material selection by use case
|      -> Constraints: wall_min, shrinkage, chamber, drying, nozzle
|      -> Printer profile and compatibility
|
+-- skills/spatial-reasoning/SKILL.md
|   -> Phase 1: Functional decomposition
|   -> Phase 2: Modeling plan (primitives, booleans, order)
|   -> Phase 3: DFM check (thicknesses, overhang, supports, orientation)
|   -> Phase 4: Coordinates and final dimensions
|
+-- skills/cadquery-codegen/SKILL.md
|   -> Parametric Python script (mandatory template)
|   -> All dimensions in commented variables [mm]
|   -> Separate functions: make_body(), make_features(), make_assembly()
|   -> Export STEP + STL
|
+-- skills/cadquery-validate/SKILL.md
|   -> Python script execution
|   -> BREP validation (bounding box, volume, fill ratio)
|   -> Automatic fix loop (max 5 attempts, 20-error catalog)
|   -> Final export .step + .stl
|
+-- OUTPUT
   -> Script .py (parametric, commented, standalone)
   -> File .step (importable in Onshape/Fusion360/FreeCAD)
   -> File .stl (for slicer: Bambu Studio, PrusaSlicer, OrcaSlicer)
   -> Complete report (see section 4)
```

### 1.1 Orchestration Rules

1. **Mandatory order** — Phases must be executed in the indicated order. Do not skip phases.
2. **Reasoning BEFORE code** — Never write CadQuery without completing spatial-reasoning.
3. **One material at a time** — If the user doesn't specify, suggest a material and ask for confirmation.
4. **Material constraints -> code** — Constraints from print-profiles (wall_min, fillet) MUST be applied in CadQuery code.
5. **Mandatory validation** — Never deliver unexecuted code. Always pass through cadquery-validate.
6. **Automatic fix** — If validation fails, the fix loop in cadquery-validate handles up to 5 attempts.
7. **Complete output** — Every delivery includes .py + .step + .stl + report.

### 1.2 Error Handling Between Phases

```
ERROR in a phase
|
+-- image-to-3d fails (unreadable/ambiguous image)
|   -> Ask the user: "Can you describe the part in words?"
|   -> Proceed with text input
|
+-- print-profiles: material not compatible with printer
|   -> Show compatibility matrix
|   -> Suggest alternative
|
+-- spatial-reasoning: geometry too complex
|   -> Break into sub-assemblies
|   -> Generate separate parts, then assemble
|
+-- cadquery-codegen: pattern not covered by templates
|   -> Generate custom code following the mandatory template
|   -> Reference the 6 templates as a base
|
+-- cadquery-validate: 5 attempts exhausted
    -> Report all errors to the user
    -> Suggest geometric simplification
    -> Never deliver non-working code
```

---

## 2. Quick Commands

Shortcuts for frequent requests. Each command triggers the full workflow
but with pre-set parameters.

| Command | Description | Base template | Example |
|---|---|---|---|
| `/box WxDxH [material]` | Parametric box with lid | `parametric_box.py` | `/box 80x60x40 PETG` |
| `/bracket [material]` | L-bracket with gusset | `bracket_l.py` | `/bracket PC` |
| `/enclosure BOARD [material]` | PCB enclosure | `enclosure.py` | `/enclosure "Arduino Uno" PETG` |
| `/snap` | Snap-fit demo module | `snap_fit.py` | `/snap` |
| `/thread M[n]` | Heat insert hole | `threaded_insert.py` | `/thread M3` |
| `/hinge [material]` | Pin hinge | `hinge.py` | `/hinge PA12` |
| `/validate FILE` | Validate and export existing script | — | `/validate enclosure.py` |
| `/export FILE` | Export STEP+STL from script | — | `/export enclosure.py` |
| `/material MAT` | Show material constraints and properties | — | `/material PETG` |
| `/sketch` | Analyze attached image | — | `/sketch` (with image) |

### 2.1 Command Parsing

```
COMMAND RECEIVED
|
+-- Starts with "/"?
|   +-- Match with known command -> Execute with parameters
|   +-- No match -> "Unknown command. Available commands: ..."
|
+-- Free text?
    +-- Contains image -> image-to-3d phase -> full workflow
    +-- Contains explicit dimensions -> spatial-reasoning -> workflow
    +-- Generic description -> Ask for details (section 3 interactive mode)
```

---

## 3. Interactive Mode

When information is insufficient, ask in a structured way.

### 3.1 Minimum Required Information

| Information | Required | Default if not provided |
|---|---|---|
| Part type | YES | — (always ask) |
| Main dimensions | YES | — (always ask) |
| Material | NO | PLA |
| Wall thickness | NO | From material (wall_min) |
| Fillet/rounds | NO | 1.0 mm |
| Mounting holes | NO | None |
| Openings | NO | None |
| Printer | NO | Generic (250x250x250mm) |

### 3.2 Structured Questions

When information is missing, ask with precise format:

```
To proceed I need:
1. **Dimensions** — Width x Depth x Height in mm?
2. **Material** — Which material? (PLA, PETG, ABS, ASA, PC, PA, TPU...)
3. **Mounting holes** — Need holes? If yes: diameter, positions, type (through/insert)?
4. **Openings** — Need openings on sides? If yes: dimensions and position?
```

### 3.3 Interaction Rules

1. **Ask everything at once** — Don't ask one question at a time. Group them.
2. **Propose defaults** — "If not specified, I'll use PLA with 2mm wall."
3. **Confirm critical dimensions** — For PCB enclosures, always confirm hole positions.
4. **Don't guess material for mechanical parts** — Always ask for structural parts.

---

## 4. Standard Output

Every completed request produces this output.

### 4.1 Generated Files

| File | Format | Purpose |
|---|---|---|
| `{name}.py` | Python | Parametric CadQuery script, standalone, executable |
| `{name}.step` | STEP AP214 | Import in CAD (Onshape, Fusion360, FreeCAD, SolidWorks) |
| `{name}.stl` | Binary STL | Import in slicer (Bambu Studio, PrusaSlicer, OrcaSlicer) |
| `{name}_report.txt` | Text | Complete report (optional, printed to console) |

For multi-part assemblies:

| File | Purpose |
|---|---|
| `{name}_body.step/.stl` | Main body |
| `{name}_lid.step/.stl` | Lid (if present) |
| `{name}_assembly.step` | Complete assembly (color per part) |

### 4.2 Complete Report

After every delivery, ALWAYS print:

```
===============================================
  REPORT — {COMPONENT NAME}
===============================================

OK Python execution: OK (attempt N/5)
OK BREP Shape: Valid

Geometry:
   Bounding box: {X:.1f} x {Y:.1f} x {Z:.1f} mm
   Volume:       {vol:,.0f} mm3 ({vol/1000:.1f} cm3)
   Surface area: {area:,.0f} mm2

Print:
   Material:       {material}
   Estimated wt:   {weight:.1f}g (infill {infill}%)
   Estimated time:  ~{hours}h {min}min
   Material cost:  ~EUR {cost:.2f}

Printer:
   Compatible:     {compatible printer list}
   Print volume:   {check OK or WARNING}
   Enclosed:       {required/not required}

Print orientation:
   Z-up axis:      {orientation description}
   Supports:       {needed/not needed}
   Slicer notes:   {any notes}

Exported files:
   {list of .py + .step + .stl files}

===============================================
```

### 4.3 Report Calculations

```python
import json, os

# Load materials
mat_path = os.path.join(os.path.dirname(__file__), "..", "print-profiles", "materials.json")
with open(mat_path) as f:
    MATERIALS = json.load(f)

def report(result, material="PLA", infill_pct=20, layer_h=0.2):
    """Generates complete report for a CadQuery result."""
    bb = result.val().BoundingBox()
    vol_mm3 = result.val().Volume()
    vol_cm3 = vol_mm3 / 1000

    mat = MATERIALS[material]
    density = mat["density_g_cm3"]
    factor = 0.3 + 0.7 * (infill_pct / 100)
    weight_g = vol_cm3 * density * factor

    # Time: approximation based on volume
    speed_cm3h = 20  # [cm3/h] FDM average
    time_h = (vol_cm3 / speed_cm3h) * 1.3  # 30% overhead
    hours = int(time_h)
    minutes = int((time_h - hours) * 60)

    # Material cost (EUR/kg average)
    PRICES = {"PLA": 20, "PETG": 22, "ABS": 22, "ASA": 28,
              "PC": 35, "PA6": 40, "PA12": 45, "TPU_85A": 35,
              "TPU_95A": 30, "PLA-CF": 35, "PETG-CF": 38,
              "PC-CF": 55, "PA-CF": 60, "Tullomer": 50,
              "PVA": 45, "HIPS": 22}
    cost = weight_g / 1000 * PRICES.get(material, 25)

    print(f"BB: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"Volume: {vol_mm3:,.0f} mm3 ({vol_cm3:.1f} cm3)")
    print(f"Weight: {weight_g:.1f}g ({material}, {infill_pct}% infill)")
    print(f"Time: ~{hours}h {minutes}min")
    print(f"Material cost: ~EUR {cost:.2f}")
```

---

## 5. Integration with CadQuery Templates

The 6 templates in `skills/cadquery-codegen/templates/` are the starting point for known categories.

| User request | Template | Typical customizations |
|---|---|---|
| Box, container, case | `parametric_box.py` | Dimensions, internal dividers, lid |
| Bracket, mount, angle | `bracket_l.py` | Arm dimensions, holes, gusset |
| PCB enclosure, electronic case | `enclosure.py` | PCB dimensions, standoffs, openings, ventilation |
| Clip, hook, snap closure | `snap_fit.py` | Hook dimensions, deflection, clearance |
| Threaded hole, heat insert | `threaded_insert.py` | Size M2-M8, depth, pattern |
| Hinge, pin, articulation | `hinge.py` | Width, knuckle count, pin diameter |

### 5.1 When NOT to Use a Template

- Fully custom part -> Generate from scratch following CLAUDE.md structural template
- Combination of patterns -> Combine elements from different templates
- Complex assembly -> Break into parts, each with its own pattern

---

## 6. Detailed Phases — What to Do in Each Phase

### 6.1 image-to-3d Phase (only if image attached)

1. Classify input type (A-E)
2. Extract shapes, dimensions, features
3. Identify suggested material
4. Produce structured specification
5. If dimensions missing -> ask the user

### 6.2 print-profiles Phase

1. Load `materials.json`
2. Select material for use case (or use the requested one)
3. Extract constraints: `wall_min_mm`, `shrinkage_pct`, `chamber_required`
4. Verify printer compatibility (if specified)
5. Prepare parameters for CadQuery code

### 6.3 spatial-reasoning Phase

1. **Functional decomposition** — List components and functions
2. **Modeling plan** — Primitives, boolean operation order, fillet order
3. **DFM check** — Thicknesses >= wall_min, overhang < 45°, print orientation
4. **Final coordinates** — Table with all dimensions and positions

**Critical rule:** Fillet on external vertical edges (`edges("|Z")`) must be applied
BEFORE boolean operations (cut for cavities, union for standoffs). See memory #55.

### 6.4 cadquery-codegen Phase

1. Choose base template (if applicable)
2. Customize parameters
3. Structure: header -> parameters -> construction -> export
4. Apply material constraints (wall_min, fillet)
5. Generate complete standalone Python script

### 6.5 cadquery-validate Phase

1. Execute the Python script
2. Verify: no errors, valid BB, volume > 0
3. If error -> apply fix from catalog (max 5 attempts)
4. Export .step + .stl
5. Generate report

---

## 7. Request Examples and Routing

| User request | Phases activated | Template |
|---|---|---|
| "Create a box 80x60x40 in PLA" | profiles -> spatial -> codegen -> validate | `parametric_box.py` |
| [image of a bracket] | image-to-3d -> profiles -> spatial -> codegen -> validate | `bracket_l.py` |
| "Enclosure for Raspberry Pi 4" | profiles -> spatial -> codegen -> validate | `enclosure.py` |
| `/box 100x80x50 PETG` | profiles -> spatial -> codegen -> validate | `parametric_box.py` |
| `/validate my_part.py` | validate (only) | — |
| `/material ASA` | profiles (only) | — |
| "Create a part that can withstand 100°C" | profiles (selection) -> interactive -> spatial -> codegen -> validate | custom |

---

## 8. Pre-Delivery Checklist

Before delivering to the user, verify ALL these points:

- [ ] Spatial reasoning completed (4 documented phases)
- [ ] Material constraints applied (wall_min, fillet, shrinkage)
- [ ] Python script runs without errors
- [ ] Bounding box dimensions > 0.1mm and < 500mm on all axes
- [ ] Volume > 0 mm3
- [ ] .step file exported and verified
- [ ] .stl file exported and verified
- [ ] No `try: except: pass` in code
- [ ] All parameters with `[mm]` or `[deg]` comment
- [ ] No magic numbers
- [ ] Complete report printed
- [ ] Print orientation indicated (Z-up)
