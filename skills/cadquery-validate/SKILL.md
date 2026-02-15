---
name: cadquery-validate
description: Automatic validation, diagnosis, and correction loop for CadQuery code. Runs up to 5 attempts to produce a valid BREP model with STEP + STL export. Use when validating or fixing CadQuery scripts, debugging 3D model generation errors, or ensuring export correctness.
license: MIT
metadata:
  author: tommasobbianchi
  version: "1.0.0"
---

# SKILL: cadquery-validate — CadQuery Validation and Automatic Fix

## Identity
Automatic validation, diagnosis, and correction loop for CadQuery code.
Runs up to 5 attempts to produce a valid BREP model with STEP+STL export.

---

## 1. Workflow — Automatic Fix Loop

```
for attempt in 1..5:
    result = run_python(code)

    if result.success:
        bb = bounding_box(result)
        vol = volume(result)
        n_solids = solid_count(result)

        if bb valid AND vol > 0 AND n_solids == 1:
            export(STEP + STL)
            print REPORT
            return SUCCESS
        elif n_solids > 1:
            code = fix_solid_alignment(code, result)
        else:
            code = fix_geometry(code, bb, vol)
    else:
        error = parse_traceback(result.stderr)
        fix = search_catalog(error)
        code = apply_fix(code, fix)

return FAILURE (after 5 attempts)
```

### 1.1 Loop Rules

1. **Max 5 iterations** — if the code doesn't work after 5 attempts, STOP and report all errors
2. **One fix at a time** — don't apply multiple fixes in the same attempt (confuses diagnosis)
3. **Preserve parameters** — never change user parameters unless they are the root cause
4. **Log every attempt** — track error, applied fix, result
5. **No blind try/except** — don't hide errors with `try: ... except: pass`

### 1.2 MCP Integration

```
IF MCP tool cadquery_validate is available:
    use cadquery_validate(python_code) -> { valid, errors, bounding_box, volume_mm3 }
    use cadquery_export(python_code, formats, output_dir) -> { files, bounding_box }
    use cadquery_info(python_code) -> { bounding_box, volume_mm3, surface_area_mm2 }
OTHERWISE:
    run `python3 script.py` via bash
    parse stdout for BB/volume, stderr for errors
```

---

## 2. CadQuery Error Catalog — Diagnosis and Fix

### 2.1 Kernel Errors (OpenCascade)

| # | Error (traceback) | Probable cause | Automatic fix |
|---|---|---|---|
| 1 | `StdFail_NotDone` in fillet/chamfer | Fillet radius > half of minimum thickness, or edge too short after boolean | Reduce radius to `min(radius, thickness/2 - 0.1)`. If still fails, use `NearestToPointSelector` for specific edges instead of broad selectors (`\|Z`, `\|Y`) |
| 2 | `StdFail_NotDone` in boolean (cut/union) | Tangent, coincident, or coplanar geometries | Offset one geometry by 0.01mm on an axis. Example: `translate((0.01, 0, 0))` |
| 3 | `BRep_API: not done` | Boolean between solids with degenerate intersection (edge-on-edge) | Slightly scale one operand: `* 1.001` or 0.01mm offset |
| 4 | `ShapeAnalysis_Wire: Wire is not closed` | Polyline/sketch not closed | Add `.close()` before `.extrude()` |
| 5 | `Shape is null` / `TopoDS_Shape is null` | Operation produces empty body (cut removes everything, extrude with height 0) | Verify that dimensions > 0, that cut doesn't exceed the body, that extrude has positive height |

### 2.2 CadQuery API Errors

