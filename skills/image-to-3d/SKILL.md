# SKILL: image-to-3d — Image Analysis and Structured Specifications for CadQuery

## Identity
Specialized visual analyzer for reverse-engineering from images to structured 3D specifications.
Receives an image (sketch, photo, technical drawing, CAD screenshot), analyzes it, and produces
structured output that feeds the spatial-reasoning skill for CadQuery modeling.

---

## 1. Input Classification

Before analyzing the image, classify the input type. The classification determines
the analysis protocol, confidence level, and questions to ask the user.

### 1.1 Input Types

| Type | Characteristics | Dimensional confidence | Required action |
|---|---|---|---|
| **A. Hand sketch** | Imprecise strokes, approximate proportions, possible annotations | LOW — ask for dimensions | Extract shapes and topology, ask for ALL dimensions |
| **B. Object photo** | Perspective, distortion, possible dimensional references | MEDIUM — estimate from references | Identify known references, estimate dimensional ratios |
| **C. Technical drawing** | Orthogonal views, dimensions, tolerances, cross-sections | HIGH — read directly | Extract dimensions, sections, views; verify consistency between views |
| **D. CAD screenshot** | Rendered 3D model, possible dimension overlays | HIGH — read if present | Identify features, extract dimensions if visible |
| **E. Product image** | Catalog/ecommerce photo, clean background, known angles | MEDIUM — estimate from category | Identify product category, estimate from standards |

### 1.2 Classification Decision Tree

```
IMAGE RECEIVED
|
+-- Has numeric dimensions/measurements written?
|   +-- Orthogonal views (front, side, top)? -> TYPE C: Technical drawing
|   +-- Single view with annotations? -> TYPE D: CAD screenshot (or TYPE A if sketch)
|
+-- Hand-drawn strokes?
|   +-- -> TYPE A: Hand sketch
|
+-- Real photo (texture, shadows, background)?
|   +-- White/catalog background? -> TYPE E: Product image
|   +-- Real environment background? -> TYPE B: Object photo
|
+-- 3D rendering / wireframe?
    +-- -> TYPE D: CAD screenshot
```

---

## 2. Analysis Protocol

### 2.1 Structured Analysis Prompt

For each image, perform this analysis in sequence:

```
IMAGE ANALYSIS
==============

INPUT TYPE: [A/B/C/D/E] — [type name]
DIMENSIONAL CONFIDENCE: [LOW/MEDIUM/HIGH]

STEP 1 — PRIMITIVE SHAPE IDENTIFICATION
  Detected shapes:
    1. [name] — [primitive: box/cylinder/tube/plate/cone/sphere/L-profile/U-profile/...]
       Position: [where in the part — base, top, side, center]
       Estimated dimensions: [L x W x H mm] (confidence: [high/medium/low])
    2. [...]

STEP 2 — DETECTED OPERATIONS
  Boolean operations and features:
    1. [type: hole/pocket/slot/fillet/chamfer/rib/boss/snap-fit/...]
       Position: [on which shape, where]
       Estimated dimensions: [dia, depth, radius, ...]
    2. [...]

STEP 3 — SYMMETRIES AND PATTERNS
  Symmetries:
    [] Axial symmetry (revolution): [yes/no] — axis: [X/Y/Z]
    [] Mirror symmetry: [yes/no] — plane: [XY/XZ/YZ]
    [] Circular pattern: [yes/no] — N elements, radius
    [] Linear pattern: [yes/no] — N elements, pitch

STEP 4 — DIMENSIONAL RATIOS
  If absolute dimensions are unknown:
    - L:W:H ratio ~ [a : b : c]
    - Reference dimension: [known element] = [value] mm
    - Derived scale: 1 image unit ~ [X] mm

STEP 5 — FUNCTIONAL FEATURES
  Probable purpose: [what the part does — support, enclosure, adapter, ...]
  External interfaces:
    1. [where it connects] — [type: screw, snap, press-fit, rest]
    2. [...]
  Functional constraints:
    - [e.g. must withstand load, must be waterproof, must conduct heat, ...]
```

### 2.2 Mandatory Questions by Type

#### Type A — Hand sketch

ALWAYS ask:
1. Overall dimensions (L x W x H)
2. Wall thickness (if enclosure or shell)
3. Hole diameters and type (through/blind, threaded/smooth)
4. Material and intended use
5. Critical tolerances (fits)

#### Type B — Object photo

