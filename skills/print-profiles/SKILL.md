---
name: print-profiles
description: FDM materials and process consultant for 3D printing. Selects optimal material for use case, applies geometric constraints to CadQuery design, estimates weight and time, and verifies printer compatibility. Use when choosing 3D printing materials, configuring slicer profiles, or checking design-for-manufacturing constraints.
license: MIT
metadata:
  author: tommasobbianchi
  version: "1.0.0"
---

# SKILL: print-profiles — Material Selection, Print Constraints, and Printer Profiles

## Identity
FDM materials and process consultant. Selects the optimal material for the use case,
applies geometric constraints to CadQuery design, estimates weight and time, and verifies printer compatibility.

---

## 1. Material Selection by Use Case

### 1.1 Decision Matrix

| Use case | Primary material | Alternative | Reason |
|---|---|---|---|
| Rapid prototype, no load | PLA | PLA-CF | Economical, easy, no special requirements |
| Indoor mechanical part | PETG | PA12 | Good strength/printability compromise |
| Outdoor mechanical part | ASA | PETG | UV-resistant, thermal resistance >85°C |
| High temperature (80-120°C) | PC | Tullomer | Excellent thermal resistance |
| High temperature + lightweight | PC-CF | PA-CF | Maximum stiffness and thermal resistance |
| Chemical resistance (solvents, oils) | PA6 | PA-CF | Nylon excels in chemical resistance |
| Flexible parts, gaskets | TPU 85A | TPU 95A | Elastomer, absorbs vibrations |
| Snap clips, living hinges | PA12 | PETG | Excellent fatigue, not brittle |
| Food-safe | PLA | Tullomer | Food contact certified |
| Gears, bushings | PA-CF | PA12 | Wear resistance + stiffness |
| Jigs, fixtures, tooling | PA-CF | PC-CF | Maximum mechanical strength |
| Outdoor electronic enclosure | ASA | PC | UV + thermal + chemical |
| Automotive/motorcycle structural parts | PC-CF | PA-CF | Stiffness, temperature, impact |
| Soluble supports (with PLA/PETG) | PVA | — | Water-soluble |
| Soluble supports (with ABS/ASA) | HIPS | — | Soluble in D-Limonene |

### 1.2 Decision Tree

```
USE CASE
|
+-- Service temperature > 80°C?
|   +-- Yes -> Need lightweight/stiffness?
|   |   +-- Yes -> PC-CF or PA-CF
|   |   +-- No -> PC or Tullomer
|   +-- No -> continue below
|
+-- Exposed to UV / outdoor?
|   +-- Yes -> ASA (or PETG if T < 70°C)
|   +-- No -> continue below
|
+-- Need flexibility?
|   +-- Yes -> TPU 85A (soft) or TPU 95A (semi-rigid)
|   +-- No -> continue below
|
+-- Chemical resistance critical?
|   +-- Yes -> PA6 or PA-CF
|   +-- No -> continue below
|
+-- Significant mechanical loads?
|   +-- Yes -> PETG (indoor) or ASA (outdoor) or PA-CF (extreme)
|   +-- No -> PLA (prototype) or PETG (production)
|
+-- Food-safe required?
    +-- Yes -> PLA or Tullomer
    +-- No -> select by temperature/load
```

### 1.3 Loading Materials Database

```python
import json, os

MATERIALS_PATH = os.path.join(os.path.dirname(__file__), "materials.json")

def load_materials():
    with open(MATERIALS_PATH) as f:
        return json.load(f)

def get_material(name):
    """Returns properties of a specific material."""
    materials = load_materials()
    key = name.upper().replace(" ", "_").replace("-", "_")
    # Exact or partial match
    if key in materials:
        return materials[key]
    for k, v in materials.items():
        if name.lower() in k.lower() or name.lower() in v.get("full_name", "").lower():
            return v
    return None
```

---

## 2. Applying Constraints to CadQuery Design

### 2.1 Wall Thickness Verification

Every material in `materials.json` has a `wall_min_mm` field. Before generating CadQuery code,
verify that all wall thicknesses are >= wall_min_mm of the selected material.

```
IF material.wall_min_mm > design_wall:
    WARNING: "Wall {design_wall}mm too thin for {material}.
             Minimum: {wall_min_mm}mm. Automatically increased."
    design_wall = material.wall_min_mm
```

