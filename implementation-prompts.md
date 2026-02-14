# Implementation Prompts for Claude CLI

> Copy and paste these prompts into Claude CLI to build the pipeline.
> Run from the project root (e.g., `~/projects/3dprint-pipeline/`)

---

## PROMPT 1: Project Setup + MCP Server

```
Read the CLAUDE.md file in this directory and the plan in openscad-pipeline-plan.md.

Your task is to implement the AI->3D Print pipeline. Start with:

1. PROJECT SETUP
   - Create the complete directory structure as per the plan
   - Verify that OpenSCAD is installed (`openscad --version`), if not install it
   - Verify Node.js and npm are available

2. MCP SERVER `openscad-mcp`
   Create an MCP server in TypeScript that exposes these tools:

   - `openscad_render`: Receives OpenSCAD code as a string, saves it to a temp file,
     runs `openscad -o output.stl input.scad 2>&1`, returns:
     { success: bool, stdout: string, stderr: string, stl_path: string|null,
       bounding_box: {x,y,z}|null }

   - `openscad_preview`: Like render but generates PNG with:
     `openscad --camera=0,0,0,55,0,25,200 --imgsize=800,600 -o preview.png input.scad`
     Returns { success: bool, image_path: string }

   - `openscad_validate`: Compiles and verifies the STL is manifold.
     Uses `openscad -o output.stl input.scad 2>&1` and checks stderr for
     "WARNING" or "ERROR". Returns { valid: bool, warnings: string[], errors: string[] }

   - `openscad_export`: Like render but with configurable format (stl, 3mf, amf).
     Returns the exported file path.

   Use the official MCP SDK (@modelcontextprotocol/sdk).
   The server must handle temporary files in /tmp/openscad-mcp/ with automatic cleanup.
   Test each tool with a simple cube `cube([10,10,10]);` to verify it works.

   Also generate the configuration for ~/.claude/mcp_servers.json.

Proceed step by step. For each component created, test it before moving on.
```

---

## PROMPT 2: Skill 1 — Spatial Reasoning

```
Now implement Skill 1: spatial-reasoning.

Create the file skills/spatial-reasoning/SKILL.md with these sections:

1. IDENTITY: Define Claude as a mechanical engineer expert in CSG and 3D spatial reasoning.

2. MANDATORY REASONING PROTOCOL:
   Before any OpenSCAD code, Claude MUST complete a structured reasoning block with:

   a) FUNCTIONAL DECOMPOSITION
      - Part objective
      - Constraints (mechanical, thermal, assembly)
      - Component list with base shape and approximate dimensions

   b) EXPLICIT CSG PLAN
      - Ordered sequence of boolean operations
      - Explicit coordinates for each translate/rotate
      - Description of what each operation "does" in the real world

   c) COORDINATE SYSTEM
      - Origin position and why
      - Print orientation (which face on build plate)
      - Main axes identification

   d) DIMENSIONAL VERIFICATION
      - Cross-check every critical dimension
      - Verify holes are through (h > thickness + epsilon)
      - Verify walls meet minimum thickness
      - Verify clearance between adjacent parts

3. REASONING RULES:
   - "Think in negative": for each subtractive feature, visualize the removed volume
   - "Think in cross-section": imagine cutting the part with a plane and describe what you see
   - "Think in print": imagine the part layer by layer from bottom to top
   - "Think in assembly": if there are multiple parts, describe how they assemble

4. PRIMITIVES CATALOG with OpenSCAD cheat-sheet and when to use each one.

5. EXAMPLES: Include 3 complete spatial reasoning examples for:
   - An L-bracket with holes
   - An enclosure with snap-fit
   - A concentric cylindrical adapter

Test the skill by creating a sample prompt and verify that the reasoning produced
is coherent and leads to correct OpenSCAD code.
```

---

## PROMPT 3: Skill 2 — OpenSCAD CodeGen

```
Implement Skill 2: openscad-codegen.

Create skills/openscad-codegen/SKILL.md that defines the rules for generating
high-quality OpenSCAD code. It must include:

1. MANDATORY TEMPLATE for each .scad file (like in CLAUDE.md but more detailed):
   - Header with metadata
   - Main parameters section (with type, range, comment [mm])
   - Print parameters section
   - Derived parameters section (calculated, with formula comment)
   - Separate modules for each logical component
   - assembly() module that composes everything
   - Final render call

2. CODE RULES:
   - Every variable: descriptive_name_snake_case
   - Every dimension: comment with units [mm] or [deg]
   - Every module: comment explaining what it physically represents
   - Use for() for repetitions, NEVER copy-paste
   - Boolean offset of 0.01mm to avoid z-fighting
   - $fn parameters: 32 for preview, 64 for production, 128 for threads/gears

3. PATTERN LIBRARY: Create separate template files in templates/:
   - templates/parametric_box.scad — Box with lid, optional snap-fit
   - templates/bracket_l.scad — L-bracket with ribs and holes
   - templates/enclosure.scad — PCB enclosure with openings
   - templates/snap_fit.scad — Cantilever snap-fit module
   - templates/threaded_insert.scad — Heat insert hole for M2/M3/M4/M5
   - templates/hinge.scad — Print-in-place hinge

   Each template must be 100% parametric and work standalone.

4. COMPLETE TOLERANCES TABLE for each type of fit.

5. ANTI-PATTERNS with explanation of why they fail and what to do instead.

Implement all template files and verify that each compiles without errors
with `openscad -o /dev/null template.scad 2>&1`.
```