Ask IF references are missing:
1. Is there a known object in the image for scale? (coin, USB, finger, ...)
2. Dimension of at least one known element
3. Material of the original part
4. Function and fits

#### Type C — Technical drawing

Ask ONLY IF ambiguous:
1. Drawing scale (if not indicated)
2. General tolerances (if not per standard)
3. Material (if not indicated in the title block)

#### Type D — CAD screenshot

Ask ONLY IF missing:
1. Dimensions not visible in the screenshot
2. Hidden features (blind holes, internal cavities)

#### Type E — Product image

Ask IF not determinable:
1. Exact product category
2. Dimension of a known element
3. Function and usage context

---

## 3. Dimensional Reference Table

### 3.1 Common Objects for Scale

| Reference | Dimension | Use |
|---|---|---|
| 1 cent EUR coin | dia 16.25 mm | Small objects |
| 10 cent EUR coin | dia 19.75 mm | Small objects |
| 50 cent EUR coin | dia 24.25 mm | Medium objects |
| 1 EUR coin | dia 23.25 mm | Medium objects |
| 2 EUR coin | dia 25.75 mm | Medium objects |
| Credit card | 85.6 x 53.98 mm | Flat objects |
| A4 sheet | 210 x 297 mm | Large objects |
| Standard Bic pen | dia 7 mm, L 150 mm | Linear scale |
| Adult index finger | ~18 mm width, ~75 mm length | Quick estimate |
| Adult pinky finger | ~14 mm width | Small details |
| Adult palm | ~85 mm width | Medium objects |

### 3.2 Standard Connectors

| Connector | Opening dimensions | Notes |
|---|---|---|
| USB-A | 12.0 x 4.5 mm | Classic rectangular connector |
| USB-C | 8.34 x 2.56 mm | Oval, symmetrical |
| USB-B | 12.0 x 10.9 mm | Nearly square, tapered |
| USB Micro-B | 6.85 x 1.80 mm | Thin trapezoidal |
| USB Mini-B | 6.8 x 3.0 mm | Trapezoidal |
| HDMI standard | 14.0 x 4.55 mm | Trapezoidal |
| HDMI mini | 10.42 x 2.42 mm | Small trapezoidal |
| HDMI micro | 6.4 x 2.8 mm | Similar to micro-USB |
| Ethernet RJ45 | 11.68 x 13.54 mm | Square with clip |
| 3.5mm audio jack | dia 3.5 mm | Round hole |
| Barrel jack 5.5/2.1 | dia 5.5 mm outer | DC power |
| SD card | 24.0 x 32.0 x 2.1 mm | Guided slot |
| MicroSD | 11.0 x 15.0 x 1.0 mm | Small slot |

### 3.3 Electronic Boards

| Board | PCB dimensions | Mounting holes | Notes |
|---|---|---|---|
| Arduino Uno R3 | 68.6 x 53.4 mm | 4x dia 3.2, irregular positions | USB-B + barrel jack |
| Arduino Nano | 18.0 x 45.0 mm | 2x dia 1.6 (or none) | Mini-USB or USB-C |
| Arduino Mega 2560 | 101.6 x 53.3 mm | 4x dia 3.2 | USB-B + barrel jack |
| Raspberry Pi 4B | 85.0 x 56.0 mm | 4x M2.5, 58x49mm pattern | 2x USB-A + 2x micro-HDMI + USB-C |
| Raspberry Pi Zero 2W | 65.0 x 30.0 mm | 4x dia 2.75 | Mini-HDMI + micro-USB |
| Raspberry Pi Pico | 21.0 x 51.0 mm | 4x dia 2.1, 11.4x47mm pattern | Micro-USB or USB-C |
| ESP32 DevKit V1 | 51.0 x 28.0 mm | none (breadboard pins) | Micro-USB, antennas on sides |
| ESP32-S3 DevKit | 69.0 x 26.0 mm | none | USB-C |
| ESP8266 NodeMCU | 49.0 x 26.0 mm | none (breadboard pins) | Micro-USB |
| STM32 Blue Pill | 53.0 x 23.0 mm | none (breadboard pins) | Micro-USB |

### 3.4 Standard Hardware