**Rules by material:**

| Material | wall_min_mm | Reason |
|---|---|---|
| PLA | 1.0 | Brittle under 1mm |
| PETG | 1.2 | Stringing makes thin walls irregular |
| ABS / ASA | 1.2 | Warping creates stress on thin walls |
| PC / Tullomer | 1.6 – 2.0 | Shrinkage + interlayer stress require robust walls |
| PA6 / PA12 | 1.2 | High shrinkage, thin walls warp |
| PA-CF / PC-CF | 1.4 – 1.8 | Fibers require thickness to align |
| TPU 85A | 1.0 | Flexible, tolerates thin walls |
| TPU 95A | 1.2 | Semi-rigid |

### 2.2 Shrinkage Compensation

For high-shrinkage materials (ABS, PA6, PC), suggest dimensional compensation:

```python
def compensate_shrinkage(dimension_mm, material):
    """Compensates material shrinkage by scaling the dimension."""
    shrink_avg = (material["shrinkage_pct"]["min"] + material["shrinkage_pct"]["max"]) / 2 / 100
    return dimension_mm * (1 + shrink_avg)
```

**When to apply compensation:**

| Situation | Action |
|---|---|
| Tight tolerances (press-fit, interlocks) | ALWAYS compensate |
| Generic dimensions (enclosure, bracket) | DO NOT compensate (slicer compensates) |
| Screw holes | Compensate ONLY if critical diameter |
| Mating with metal parts | ALWAYS compensate |

**Average shrinkage table:**

| Material | Average shrinkage | Compensation per 100mm |
|---|---|---|
| PLA | 0.4% | +0.4mm |
| PETG | 0.45% | +0.45mm |
| ABS | 0.65% | +0.65mm |
| ASA | 0.55% | +0.55mm |
| PA6 | 1.1% | +1.1mm |
| PA12 | 0.75% | +0.75mm |
| PC | 0.65% | +0.65mm |
| Tullomer | 0.6% | +0.6mm |

### 2.3 Enclosed Chamber — Warnings

```
IF material.chamber_required == true:
    WARNING: "{material} requires an enclosed chamber.
             Compatible printers: Bambu X1C, Voron 2.4, Prusa XL (optional).
             NOT compatible printers: Bambu A1, Ender 3, Prusa MK4 (without enclosure)."
```

### 2.4 Drying — Warnings

```
IF material.drying_required == true:
    INFO: "{material} requires drying before printing.
           Temperature: {drying_temp_hours.temp_c}°C for {drying_temp_hours.hours}h.
           Use a drybox during printing for hygroscopic materials (PA, PVA)."
```

### 2.5 Hardened Steel Nozzle — Warnings

```
IF material name contains "CF":
    WARNING: "{material} contains abrasive fibers.
             Hardened steel nozzle MANDATORY.
             A brass nozzle will wear out in a few hours."
```

---

## 3. Estimation Formulas

### 3.1 Estimated Weight

```python
def estimated_weight(vol_mm3, material="PLA", infill_pct=20):
    """
    Estimates weight of the printed part.

    Formula: weight = volume_cm3 x density x infill_factor
    infill_factor = shell_fraction + (1 - shell_fraction) x (infill_pct / 100)

    Approximation: shell_fraction = 0.3 (average for typical FDM parts)
    For small parts (<30mm): shell_fraction ~ 0.6-0.8
    For large parts (>100mm): shell_fraction ~ 0.15-0.25
    """
    materials = load_materials()
    mat = materials.get(material, materials.get("PLA"))
    density = mat["density_g_cm3"]

    vol_cm3 = vol_mm3 / 1000.0
    factor = 0.3 + 0.7 * (infill_pct / 100.0)
    weight_g = vol_cm3 * density * factor

    return round(weight_g, 1)
```

### 3.2 Estimated Print Time