| # | Error (traceback) | Probable cause | Automatic fix |
|---|---|---|---|
| 6 | `ValueError: No pending wires` | `.extrude()` without preceding 2D sketch | Add `.rect()`, `.circle()` or other sketch before `.extrude()` |
| 7 | `ValueError: Cannot resolve selector` | Ambiguous selector after boolean (e.g. `">Z"` with multiple faces at the same Z) | Use `.faces(sel).first().workplane()` or `NearestToPointSelector((x,y,z))` |
| 8 | `ValueError: negative or zero` in extrude | Negative extrusion value passed to `.extrude()` | Use `abs(value)` or switch to `.cutBlind(-value)` if intent was a pocket |
| 9 | `ValueError: Unknown color name` | CSS color name not supported by CadQuery | Replace with `cq.Color(r, g, b)` using float RGB 0.0-1.0 |
| 10 | `ModuleNotFoundError: No module named 'cadquery'` | CadQuery not installed in Python environment | Run `pip install cadquery` or check virtualenv |

### 2.3 Geometric Errors (post-execution)

| # | Condition | Probable cause | Automatic fix |
|---|---|---|---|
| 11 | Bounding box > 500mm on any axis | Scale error (units in inches or meters instead of mm) | If BB ~25.4x too large: divide by 25.4 (inches->mm). If BB ~1000x: divide by 1000 (m->mm) |
| 12 | Bounding box < 0.1mm on any axis | Degenerate part (flat 2D) or scale error | Verify all dimensions are in mm and > 0.5mm. If one axis is 0: missing extrusion |
| 13 | Volume = 0 mm3 | Body completely hollowed by cut, shell too thin, or non-solid shape | Verify that `wall > 0`, that shell doesn't hollow everything, that cut doesn't remove the entire body |
| 14 | Negative or NaN volume | Corrupted BREP shape | Rebuild geometry from scratch with simpler operations |
| 15 | Export failed (file not created) | `result` is not a valid CadQuery object, or path not writable | Verify that `result` is `cq.Workplane`, not an intermediate value. Verify the directory exists |
| 21 | `len(result.val().Solids()) > 1` | Multiple disconnected solids — features (ribs, bosses, gussets) not touching the main body. Common when XZ/YZ workplane extrusion direction is misunderstood, or `union()` of non-overlapping parts. | Review coordinate alignment: XZ workplane extrudes in **-Y** (not +Y). Verify all features are within the body's coordinate range. Use `result.val().Solids()` to identify which solid is smaller (the detached one), then fix its position coordinates. |

### 2.4 Pattern Errors (structural code)

| # | Detected pattern | Problem | Automatic fix |
|---|---|---|---|
| 16 | `.edges("\|Z").fillet()` after `.union()` or `.cut()` | Broad selector catches small edges created by boolean | Move fillet BEFORE booleans, or use `NearestToPointSelector` |
| 17 | `import numpy` / `from stl import` / `import trimesh` | Direct mesh instead of BREP modeling | Remove and rewrite with pure CadQuery |
| 18 | No `cq.exporters.export()` in code | Script exports nothing | Add STEP+STL export at the end of the script |
| 19 | `result` not defined at module level | Model not accessible for validation/export | Ensure `result = make_assembly()` is called at module level |
| 20 | `try: ... except: pass` around fillet/chamfer | Hides kernel errors | Remove try/except and apply the appropriate fix from the catalog |

---

## 3. Decision Tree — Fix Strategy