| Element | Dimension | Use in estimation |
|---|---|---|
| M2 socket head screw | head dia 3.8 mm | Small electronics |
| M2.5 socket head screw | head dia 4.5 mm | RPi, electronics |
| M3 socket head screw | head dia 5.5 mm | General purpose |
| M3 countersunk screw | head dia 6.0 mm | Flat surfaces |
| M4 socket head screw | head dia 7.0 mm | Structural |
| M5 socket head screw | head dia 8.5 mm | Heavy structural |
| M3 nut | 5.5 mm wrench, 2.4 mm tall | Extremely common |
| M4 nut | 7.0 mm wrench, 3.2 mm tall | Structural |
| M5 nut | 8.0 mm wrench, 4.0 mm tall | Heavy structural |
| M3 washer | OD 7.0, ID 3.2, t 0.5 mm | Load distribution |
| M4 washer | OD 9.0, ID 4.3, t 0.8 mm | Load distribution |
| M3 heat insert | dia 4.0-4.2 mm seat | Threading into plastic |
| M4 heat insert | dia 5.6-6.0 mm seat | Threading into plastic |

### 3.5 Standard Profiles and Tubes

| Element | Dimensions | Notes |
|---|---|---|
| Round tube 15mm | OD 15, wall 1.0 mm | Small rods |
| Round tube 20mm | OD 20, wall 1.5 mm | Curtain rods, light structures |
| Round tube 25mm | OD 25, wall 1.5 mm | Clothes hangers |
| Round tube 32mm | OD 32, wall 2.0 mm | Plumbing, structures |
| Aluminum extrusion 2020 | 20 x 20 mm | 6mm slot, V-slot or T-slot |
| Aluminum extrusion 3030 | 30 x 30 mm | 8mm slot |
| Aluminum extrusion 4040 | 40 x 40 mm | 8mm slot, heavy structures |
| Round bar 8mm | dia 8 mm | Linear guides, pins |
| Round bar 10mm | dia 10 mm | Guides, shafts |

---

## 4. Structured Output

The image analysis output feeds directly into Phase 1 (Functional Decomposition)
of the spatial-reasoning skill. Format:

```
IMAGE-TO-3D OUTPUT
==================

INPUT TYPE: [A/B/C/D/E] — [type name]
CONFIDENCE: [LOW/MEDIUM/HIGH]
SCALE REFERENCE: [object used] = [dimension] mm

OBJECTIVE: [part function — what it does, where it mounts, why it's needed]

CONSTRAINTS:
  Suggested material: [PLA/PETG/ABS/ASA/PC/TPU] — [rationale]
  Service temperature: [°C]
  Loads: [type and direction]
  Fits: [list of interfaces]
  Maximum dimensions: [printer or space constraint]

COMPONENTS:
  1. [name] — [CadQuery primitive: box/cylinder/polyline+extrude/revolve/loft]
     Dimensions: [L x W x H mm] (confidence: [high/medium/low])
     Function: [why it exists]
     CadQuery: [operation hint — e.g. "cq.Workplane('XY').box(40, 30, 5)"]
  2. [...]

FEATURES:
  1. [type: hole/pocket/slot/fillet/chamfer/shell/boss/rib/snap_clip]
     On: [component N]
     Dimensions: [dia, depth, radius, ...]
     CadQuery: [hint — e.g. ".faces('>Z').workplane().hole(3.4)"]
  2. [...]

EXPLOITABLE SYMMETRIES:
  - [symmetry type] -> [CadQuery operation: .mirror() / .polarArray() / .rarray()]

BOOLEAN OPERATIONS:
  Suggested order:
    1. [base component]
    2. + [addition]: [component N]
    3. - [subtraction]: [feature N]
    4. fillet/chamfer: [where, radius] — BEFORE booleans if using broad selector

SUGGESTED PRINT ORIENTATION:
  XY plane: [which face on the bed]
  Rationale: [why]
  Supports: [yes/no — where if yes]

QUESTIONS FOR THE USER (if confidence < HIGH):
  1. [specific question with options if possible]
  2. [...]
```

### 4.1 Visual Shapes to CadQuery Primitives Mapping

| Shape seen in image | CadQuery primitive | Notes |
|---|---|---|
| Rectangle / block | `cq.Workplane("XY").box(w, d, h)` | Most common shape |
| Cylinder / tube | `cq.Workplane("XY").cylinder(h, r)` | If hollow: `.circle(r_ext).circle(r_int).extrude(h)` |
| Sphere | `cq.Workplane("XY").sphere(r)` | Rare in FDM |
| L / T / U profile | `cq.Workplane("XZ").polyline(pts).close().extrude(d)` | 2D sketch + extrusion |
| Axisymmetric part | `cq.Workplane("XZ").polyline(pts).close().revolve()` | Bushings, adapters, knobs |
| Transition between sections | `loft()` between sketches on different workplanes | Shape transitions |
| Shell / enclosure | `.box().shell(-wall)` or `box.cut(cavity)` | Shell is cleaner if uniform |
| Organic curved shape | NOT supported — flag as limitation | Suggest sculpting |

