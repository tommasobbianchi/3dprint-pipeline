# Target Practice Prompts — Increasing Difficulty

> Each example exercises different skills of the pipeline.
> Use: `cd ~/projects/3dprint-pipeline && claude`
> Then: `Read skills/3d-print-orchestrator/SKILL.md` before the prompt.

---

## LEVEL 1 — Parametric Primitives (codegen + validate only)

### 1.1 — Cube with hole
```
Create a 30x30x30mm cube with a through-hole dia 10mm centered on the top face.
Material PLA. Fillet r=2mm on all vertical edges.
```
**Tests:** native fillets, through-hole, STEP+STL export

---

### 1.2 — Washer / spacer
```
/box 0
Create a cylindrical spacer: outer diameter 12mm, inner bore dia 5.2mm (M5 clearance hole),
height 8mm. Chamfer 0.5mm on both top and bottom edges.
```
**Tests:** hollow cylinder, chamfer, precise dimensions for screw

---

### 1.3 — Name tag
```
Create a rectangular tag 60x20x3mm with rounded corners r=3mm.
Add the text "TOMMY" embossed 1mm on the top face.
Simple font, centered.
```
**Tests:** 3D text (CadQuery supports text via Workplane.text()), 2D fillet

---

## LEVEL 2 — Simple Functional Parts (codegen + validate + materials)

### 2.1 — Wall-mounted pipe clip
```
Wall-mounted clip for a dia 25mm pipe (plumbing tube).
Wall mounting with 2x M4 screws (holes spaced 50mm vertically).
The pipe must snap in through a side opening (C-clip, not a closed circle).
Material PETG. Wall thickness 2.5mm.
```
**Tests:** C-profile (open arc), mounting holes, PETG constraints

---

### 2.2 — Wedge doorstop
```
Wedge doorstop:
- Length 100mm, width 40mm
- Height from 2mm (tip) to 25mm (base)
- Anti-slip texture on the bottom face (grid of small 1x1mm bumps, 3mm pitch)
- Lanyard hole dia 5mm in the tall end
Material TPU 95A.
```
**Tests:** loft (tapered wedge), repeating pattern, flexible material

---

### 2.3 — Parametric box with lid
```
/box 80x60x40 PETG

Add:
- Lid with male/female interlock (1.5mm lip)
- 4x M3 self-tapping screw holes at corners
- Label slot 40x15mm recessed 0.5mm on the front
- Cylindrical feet h=2mm dia 8mm under 4 corners
```
**Tests:** 2-part assembly (body+lid), interlock lip with tolerance, multiple features

---

## LEVEL 3 — Enclosures and Mechanical Parts (all skills except image)

### 3.1 — ESP32-CAM enclosure with SD slot and lens hole
```
Enclosure for ESP32-CAM:
- PCB: 40.5 x 27 x 4.5mm (without camera)
- Camera module protrusion: 8x8x5mm centered on one short side
- Lens hole dia 8mm aligned with the camera
- Micro-SD slot accessible from the side
- FTDI connector slot (6 pins, 2.54mm pitch) on the side opposite the camera
- Snap-fit closure
- M2 mounting screw hole on the back
- Material: black PLA

Print orientation: enclosure base on build plate, no supports needed.
```
**Tests:** precise dimensions, snap-fit, circular lens hole, side slots

---

### 3.2 — Reinforced L-bracket with ribs
```
L-bracket for wall-mounting a 20x20mm aluminum extrusion:
- Horizontal arm: 60x40mm with 2x dia 5.5mm holes (M5 clearance) spaced 30mm
- Vertical arm: 60x40mm with 2x dia 5.5mm symmetrical holes
- Thickness: 4mm
- 3 triangular reinforcement ribs in the inner corner (h=15mm, thickness 2mm)
- Fillet r=3mm in the inner L-corner
- Fillet r=1mm on all outer edges
- Material: PETG-CF

Must hold ~2kg load. Print orientation: vertical arm on build plate.
```
**Tests:** ribs, multiple fillets, structural considerations, composite material

---

### 3.3 — Tube adapter with loft
```
Reducer adapter for vacuum cleaner hose:
- Inlet: dia 35mm outer, 2mm wall thickness
- Outlet: dia 25mm outer, 2mm wall thickness
- Transition length: 45mm (gradual loft, no sharp edges)
- 5mm straight lip on both ends (for tube insertion)
- Fillet r=0.5mm on lip edges
- Tolerance: slip-fit (0.3mm clearance on diameter relative to tubes)
- Material: PETG

This part is IMPOSSIBLE to do well in OpenSCAD — loft is native in CadQuery.
```
**Tests:** loft between 2 circles of different diameter — key CadQuery feature