```python
def estimated_print_time(vol_mm3, height_mm, layer_h=0.2, nozzle_d=0.4,
                          speed_mm_s=60, overhead=1.3):
    """
    Estimates print time.

    Base formula: time_h = (volume_mm3 / (layer_h x nozzle_d x speed_mm_s)) / 3600
    Corrected with overhead factor (moves, retractions, heating).

    Default parameters: layer 0.2mm, nozzle 0.4mm, speed 60mm/s, overhead 30%.
    """
    # Effective volume rate [mm3/s]
    flow_rate = layer_h * nozzle_d * speed_mm_s

    # Base time [s]
    time_s = vol_mm3 / flow_rate

    # Overhead: non-print moves, heating, retractions, layer changes
    time_s *= overhead

    # Additional overhead for height (more layers = more layer changes and z-hop)
    n_layers = height_mm / layer_h
    time_s += n_layers * 1.5  # ~1.5s per layer change

    time_h = time_s / 3600.0
    hours = int(time_h)
    minutes = int((time_h - hours) * 60)

    return hours, minutes
```

### 3.3 Estimated Filament Cost

```python
# Average filament prices [EUR/kg] — 2026 update
FILAMENT_PRICES = {
    "PLA":      20,   "PLA-CF":   35,
    "PETG":     22,   "PETG-CF":  38,
    "ABS":      20,   "ASA":      25,
    "PC":       35,   "PC-CF":    55,
    "PA6":      40,   "PA12":     35,
    "PA-CF":    60,   "TPU_85A":  35,
    "TPU_95A":  30,   "Tullomer": 45,
    "PVA":      40,   "HIPS":     22,
}

def estimated_cost(weight_g, material="PLA"):
    price_kg = FILAMENT_PRICES.get(material, 25)
    return round(weight_g * price_kg / 1000, 2)
```

### 3.4 Complete Report

```
PRINT ESTIMATE — {part_name}
================================
Volume:            {vol:,.0f} mm3 ({vol/1000:.1f} cm3)
Estimated weight:  {weight:.1f}g ({material}, {infill}% infill)
Estimated time:    ~{hours}h {min}min (layer {layer_h}mm, {speed}mm/s)
Filament cost:     ~EUR {cost:.2f} ({material} @ EUR {price}/kg)
Nozzle temp:       {temp_nozzle_min}-{temp_nozzle_max}°C
Bed temp:          {temp_bed_min}-{temp_bed_max}°C
Enclosed chamber:  {"REQUIRED" if chamber else "Not needed"}
Drying:            {"REQUIRED ({dry_t}°C x {dry_h}h)" if drying else "Not needed"}
```

---

## 4. Special Rules: Tullomer and Polycarbonate

### 4.1 Common Rules for PC and Tullomer

Both PC and Tullomer are engineering materials with high temperature resistance and special requirements:

| Rule | Value | Reason |
|---|---|---|
| Minimum wall | >= 2.0mm | High interlayer stress, thin walls delaminate |
| Internal fillets | >= 1.0mm on ALL corners | Stress concentration causes cracks |
| Enclosed chamber | MANDATORY (>50°C) | Severe warping, delamination |
| Hotend | All-metal | Temperatures >250°C, PTFE degrades |
| Drying | Critical | Bubbles, stringing, delamination if wet |
| Max speed | 40-60 mm/s | Interlayer adhesion requires time |
| Part fan | 0-30% | Rapid cooling causes warping and delamination |

### 4.2 Fiber Orientation vs Loads (-CF materials)

For fiber-reinforced materials (PLA-CF, PETG-CF, PC-CF, PA-CF):

```
RULE: Short fibers align in the PRINT DIRECTION (X/Y axis of the layer).

Mechanical strength is ANISOTROPIC:
  - XY direction (in-layer plane): 100% of nominal strength
  - Z direction (between layers): 30-50% of nominal strength

DESIGN CONSEQUENCE:
  OK: Tension/compression loads in XY plane -> strong
  NO: Tension loads along Z (between layers) -> weak
  OK: Bending with neutral axis in XY plane -> strong
  NO: Bending with neutral axis along Z -> weak
```

**Orientation rules:**

| Load type | Recommended print orientation |
|---|---|
| Tension along longest axis | Print with long axis in X or Y |
| Bending (beam) | Layers perpendicular to neutral axis |
| Axial compression | Z-up (layers perpendicular to load) |
| Torsion | Layers parallel to torsion axis |
| Multi-axis load | Prioritize main load direction |

### 4.3 Creep at 80°C — Tullomer and PC Verification

```
IF material IN (Tullomer, PC) AND service_temperature > 60°C AND sustained_load:
    WARNING: "At {temp}°C with sustained load, verify creep.
             Reduce allowable stress by 40-60% compared to 23°C data.
             Consider:
             - Increase resistant cross-section (+50%)
             - Reduce service temperature if possible
             - Use PC-CF or PA-CF for better creep resistance"
```