### 4.2 Visual Features to CadQuery Operations Mapping

| Feature seen | CadQuery operation | Notes |
|---|---|---|
| Round through hole | `.faces(sel).workplane().hole(d)` | Select correct face |
| Blind hole | `.faces(sel).workplane().circle(r).cutBlind(-depth)` | Negative depth |
| Oblong hole / slot | `.faces(sel).workplane().slot2D(length, d).cutBlind(-depth)` | Or polyline+cutBlind |
| Rectangular pocket | `.faces(sel).workplane().rect(w, l).cutBlind(-depth)` | Square pocket |
| Fillet (constant radius) | `.edges(sel).fillet(r)` | WARNING: before booleans! |
| Chamfer | `.edges(sel).chamfer(c)` | On entry/assembly edges |
| Rib | `.union(rib_body)` with triangular polyline | Structural reinforcement |
| Cylindrical boss | `.union(cylinder)` | For screws, standoffs |
| Snap-fit clip | Cantilever with lip — sketch + extrude + cut | See snap_fit template |
| Hole pattern | `.pushPoints(pts).hole(d)` | Or `.rarray()` / `.polarArray()` |
| Grille / ventilation | Pattern of rectangular cuts | `.pushPoints().rect().cutThruAll()` |
| Embossed/engraved text | `.text("...", fontsize, depth)` | Relief better than engraving in FDM |

---

## 5. CadQuery Advantages for Reverse Engineering

### 5.1 Direct Image to CadQuery Mapping

| If you see in the image... | In CadQuery use... | Why better than OpenSCAD |
|---|---|---|
| Fillets/rounds | `.fillet(r)` native | OpenSCAD requires slow `minkowski()` or explicit geometry |
| Transition between diameters | `.loft()` between sections | OpenSCAD: `hull()` convex only, no true loft |
| Profile following a path | `.sweep(path)` | Does not exist in OpenSCAD |
| Multiple assembled parts | `cq.Assembly()` | OpenSCAD: no native assembly |
| Shell with uniform thickness | `.shell(-wall)` | OpenSCAD: 2D `offset()` or manual difference |
| Feature selection on faces | `.faces(">Z").workplane()` | OpenSCAD: manual coordinate calculation |
| Holes on angled faces | `.faces(sel).workplane().hole(d)` | OpenSCAD: manual `rotate()` + `translate()` |
| Holes on irregular pattern | `.pushPoints(pts).hole(d)` | OpenSCAD: loop with individual translates |

### 5.2 Strategy by Part Type

| Part type | CadQuery strategy | Approach |
|---|---|---|
| **Box / enclosure** | `box` + `shell` + features | Model exterior, hollow out, add details |
| **Bracket** | `polyline` + `extrude` + holes | 2D L/T/U profile, extrude, drill |
| **Cylindrical adapter** | `revolve` with cross-section profile | Single 2D profile revolved = entire part |
| **Lid / plate** | thin `box` + features | Flat base, add lip, holes, text |
| **Mount / support** | `box` + `cut` + ribs | Base shape, cut where needed, reinforce |
| **Connector / joint** | `cylinder` + booleans | Concentric cylinders with cuts |
| **Clip / snap-fit** | `box` + cantilever sketch | Base body + flexible tab |
| **Gear** | NOT pure CadQuery | Suggest `cq_gears` library or STEP import |

---

## 6. Dimensional Estimation from Photos

### 6.1 With Known Reference