---

## PROMPT 4: Skill 3 — Validate & Fix Loop

```
Implement Skill 3: openscad-validate.

This skill defines the automatic validation and correction loop.
Create skills/openscad-validate/SKILL.md with:

1. VALIDATION WORKFLOW:

   ```
   generate_code()
   for i in 1..5:
       result = compile(code)
       if result.success:
           if result.warnings:
               code = fix_warnings(code, result.warnings)
           else:
               return SUCCESS(code, result.stl)
       else:
           code = fix_errors(code, result.errors)
   return FAILURE("Max iterations reached", last_error)
   ```

2. COMMON ERROR CATALOG with automatic fixes:

   | OpenSCAD Error | Cause | Fix |
   |---|---|---|
   | "No top-level geometry" | Missing render() or assembly() | Add call |
   | "Object may not be a valid 2-manifold" | Non-closed mesh | Add 0.01 offset |
   | "undefined variable" | Missing variable | Search in context, define |
   | "WARNING: ... undefined operation" | Unsupported operation | Replace with equivalent |
   | "minkowski: child 0 is empty" | Empty geometry in minkowski | Verify child dimensions |
   | Unreasonable bounding box (>1000mm or <0.1mm) | Scale/units error | Recalculate dimensions |

3. POST-VALIDATION CHECKS:
   - Reasonable bounding box (alert if >300mm on any axis)
   - Volume > 0 (not an empty object)
   - Weight and print time estimate
   - Verify print orientation (suggest rotation if needed)

4. OUTPUT FORMAT:
   ```
   Compilation: OK
   Manifold: OK
   Bounding box: 45 x 30 x 25 mm
   Volume: 12.3 cm3
   Estimated weight: 15.1g (PLA, 20% infill)
   Estimated print time: ~1h 20min (0.2mm layer, 50mm/s)
   Recommended orientation: flat base on build plate
   ```

If the MCP openscad server is available, use it. Otherwise, define equivalent
bash commands as fallback.
```

---

## PROMPT 5: Skill 4 — Image to 3D

```
Implement Skill 4: image-to-3d.

Create skills/image-to-3d/SKILL.md that defines how to analyze images (photos, sketches,
technical drawings) to extract geometry and produce OpenSCAD code.

1. IMAGE ANALYSIS WORKFLOW:

   a) INPUT CLASSIFICATION:
      - Freehand sketch -> extract approximate shapes, ask for dimensions
      - Photo of real object -> reverse-engineering, estimate dimensions from references
      - Technical drawing -> extract dimensions, views, sections
      - CAD screenshot -> identify features and parameters

   b) GEOMETRIC EXTRACTION:
      - Identify primitive shapes (box, cylinders, spheres, cones)
      - Identify boolean operations (holes, pockets, fillets)
      - Identify symmetries (mirror, circular/linear patterns)
      - Estimate dimensional ratios between features

   c) DIMENSION ESTIMATION:
      - If reference objects present (coin, hand, known PCB) -> calculate scale
      - If dimensions partially known -> deduce the rest from ratios
      - If no reference -> ask the user for critical dimensions

   d) STRUCTURED OUTPUT:
      Generate a structured specification block that feeds into spatial reasoning:
      ```
      OBJECT: [name/description]
      ESTIMATED DIMENSIONS: [W x D x H mm]
      BASE SHAPE: [main primitive]
      FEATURES:
        1. [type] at [relative position] — [dimensions]
        2. ...
      SYMMETRIES: [axes of symmetry]
      NOTES: [peculiarities, undercuts, moving parts]
      ```

2. ANALYSIS PROMPT (template to use with the image):

   "Analyze this image to generate a printable 3D model:

   1. What kind of object is it? What is its function?
   2. What primitive geometric shapes make up the object?
   3. What are the approximate dimensions? (use visible references)
   4. What functional features are there? (holes, slots, clips, fillets)
   5. Are there exploitable symmetries?
   6. How should it be oriented for FDM printing?
   7. Are there parts that require supports?"

3. MULTI-VIEW HANDLING:
   If the user provides multiple photos/views of the same object, combine the information
   to build a more accurate 3D model. Map features across views.

4. EXPLICIT LIMITATIONS:
   - Complex organic shapes (sculptures, faces) -> NOT feasible with OpenSCAD
   - NURBS surfaces -> Suggest Fusion360/FreeCAD
   - Complex surface textures/patterns -> Suggest bitmap2surface approach
```

---

## PROMPT 6: Skill 5 — Print Profiles & Materials