**Creep reduction factors:**

| Temperature | Factor on tensile strength |
|---|---|
| 23°C (ambient) | 1.0 (nominal value) |
| 50°C | 0.8 |
| 60°C | 0.65 |
| 80°C | 0.45 |
| 100°C | 0.30 |
| 120°C (PC only) | 0.20 |

### 4.4 CadQuery Checklist for PC/Tullomer

Before generating CadQuery code for PC or Tullomer parts, verify:

- [ ] `wall >= 2.0` mm throughout the model
- [ ] Fillet >= 1.0mm on ALL internal corners (`.fillet(1.0)`)
- [ ] No sharp internal corners (stress concentrators)
- [ ] Uniform thicknesses where possible (avoid abrupt transitions)
- [ ] Holes with countersink or entry fillet
- [ ] Ribs with draft angle >= 1° if possible
- [ ] Print orientation chosen to maximize interlayer adhesion in load direction
- [ ] Brim >= 8mm in slicer profile

---

## 5. Printer Profiles

### 5.1 Printer Database

| Printer | Volume (mm) | Max speed | Chamber | Multi-mat | Nozzle | Notes |
|---|---|---|---|---|---|---|
| **Bambu X1C** | 256x256x256 | 500 mm/s | Enclosed (heated) | AMS 4 slot | 0.4 default | Top tier. ABS/PC/PA no problem. |
| **Bambu P1S** | 256x256x256 | 500 mm/s | Enclosed (not heated) | AMS 4 slot | 0.4 default | Like X1C but chamber not actively heated. OK for ABS/ASA. |
| **Bambu A1** | 256x256x256 | 500 mm/s | Open | AMS lite 4 slot | 0.4 default | PLA/PETG/TPU only. NO ABS/PC/PA (no chamber). |
| **Bambu A1 Mini** | 180x180x180 | 500 mm/s | Open | AMS lite 4 slot | 0.4 default | Reduced volume. PLA/PETG/TPU only. |
| **Prusa MK4S** | 250x210x220 | 200 mm/s | Open (enclosure opt.) | MMU3 5 slot | 0.4 default | Reliable. With DIY enclosure: ABS possible. |
| **Prusa XL** | 360x360x360 | 200 mm/s | Open (enclosure opt.) | 5 toolhead | 0.4 default | Huge volume. True multi-tool. Optional enclosure for ABS. |
| **Creality Ender 3 V3** | 220x220x250 | 300 mm/s | Open | No | 0.4 default | Entry-level. PLA/PETG only. |
| **Creality K1** | 220x220x250 | 600 mm/s | Enclosed | No | 0.4 default | Fast. Enclosed chamber for ABS/ASA. |
| **Voron 2.4** | 350x350x340 | 500 mm/s | Enclosed (heated) | No (opt.) | 0.4 default | DIY CoreXY. Heated enclosed chamber up to 60°C. Ideal for PC/PA/CF. |

### 5.2 Material-Printer Compatibility

```
FOR EACH selected material:
    IF material.chamber_required:
        printers_ok = [X1C, P1S, K1, Voron 2.4]
        printers_with_mod = [Prusa MK4S+enclosure, Prusa XL+enclosure]
        printers_no = [Bambu A1, A1 Mini, Ender 3]
    OTHERWISE:
        printers_ok = all
```

**Quick compatibility matrix:**

| Material | X1C | P1S | A1 | MK4S | XL | Ender 3 | K1 | Voron |
|---|---|---|---|---|---|---|---|---|
| PLA | OK | OK | OK | OK | OK | OK | OK | OK |
| PLA-CF | OK1 | OK1 | OK1 | OK1 | OK1 | OK1 | OK1 | OK1 |
| PETG | OK | OK | OK | OK | OK | OK | OK | OK |
| ABS | OK | OK | NO | WARN2 | WARN2 | NO | OK | OK |
| ASA | OK | OK | NO | WARN2 | WARN2 | NO | OK | OK |
| PC | OK | WARN3 | NO | NO | WARN2 | NO | WARN3 | OK |
| PC-CF | OK1 | WARN13 | NO | NO | WARN12 | NO | WARN13 | OK1 |
| PA6 | OK | WARN3 | NO | NO | WARN2 | NO | WARN3 | OK |
| PA-CF | OK1 | WARN13 | NO | NO | WARN12 | NO | WARN13 | OK1 |
| TPU 85A | OK4 | OK4 | OK4 | OK4 | OK4 | WARN5 | OK4 | OK4 |
| TPU 95A | OK | OK | OK | OK | OK | WARN5 | OK | OK |
| Tullomer | OK | WARN3 | NO | NO | WARN2 | NO | WARN3 | OK |