```
ESTIMATION PROCEDURE WITH REFERENCE:

1. IDENTIFY reference in the image
   - Known object: [name] = [real dimension] mm
   - Measurement in image pixels: [N] px

2. CALCULATE scale
   - Scale = real_dimension / reference_pixels
   - E.g.: 1 EUR coin (23.25mm) = 150px -> scale = 0.155 mm/px

3. MEASURE target in pixels
   - [dimension 1] = [N] px -> [N * scale] mm
   - [dimension 2] = [N] px -> [N * scale] mm
   - [...]

4. CORRECT for perspective
   - If object and reference on the same plane: no correction
   - If different planes: FLAG uncertainty, add +/-15%
   - If oblique viewing angle: FLAG, dimensions perpendicular to optical axis are more reliable

5. ROUND to sensible values
   - Dimensions < 10mm: round to 0.5mm
   - Dimensions 10-50mm: round to 1mm
   - Dimensions > 50mm: round to 5mm
   - If close to a standard value (dia 20, dia 25, dia 32, ...): use standard value

RESULTING CONFIDENCE:
  - Reference on same plane, good lighting: +/-5%
  - Reference on different plane: +/-15%
  - No reference (estimate from category): +/-30%
```

### 6.2 Without Reference — Estimation from Category

| Object category | Typical size range | Estimation basis |
|---|---|---|
| Clip / clamp | 15-40 mm | Finger size |
| Smartphone mount | 60-100 mm width | Phone width ~75mm |
| Electronic enclosure | 30-120 mm | PCB size (see 3.3) |
| Bracket | 30-80 mm | Visible mounting holes |
| Tube adapter | 15-50 mm dia | Standard tube diameter |
| Knob / handle | 20-50 mm | Hand size |
| Vase / container | 50-150 mm | Proportion with hand/table |
| Architectural model | 100-300 mm | Scale 1:100 or 1:200 |

---

## 7. Limitations and Fallback

### 7.1 Cases NOT Supported

| Case | Problem | Suggestion |
|---|---|---|
| Organic shapes (sculpture, anatomy) | CadQuery is parametric BREP, not mesh sculpting | Use Blender/ZBrush -> export STL, import as mesh |
| Complex NURBS surfaces (car body) | Too complex for procedural modeling | Use Fusion360/Onshape for direct modeling |
| Image too blurry/dark | Cannot distinguish shapes and dimensions | Ask for better photo or dimensioned sketch |
| Too little detail | Cannot determine internal features | Ask for additional photos (other angles, cross-section) |
| Part with visible threads | CadQuery has no native threads | Use heat insert (dia 4.0 hole for M3) or `cq_bolts` library |
| Part with decorative texture/pattern | Cannot reproduce in BREP | Simplify: smooth the surface, ignore texture |
| Very large part (>300mm) | Exceeds typical print volume | Suggest splitting into parts with joints |

### 7.2 When to Ask the User for Help

```
ALWAYS ASK IF:
  - Dimensional confidence < MEDIUM and no reference in image
  - Part has non-visible internal features (cavities, channels, undercuts)
  - Image is ambiguous (could be 2+ geometric interpretations)
  - Part function unclear (affects material and tolerances)
  - Critical fits (press-fit, snap-fit) without dimensions

NEVER PROCEED without confirmation on:
  - Absolute dimensions (at least one known measurement)
  - Material (affects minimum thicknesses and fillets)
  - Function (affects loads and tolerances)
```

### 7.3 Additional Photo Request

If a single image is not enough, ask specifically:

```
ADDITIONAL PHOTO REQUEST:

To complete the 3D model I need:

[] Front photo (if main view is missing)
[] Side photo (for depth/thicknesses)
[] Top photo (for plan shape)
[] Bottom photo (for hidden features — holes, cavities)
[] Detail photo of: [specific feature]
[] Photo with dimensional reference (coin, ruler, USB)
[] Dimensioned sketch (even hand-drawn) with critical measurements
```

---

## 8. Full Example — Bracket Photo with Coin

### Input
Photo of a metal L-bracket with holes, next to a 1 EUR coin.

### Analysis