```
Implement Skill 5: print-profiles.

Create skills/print-profiles/SKILL.md and skills/print-profiles/materials.json.

1. materials.json — Structured database:

{
  "PLA": {
    "temp_max_service": 50,
    "temp_nozzle": [190, 220],
    "temp_bed": [50, 60],
    "wall_min_mm": 1.2,
    "shrinkage_pct": [0.3, 0.5],
    "density_g_cm3": 1.24,
    "tensile_strength_mpa": 50,
    "impact_resistance": "low",
    "chemical_resistance": "low",
    "uv_resistance": "low",
    "food_safe": false,
    "chamber_required": false,
    "notes": "Easy to print, good detail, brittle"
  },
  // PETG, ABS, ASA, PC, Nylon (PA6, PA12), TPU (85A, 95A),
  // PLA-CF, PETG-CF, PA-CF, Tullomer, PC+CF
  // ... (complete all)
}

2. SKILL.md must:
   - Given a material and use case, automatically apply the correct constraints
   - Suggest the best material given a use case
   - Calculate estimated weight: volume * density * infill_factor
   - Calculate estimated print time based on volume and speed
   - Include specific rules for composites (Tullomer + PC wrapping):
     * Fiber orientation relative to loads
     * Service and deflection temperatures
     * Critical inter-layer adhesion
   - Printer profiles for:
     * Bambu Lab X1C / P1S / A1
     * Prusa MK4 / XL
     * Creality Ender 3 / K1
     * Voron 2.4 / Trident
     With print volumes, max speeds, special features

3. MATERIAL COMMANDS:
   `/material PLA` -> show spec sheet + apply constraints
   `/material compare PLA PETG` -> comparison table
   `/material suggest outdoor load-bearing` -> recommend material
```

---

## PROMPT 7: Skill 6 — Orchestrator + Final Test

```
Implement Skill 6: 3d-print-orchestrator.

This is the master skill that orchestrates all others.
Create skills/3d-print-orchestrator/SKILL.md that:

1. DEFINES THE COMPLETE WORKFLOW:

   User input (text and/or image)
   |
   +-- [If image present]
   |  +-> Read skills/image-to-3d/SKILL.md -> Image analysis
   |     Output: structured object specification
   |
   +-> Read skills/spatial-reasoning/SKILL.md -> Spatial reasoning
   |  Output: detailed CSG plan
   |
   +-> Read skills/print-profiles/SKILL.md -> Material selection + constraints
   |  Output: dimensional and design constraints applied
   |
   +-> Read skills/openscad-codegen/SKILL.md -> Code generation
   |  Output: complete parametric .scad file
   |
   +-> Read skills/openscad-validate/SKILL.md -> Validation + fix loop
   |  |  (use MCP openscad if available, otherwise bash)
   |  Output: validated .scad + .stl
   |
   +-> Final report with:
      - .scad file (parametric, commented)
      - .stl file (ready for slicer)
      - Bounding box, volume, estimated weight
      - Slicer instructions (orientation, supports, infill)
      - Notes on limitations and possible improvements

2. QUICK COMMANDS HANDLING (/box, /bracket, /enclosure, etc.)
   Each command bypasses the analysis and goes directly to generation with preset parameters.

3. INTERACTIVE MODE:
   If information is insufficient, ask in a structured way:
   "To complete the design, I need:
    [] External or internal dimensions? [mm]
    [] Material? [PLA/PETG/PC/...]
    [] Which face is the most aesthetically important?
    [] Are there mating parts? If so, what dimensions?"

4. FINAL TEST:
   After creating everything, test the complete pipeline with this case:

   "Create an enclosure for Arduino Uno Rev3 with:
   - Openings for USB-B and DC jack
   - M3 mounting holes (4 corners, compatible with PCB holes)
   - Ventilation grid on top
   - Snap-fit closure without screws
   - Material: PETG
   - Space for a small breadboard next to the Arduino"

   Verify that the code compiles, the STL is valid, and the dimensions
   are correct for a real Arduino Uno (68.6 x 53.4 mm PCB).

   If everything works, the pipeline is complete.
```

---

## Execution Notes

### How to use these prompts:

1. Create the project: `mkdir -p ~/projects/3dprint-pipeline && cd $_`
2. Copy `CLAUDE-3dprint.md` as `CLAUDE.md` in the root
3. Copy `openscad-pipeline-plan.md` in the root
4. Open Claude CLI: `claude`
5. Run the prompts in order (1->7)
6. Each prompt is self-contained and independently testable
7. Prompt 7 tests the pipeline end-to-end

### Estimated time:
- Prompt 1 (Setup + MCP): ~30-45 min
- Prompt 2-5 (Skills): ~15-20 min each
- Prompt 6 (Profiles + DB): ~20-30 min
- Prompt 7 (Orchestrator + Test): ~30-45 min
- **Total: ~2.5-3.5 hours**

### If something fails:
- The MCP server is optional: the bash fallback works perfectly
- Each skill is independent: you can skip one and come back later
- The .scad templates are the most important: always test them first