**Notes:**
1. 1 Hardened steel nozzle mandatory
2. 2 Requires aftermarket/DIY enclosure
3. 3 Chamber not actively heated — possible with precautions, warping risk
4. 4 Reduced speed (20-30 mm/s for 85A, 30-40 mm/s for 95A)
5. 5 Ender 3 is bowden — TPU 85A very difficult, 95A possible slowly

### 5.3 Print Volume Verification

```
IF part.bounding_box > printer.volume:
    ERROR: "The part ({bb.x}x{bb.y}x{bb.z}mm) does not fit in the
             print volume of {printer.name} ({vol.x}x{vol.y}x{vol.z}mm).
             Options:
             1. Choose a larger printer (e.g. Prusa XL: 360x360x360)
             2. Split the part with cuts and interlocks
             3. Rotate the part (if one dimension is dominant)"
```

### 5.4 Recommended Slicer Profiles

| Scenario | Layer | Speed | Infill | Perimeters | Notes |
|---|---|---|---|---|---|
| Quick prototype | 0.28mm | 150 mm/s | 10% | 2 | PLA only |
| Standard | 0.20mm | 80 mm/s | 20% | 3 | Default for most |
| Mechanical | 0.16mm | 60 mm/s | 40% | 4 | Parts under load |
| Precision | 0.12mm | 40 mm/s | 30% | 3 | Tight tolerances |
| Structural | 0.16mm | 40 mm/s | 60% | 5 | Maximum strength |
| Flexible (TPU) | 0.20mm | 25 mm/s | 20% | 3 | Retraction 0-1mm |
| PC / Tullomer | 0.20mm | 40 mm/s | 30% | 4 | Fan 0-20%, enclosed chamber |

---

## 6. Integration with CadQuery Pipeline

### 6.1 Workflow

```
1. User specifies use case + operating conditions
2. print-profiles selects material (Section 1)
3. print-profiles applies constraints to design (Section 2):
   - wall_min_mm -> verify/update CadQuery parameters
   - shrinkage_pct -> compensation on critical dimensions
   - chamber_required -> printer compatibility warning
   - mandatory fillets for PC/Tullomer
4. cadquery-codegen generates code with applied constraints
5. cadquery-validate executes and verifies
6. print-profiles generates report (Section 3):
   - Estimated weight
   - Estimated time
   - Filament cost
   - Material-specific print notes
```

### 6.2 Constraint Application Example

```python
# User input: outdoor enclosure, temp 60°C
# Selection: ASA (outdoor + UV + 90°C service)

# Constraints applied automatically:
material = "ASA"
wall = max(user_wall, 1.2)        # wall_min_mm ASA = 1.2
# Shrinkage compensation on critical dimensions:
# pcb_clearance += compensate_shrinkage(pcb_clearance, 0.55%)
# Enclosed chamber warning: ASA requires enclosed chamber

# In the final report:
# WARNING: ENCLOSED CHAMBER REQUIRED — compatible printers: X1C, P1S, K1, Voron
# WARNING: DRYING: 65°C x 4h before printing
# Estimated weight: 45.2g (ASA, 20% infill)
# Estimated time: ~3h 15min
```

---

## 7. Pre-Print Checklist

Before declaring the model ready for printing:

- [ ] Material selected and justified for the use case
- [ ] `wall >= material.wall_min_mm` verified throughout the model
- [ ] Fillet >= 1mm on internal corners (if PC/Tullomer)
- [ ] Shrinkage compensation applied on critical dimensions
- [ ] Print volume verified for the target printer
- [ ] Printer-material compatibility verified (Section 5.2)
- [ ] Drying flagged if necessary
- [ ] Enclosed chamber flagged if necessary
- [ ] Hardened steel nozzle flagged if -CF material
- [ ] Weight/time/cost report generated
- [ ] Recommended slicer profile indicated