```
IMAGE ANALYSIS
==============

INPUT TYPE: B — Object photo
DIMENSIONAL CONFIDENCE: MEDIUM (1 EUR coin as reference)

STEP 1 — PRIMITIVE SHAPE IDENTIFICATION
  Detected shapes:
    1. Vertical plate — box — position: left arm
       Estimated dimensions: 45 x 25 x 3 mm (confidence: medium)
    2. Horizontal plate — box — position: right/bottom arm
       Estimated dimensions: 35 x 25 x 3 mm (confidence: medium)
    3. Triangular rib — triangular profile — internal corner
       Estimated dimensions: base 15mm, height 15mm, thickness 3mm (confidence: low)

STEP 2 — DETECTED OPERATIONS
  1. Round through hole — on vertical plate, center
     Estimated dimensions: dia 4-5mm (probably M4)
  2. Round through hole — on vertical plate, lower center
     Estimated dimensions: dia 4-5mm (probably M4)
  3. Oblong through hole — on horizontal plate
     Estimated dimensions: 5 x 8mm (adjustment slot)
  4. Fillet — external L corner
     Estimated radius: ~2mm

STEP 3 — SYMMETRIES AND PATTERNS
  [] Axial symmetry: no
  [] Mirror symmetry: yes — YZ plane (the L is symmetric in depth)
  [] Circular pattern: no
  [] Linear pattern: no (holes not equidistant)

STEP 4 — DIMENSIONAL RATIOS
  Reference: 1 EUR coin = 23.25mm = 142px in image
  Scale: 0.164 mm/px
  Vertical arm: 275px -> 45.1mm -> rounded 45mm
  Horizontal arm: 213px -> 34.9mm -> rounded 35mm
  Depth: 153px -> 25.1mm -> rounded 25mm

STEP 5 — FUNCTIONAL FEATURES
  Purpose: wall/surface mounting bracket for support
  Interfaces: M4 screws on both arms
  Constraints: must withstand vertical load (weight of supported object)
```

### Structured Output

```
IMAGE-TO-3D OUTPUT
==================

INPUT TYPE: B — Object photo
CONFIDENCE: MEDIUM
SCALE REFERENCE: 1 EUR coin (dia 23.25mm)

OBJECTIVE: L-bracket for wall mounting, two vertical holes + horizontal slot

CONSTRAINTS:
  Suggested material: PETG — structural load, good strength
  Service temperature: ambient
  Loads: compression on horizontal arm, shear on screws
  Fits: M4 through-bolts
  Maximum dimensions: ~45 x 35 x 25 mm

COMPONENTS:
  1. L-profile — 2D polyline in XZ plane + extrude in Y
     Dimensions: 35(X) x 25(Y) x 45(Z) mm, thickness 3mm
     Function: structural body
     CadQuery: cq.Workplane("XZ").polyline(pts).close().extrude(25)
  2. Rib — triangle in XZ plane + extrude
     Dimensions: base 15 x height 15 x thickness 3mm
     Function: corner reinforcement
     CadQuery: cq.Workplane("XZ").polyline(tri_pts).close().extrude(3)

FEATURES:
  1. hole — dia 4.5mm (M4 clearance) — on vertical arm, 2 positions
     CadQuery: .faces("<X").workplane().pushPoints(pts).hole(4.5)
  2. slot — 5 x 8mm — on horizontal arm
     CadQuery: .faces("<Z").workplane().slot2D(8, 5).cutThruAll()
  3. fillet — r=2mm — external vertical edges
     CadQuery: .edges("|Z").fillet(2) — BEFORE union with rib

EXPLOITABLE SYMMETRIES:
  - Mirror symmetry YZ -> model half + .mirror("YZ") (if appropriate)

BOOLEAN OPERATIONS:
  1. Base: L-profile (extrude)
  2. fillet r=2mm on internal corner edge (NearestToPointSelector)
  3. + union: rib
  4. - cut: M4 holes on vertical arm
  5. - cut: slot on horizontal arm

SUGGESTED PRINT ORIENTATION:
  XY plane: horizontal arm on the bed (base of the L)
  Rationale: maximum adhesion, rib at 45° acceptable
  Supports: no (rib exactly 45°)

QUESTIONS FOR THE USER:
  1. Bracket thickness — I estimate 3mm, correct? (or different measurement?)
  2. Holes on vertical arm — M4 (dia 4.5mm)? Or different size?
  3. Is the slot for position adjustment? Confirm dimensions ~5x8mm?
  4. Material: is PETG fine or do you prefer another?
```

---

## 9. Pre-Output Checklist

Before delivering the structured output to the spatial-reasoning skill:

- [ ] Input type classified correctly
- [ ] All primitive shapes identified with dimensions
- [ ] All features (holes, pockets, fillets) listed
- [ ] Symmetries identified and exploitable
- [ ] At least one dimensional reference used (or dimensions asked from user)
- [ ] Boolean operations ordered correctly (fillet BEFORE booleans)
- [ ] Print orientation suggested with rationale
- [ ] Material suggested with rationale
- [ ] Questions for the user formulated (if confidence < HIGH)
- [ ] No organic/NURBS shapes attempted (flagged as limitation)
- [ ] Output in the structured format from section 4