---

## LEVEL 4 — Multi-Part Assembly and Complex Design

### 4.1 — Print-in-place hinge
```
2-part hinge for a door panel:
- Total width: 40mm
- 3 alternating knuckles (2 on one part, 1 on the other)
- Integrated pin dia 3mm with 0.3mm clearance
- Mounting holes: 2 per side, M3
- Mounting plates 40x15x3mm
- Fillet r=0.5mm on all edges
- Material: PLA

Export as assembly .step with the 2 parts separate and positioned.
Also export the 2 separate STLs for printing.
```
**Tests:** cq.Assembly(), multi-part export, rotary coupling tolerances

---

### 4.2 — Phone charging dock with cable management
```
Smartphone charging dock:
- Angled rest at 70deg for visible screen
- Width: 80mm (fits phones up to 78mm)
- Stable base: 80x90mm, front height 5mm, rear height 60mm
- USB-C cable groove: width 12mm, routed through the thickness
- Cable channel running along the base and exiting from the rear
- Front lip 8mm tall for phone support
- Anti-slip pads: 4x dia 10mm recesses 1mm deep on the bottom (for adhesive rubber feet)
- Text "CHARGE" engraved 0.3mm on the front base
- Generous fillets r=3mm on all visible edges
- Material: PLA silk

Print without supports. Cable channel must be accessible without disassembly.
```
**Tests:** complex geometry, sweep for cable channel, angled surface, aesthetics

---

### 4.3 — Arduino Uno + breadboard + OLED display enclosure
```
Multi-component enclosure:
- Arduino Uno Rev3: 68.6x53.4mm, M3 standoffs at the 4 exact positions
  (13.97,2.54), (66.04,7.62), (66.04,35.56), (15.24,50.8) mm
- Mini breadboard: 47x35mm, next to the Arduino
- OLED display 0.96" I2C: 27x27mm, rectangular opening in the lid
- Openings: USB-B (12x10.9mm) and DC jack (9x11mm) on the correct sides
- Side slots for jumper wire pass-through (2x 15x3mm slots)
- Ventilation grid on top (excluding display area)
- 4-point snap-fit closure
- Fillet r=1.5mm on outer vertical edges
- Material: PETG
- Feet h=3mm at corners

Export body and lid as assembly .step + separate STLs for printing.
```
**Tests:** precise multi-component positioning, assembly, multiple openings

---

## LEVEL 5 — From Image + Engineering Design (full pipeline)

### 5.1 — Reverse engineering from photo
```
[ATTACH PHOTO of a broken/worn part]

Recreate this part based on the photo.
The center hole diameter is 8mm (measured with caliper).
Material: PETG.
Must be functionally identical to the original.
```
**Tests:** image-to-3d skill -> spatial reasoning -> codegen -> validate

---

### 5.2 — From hand sketch
```
[ATTACH PHOTO of a hand sketch]

Turn this sketch into a printable 3D model.
Dimensions written on the sketch are in millimeters.
Where there are no dimensions, estimate proportionally.
Material: PLA.
```
**Tests:** sketch interpretation, relative dimension estimation, translation to CadQuery

---

### 5.3 — High-performance mechanical part
```
Support bracket for NEMA 17 motor in an 80C environment:
- 4 motor mounting holes: M3 at 31mm spacing (standard NEMA 17 square pattern)
- Center hole dia 22.5mm for motor boss
- 2 side mounting holes M4 for mounting on 2020 extrusion
- Base thickness: 5mm
- Side arm with 90deg angle and reinforcement ribs
- MUST withstand continuous 80C with ~20N axial load
- Material: Tullomer (or PC if Tullomer not available)
- All internal corners: fillet r>=1.5mm (mandatory for PC/Tullomer)
- Shrinkage compensation: +0.5% on critical dimensions (mounting holes)

Print orientation: flat base on build plate, fibers parallel to load.
Verify that no wall is thinner than 2.5mm.
```
**Tests:** thermal constraints, composite material, shrinkage compensation, advanced DFM

---