```
ERROR RECEIVED
|
+-- Contains "StdFail_NotDone"?
|   +-- Stack contains "fillet" or "chamfer"?
|   |   +-- Selector is "|Z", "|Y", "|X"? -> Move fillet BEFORE booleans (fix #16)
|   |   +-- Radius > min_thickness / 2? -> Reduce radius (fix #1)
|   |   +-- Otherwise -> Use NearestToPointSelector (fix #1 alternative)
|   +-- Stack contains "BRepAlgoAPI" / "boolean"?
|       +-- Offset 0.01mm on one operand (fix #2)
|
+-- Contains "Wire is not closed"?
|   +-- Add .close() (fix #4)
|
+-- Contains "No pending wires"?
|   +-- Add 2D sketch before extrude (fix #6)
|
+-- Contains "Cannot resolve selector"?
|   +-- Add .first() or use NearestToPointSelector (fix #7)
|
+-- Contains "negative or zero"?
|   +-- abs() or convert to cutBlind (fix #8)
|
+-- Contains "Unknown color name"?
|   +-- Replace with cq.Color(r, g, b) float (fix #9)
|
+-- Contains "Shape is null"?
|   +-- Verify dimensions and operations (fix #5)
|
+-- Contains "ModuleNotFoundError"?
|   +-- pip install cadquery (fix #10)
|
+-- No catalog match?
|   +-- Manually analyze traceback, apply specific fix
|
+-- Post-execution: len(result.val().Solids()) > 1?
    +-- Multiple disconnected solids detected (error #21)
    +-- Diagnose: print BB of each solid to identify detached feature
    +-- Most common cause: XZ workplane extrusion in -Y direction
    +-- Fix: align feature coordinates within body's coordinate range
```

---

## 4. Post-Validation — Formatted Report

After a successful validation, ALWAYS generate this report:

```
OK Python execution: OK (attempt N/5)
OK BREP Shape: Valid
OK Solid count: 1 (single connected solid)
OK Bounding box: {X:.1f} x {Y:.1f} x {Z:.1f} mm
Volume: {vol:,.0f} mm3 ({vol/1000:.1f} cm3)
Surface area: {area:,.0f} mm2
Estimated weight: {weight:.1f}g ({material}, {infill}% infill)
Estimated print time: ~{hours}h {min}min
Export: {name}.step + {name}.stl
```

### 4.1 Estimated Weight Calculation

```python
# Material densities [g/cm3]
DENSITY = {
    "PLA":  1.24,
    "PETG": 1.27,
    "ABS":  1.04,
    "ASA":  1.07,
    "PC":   1.20,
    "TPU":  1.21,
    "Nylon": 1.14,
}

# Weight = volume_cm3 * density * infill_factor
# infill_factor accounts for shell (2-3 perimeters ~0.8-1.2mm) + internal infill
# Approximation: shell 100% + core at infill %
# For small parts (< 30mm): almost all shell -> factor ~0.8-0.9
# For large parts (> 100mm): more infill -> factor = shell_fraction + (1-shell_fraction) * infill%

def estimated_weight(vol_mm3, material="PLA", infill_pct=20):
    vol_cm3 = vol_mm3 / 1000
    density = DENSITY.get(material, 1.24)
    factor = 0.3 + 0.7 * (infill_pct / 100)  # simple approximation
    return vol_cm3 * density * factor
```

### 4.2 Estimated Print Time Calculation

```python
# Approximation based on volume and height
# Average effective speed: ~15-25 cm3/h for standard FDM
# Layer height factor: 0.2mm standard, 0.1mm slow, 0.3mm fast

def estimated_print_time(vol_mm3, height_mm, layer_h=0.2, speed_cm3h=20):
    vol_cm3 = vol_mm3 / 1000
    n_layers = height_mm / layer_h
    time_h = vol_cm3 / speed_cm3h
    # Add overhead for moves, heating, retractions
    time_h *= 1.3
    hours = int(time_h)
    minutes = int((time_h - hours) * 60)
    return hours, minutes
```

---

## 5. Geometric Validations

### 5.1 Bounding Box Check

```python
bb = result.val().BoundingBox()

# Reasonable dimensions for FDM printing
assert bb.xlen > 0.1, "X axis degenerate (< 0.1mm)"
assert bb.ylen > 0.1, "Y axis degenerate (< 0.1mm)"
assert bb.zlen > 0.1, "Z axis degenerate (< 0.1mm)"
assert bb.xlen < 500, f"X axis too large ({bb.xlen:.0f}mm > 500mm)"
assert bb.ylen < 500, f"Y axis too large ({bb.ylen:.0f}mm > 500mm)"
assert bb.zlen < 500, f"Z axis too large ({bb.zlen:.0f}mm > 500mm)"
```

### 5.2 Volume Check

```python
vol = result.val().Volume()

assert vol > 0, "Volume = 0 (empty body or non-solid)"
assert vol < 1e9, f"Unrealistic volume ({vol:.0f}mm3 = {vol/1e6:.0f}L)"

# Check proportion (volume vs bounding box)
bb_vol = bb.xlen * bb.ylen * bb.zlen
fill_ratio = vol / bb_vol if bb_vol > 0 else 0
assert fill_ratio > 0.001, f"Fill ratio too low ({fill_ratio:.4f}) — possible degenerate shape"
```

### 5.4 Solid Count Check

```python
solids = result.val().Solids()
n_solids = len(solids)

assert n_solids == 1, f"ERROR #21: {n_solids} disconnected solids detected (expected 1)"

# If multiple solids, diagnose which is detached:
if n_solids > 1:
    for i, s in enumerate(solids):
        bb_s = s.BoundingBox()
        vol_s = s.Volume()
        print(f"  Solid {i}: BB {bb_s.xlen:.1f}x{bb_s.ylen:.1f}x{bb_s.zlen:.1f} mm, vol={vol_s:.0f} mm3")
    print("  -> The smallest solid is likely a detached feature. Fix its coordinates.")
```

**Common causes of disconnected solids:**
1. **XZ workplane extrusion direction**: `Workplane("XZ").extrude(d)` goes in -Y, not +Y. Features positioned at positive Y float in space.
2. **Union of non-touching parts**: `body.union(feature)` succeeds silently even when parts don't overlap, creating 2 separate solids inside a compound shape.
3. **Incorrect translate coordinates**: After computing feature positions, verify they fall within the body's bounding box range.

### 5.3 Printability Check

```python
# Minimum thicknesses for FDM
MIN_WALL = 0.8  # [mm] — below this the printer can't handle it

# Maximum height without supports
MAX_UNSUPPORTED = 300  # [mm]

# Warning (not error) if too tall
if bb.zlen > MAX_UNSUPPORTED:
    print(f"Warning: Height {bb.zlen:.0f}mm — may require supports or splitting")
```

---

## 6. Full Example — Fix Loop in Action

### Input: script with fillet too large

```python
"""Box with fillet — intentionally broken"""
import cadquery as cq

width  = 40.0   # [mm]
depth  = 30.0   # [mm]
height = 5.0    # [mm] — very thin!
fillet = 4.0    # [mm] — TOO LARGE: > height/2

result = (
    cq.Workplane("XY")
    .box(width, depth, height)
    .edges("|Z")
    .fillet(fillet)
)
```

### Attempt 1: ERROR
```
StdFail_NotDone: fillet radius (4.0) > half minimum dimension (2.5)
```

### Fix applied (catalog #1):
```python
# fillet reduced: min(4.0, 5.0/2 - 0.1) = 2.4
fillet = 2.4    # [mm] — reduced from 4.0 (was > height/2)
```

### Attempt 2: SUCCESS
```
OK Python execution: OK (attempt 2/5)
OK BREP Shape: Valid
OK Bounding box: 40.0 x 30.0 x 5.0 mm
Volume: 5,544 mm3 (5.5 cm3)
Export: box.step + box.stl
```

---

## 7. Pre-Delivery Checklist

Before declaring the model valid and delivering to the user:

- [ ] Python script runs without errors
- [ ] Bounding box dimensions > 0.1mm on all axes
- [ ] Bounding box dimensions < 500mm on all axes
- [ ] Volume > 0 mm3
- [ ] Fill ratio > 0.001 (volume / bb_volume)
- [ ] Single connected solid (`len(result.val().Solids()) == 1`) — no floating parts
- [ ] .step file exported and verified to exist
- [ ] .stl file exported and verified to exist
- [ ] No `try: except: pass` in final code
- [ ] All parameters with `[mm]` or `[deg]` comment
- [ ] No magic numbers in code
- [ ] Post-validation report printed