### 5.4 — Multi-part modular system
```
Modular desk organizer snap-together system:
- Base module: 80x80mm, height 30mm, with puzzle-type interlocking edge
  on all 4 sides (male on 2 sides, female on the other 2)
- Pen holder module: same 80x80mm base, 6x dia 15mm holes 80mm deep
- Phone holder module: same base, with angled slot at 70deg
- Card holder module: same base, 30mm wide slot
- All modules connect laterally via the puzzle interlocks
- Material: PLA
- Fillet r=1mm on all visible edges

Export as complete assembly .step (all 4 modules side by side)
+ 4 separate STLs for printing.
Puzzle connectors must have tight-fit tolerance (0.1mm).
```
**Tests:** 4-part assembly, repeated connection interface, dimensional consistency

---

## LEVEL 6 — Stress Tests and Edge Cases

### 6.1 — Parametric gear pair
```
Spur gear pair with straight teeth:
- Gear 1: 20 teeth, module 1.5
- Gear 2: 40 teeth, module 1.5 (2:1 ratio)
- Face width: 8mm
- Shaft bore: dia 5mm with 2x2mm keyway on both
- Correct center distance calculated from module
- Simplified involute tooth profile (polygonal approximation acceptable)
- Material: PLA-CF for stiffness

Export assembly with the 2 gears in correct position.
+ Separate STLs. Note the printability limitations of small teeth.
```
**Tests:** complex mathematical geometry, involute profile, positioned assembly

---

### 6.2 — Sweep along path
```
Ergonomic drawer handle:
- Path: elliptical arc, width 120mm, max protrusion 30mm from plane
- Cross-section: 12x20mm rectangle with rounded corners r=4mm
- Mounting feet at ends: 20x20x5mm with M4 hole each
- Gradual transition (loft) between handle cross-section and feet
- Fillet r=2mm on transition edges
- Material: PETG

Use sweep for the body and loft for transitions.
Both operations impossible in OpenSCAD.
```
**Tests:** sweep along curved path, loft for transitions, ergonomic geometry

---

### 6.3 — IP-rated enclosure with gasket
```
Weatherproof IP54 enclosure for outdoor sensor:
- Internal dimensions: 60x40x25mm
- Wall 3mm
- O-ring groove 2mm (1.5x1.5mm cross-section) around lid perimeter
- Cable gland: dia 8mm hole with conical boss for PG7 cable gland
- 4x M3 screws with heat inserts for closure, rectangular pattern
- Internal cylindrical bosses for PCB mounting (4x M2.5 standoffs, height 5mm)
- Drainage channel: 1x1mm groove on external bottom
- Material: ASA (UV resistance for outdoor)
- Fillet r=2mm on all outer edges

Export body + lid as assembly. Include note on slicer settings
to maximize water-tightness (100% infill on walls, 5 perimeters).
```
**Tests:** O-ring groove (precision feature), cable gland, internal bosses, advanced DFM

---

## Summary Table

| Lv | Example | Skills Tested | Key CadQuery Feature |
|----|---------|---------------|----------------------|
| 1.1 | Cube with hole | codegen, validate | fillet, hole |
| 1.2 | Spacer | codegen, validate | hollow cylinder, chamfer |
| 1.3 | Name tag | codegen, validate | text(), 2D fillet |
| 2.1 | Pipe clip | + materials | arc, C-clip |
| 2.2 | Doorstop | + materials | loft (wedge), pattern |
| 2.3 | Box+lid | + materials | 2-part assembly, lip |
| 3.1 | ESP32 enclosure | all except image | snap-fit, slot, lens hole |
| 3.2 | L-bracket | all except image | ribs, multiple fillets |
| 3.3 | Tube adapter | all except image | **loft** (impossible in OpenSCAD) |
| 4.1 | Hinge | all except image | **multi-part assembly** |
| 4.2 | Charging dock | all except image | **sweep** cable channel |
| 4.3 | Multi-PCB enclosure | all except image | precise multi-board positioning |
| 5.1 | From photo | **ALL** | image-to-3d pipeline |
| 5.2 | From sketch | **ALL** | dimension estimation from sketch |
| 5.3 | 80C bracket | **ALL** | Tullomer/PC, thermal DFM |
| 5.4 | Modular 4-part | all except image | **4-part assembly**, puzzle-fit |
| 6.1 | Gear pair | all except image | involute geometry, ratio |
| 6.2 | Handle sweep | all except image | **sweep + loft** combined |
| 6.3 | IP54 enclosure | all except image | O-ring groove, cable gland |
