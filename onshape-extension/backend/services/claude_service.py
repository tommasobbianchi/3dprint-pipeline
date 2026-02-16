"""Claude CLI integration — prompt to CadQuery code generation.

Uses `claude --print` (Claude Code CLI) which authenticates via the user's
Max/Pro subscription.  No separate API key required.
"""

import asyncio
import os
import re

import logging

from ..config import CLAUDE_CLI, CLAUDE_MODEL, CLAUDE_TIMEOUT

log = logging.getLogger(__name__)

DIMENSION_LOOKUP_PROMPT = """You are a dimension lookup tool. Given the user's design request, identify the real-world objects referenced and return their EXACT physical dimensions in millimeters.

RULES:
- Return ONLY a structured text block — no explanations
- Use manufacturer specifications, not estimates
- Include ALL relevant dimensions for 3D modeling: length, width, thickness, corner radius, port positions, camera module size, button locations, mounting holes, etc.
- If multiple objects are referenced, list dimensions for each
- If no specific real-world object is mentioned, return "NO_LOOKUP_NEEDED"

FORMAT:
```
OBJECT: [name]
  length: [mm]
  width: [mm]
  thickness: [mm]
  corner_radius: [mm]
  [feature]: [dimension]
  ...
```

User request:
"""

MODIFY_WRAPPER = """You are a CadQuery code modifier. You will receive existing CadQuery code and a modification request.

CRITICAL RULES:
- Output ONLY the COMPLETE modified Python code inside a single ```python``` block
- MODIFY the existing code — do NOT rewrite from scratch
- Preserve the existing code structure, variable naming style, and comments
- Keep all parameters that are not affected by the modification
- The script must assign the final shape to a variable named `result`
- Export to "output.step" and "output.stl" at the end

FILLET SAFETY (most common crash cause):
- ALWAYS fillet primitives BEFORE boolean ops (union/cut) and BEFORE shell()
- NEVER use .edges("|Z").fillet(r) after union(), cut(), or shell() — OCC kernel WILL crash
- For hollowing: fillet the solid box first, THEN shell(), or use outer.cut(cavity) approach
- If post-boolean fillet is essential, use NearestToPointSelector targeting ONE specific edge

THREAD GENERATION (CadQuery has no .thread() — use OCC BRepOffsetAPI_MakePipeShell):
- NEVER use cq.Solid.sweep() — it twists the V-profile, producing malformed threads
- Use BRepOffsetAPI_MakePipeShell + gp_Dir(0,0,1) binormal + core.union(thread) pattern
- Core radius = r_minor + 0.05mm (overlap required for clean boolean)
- Common pitches: M3=0.5, M4=0.7, M5=0.8, M6=1.0, M8=1.25, M10=1.5, M12=1.75, M16=2.0, M20=2.5

EXISTING CODE:
```python
{code}
```

MODIFICATION REQUEST:
"""

CODE_WRAPPER = """You are a CadQuery code generator. Generate ONLY a complete, runnable Python CadQuery script.

CRITICAL RULES:
- Output ONLY Python code inside a single ```python``` block
- Do NOT explain, validate, execute, or export — just output the code
- The script must assign the final shape to a variable named `result`
- Include proper parametric variables with [mm] comments
- Export to "output.step" and "output.stl" at the end
- Follow all CadQuery best practices from your system prompt

FILLET SAFETY (most common crash cause):
- ALWAYS fillet primitives BEFORE boolean ops (union/cut) and BEFORE shell()
- NEVER use .edges("|Z").fillet(r) after union(), cut(), or shell() — OCC kernel WILL crash
- For hollowing: fillet the solid box first, THEN shell(), or use outer.cut(cavity) approach
- If post-boolean fillet is essential, use NearestToPointSelector targeting ONE specific edge

THREAD GENERATION (CadQuery has no .thread() — use OCC BRepOffsetAPI_MakePipeShell):
- NEVER use cq.Solid.sweep() for threads — it twists the V-profile, producing malformed geometry
- ALWAYS use BRepOffsetAPI_MakePipeShell with gp_Dir(0,0,1) binormal to keep profile radially oriented
- Core cylinder must be r_minor + 0.05mm to ensure boolean overlap (coincident surfaces fail)

ISO metric thread pattern (builds a centered threaded rod):
```
import math
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCP.gp import gp_Dir

H = pitch * math.sqrt(3) / 2
r_major = d_nominal / 2
r_minor = r_major - 5 * H / 8
r_pitch = (r_major + r_minor) / 2

# Centered helix from -length/2 to +length/2
helix = cq.Wire.makeHelix(pitch, length, r_pitch, center=cq.Vector(0, 0, -length / 2))
profile = (cq.Workplane("XZ")
    .moveTo(r_minor, -pitch / 4)
    .lineTo(r_major, 0)
    .lineTo(r_minor, pitch / 4)
    .close().wires().val())

# Sweep with Z-axis binormal — keeps V-profile radially flat
builder = BRepOffsetAPI_MakePipeShell(helix.wrapped)
builder.SetMode(gp_Dir(0, 0, 1))
builder.Add(profile.wrapped, False, False)
builder.Build()
builder.MakeSolid()
thread_shape = cq.Shape.cast(builder.Shape())

# Core with 0.05mm overlap for clean boolean (coincident surfaces fail)
core = cq.Workplane("XY").cylinder(length, r_minor + 0.05)
threaded_rod = core.union(cq.Workplane().newObject([thread_shape]).translate((0, 0, -length / 2)))
```
For internal threads: build the rod, then body.cut(threaded_rod).
For external threads: threaded_rod IS the bolt shaft.
Common pitches: M3=0.5, M4=0.7, M5=0.8, M6=1.0, M8=1.25, M10=1.5, M12=1.75, M16=2.0, M20=2.5

User request:
"""


def extract_python_code(response_text: str) -> str | None:
    """Extract the first Python code block from Claude's response."""
    # Try ```python ... ``` first
    match = re.search(r"```python\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try generic ``` ... ```
    match = re.search(r"```\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        code = match.group(1).strip()
        if "import cadquery" in code:
            return code
    # Fallback: look for import cadquery in raw text
    if "import cadquery" in response_text:
        lines = response_text.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if "import cadquery" in line:
                in_code = True
            if in_code:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines)
    return None


async def generate_cadquery_code(
    system_prompt: str,
    user_prompt: str,
    material: str = "PLA",
) -> dict:
    """Call Claude CLI (--print) and return extracted CadQuery code.

    Returns dict with keys: code, response_text, model, error
    """
    full_prompt = CODE_WRAPPER + user_prompt
    if material != "PLA":
        full_prompt += f"\n\nMaterial: {material}"

    # Build environment — remove CLAUDECODE to avoid nesting check
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI,
            "--print",
            "--system-prompt", system_prompt,
            "--model", CLAUDE_MODEL,
            "--tools", "",
            "--no-session-persistence",
            full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=CLAUDE_TIMEOUT
        )
        response_text = stdout.decode()

        if proc.returncode != 0:
            error_text = stderr.decode()[:500]
            return {
                "code": None,
                "response_text": None,
                "model": CLAUDE_MODEL,
                "error": f"Claude CLI error (exit {proc.returncode}): {error_text}",
            }

        code = extract_python_code(response_text)
        return {
            "code": code,
            "response_text": response_text,
            "model": CLAUDE_MODEL,
            "error": None if code else "No Python code extracted from response",
        }
    except asyncio.TimeoutError:
        return {
            "code": None,
            "response_text": None,
            "model": CLAUDE_MODEL,
            "error": f"Claude CLI timed out after {CLAUDE_TIMEOUT}s",
        }
    except Exception as e:  # generate_cadquery_code
        return {
            "code": None,
            "response_text": None,
            "model": CLAUDE_MODEL,
            "error": f"Claude CLI error: {e}",
        }


async def modify_cadquery_code(
    system_prompt: str,
    previous_code: str,
    modification_prompt: str,
    material: str = "PLA",
) -> dict:
    """Call Claude CLI to modify existing CadQuery code.

    Returns dict with keys: code, response_text, model, error
    """
    full_prompt = MODIFY_WRAPPER.format(code=previous_code) + modification_prompt
    if material != "PLA":
        full_prompt += f"\n\nMaterial: {material}"

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI,
            "--print",
            "--system-prompt", system_prompt,
            "--model", CLAUDE_MODEL,
            "--tools", "",
            "--no-session-persistence",
            full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=CLAUDE_TIMEOUT
        )
        response_text = stdout.decode()

        if proc.returncode != 0:
            error_text = stderr.decode()[:500]
            return {
                "code": None,
                "response_text": None,
                "model": CLAUDE_MODEL,
                "error": f"Claude CLI error (exit {proc.returncode}): {error_text}",
            }

        code = extract_python_code(response_text)
        return {
            "code": code,
            "response_text": response_text,
            "model": CLAUDE_MODEL,
            "error": None if code else "No Python code extracted from response",
        }
    except asyncio.TimeoutError:
        return {
            "code": None,
            "response_text": None,
            "model": CLAUDE_MODEL,
            "error": f"Claude CLI timed out after {CLAUDE_TIMEOUT}s",
        }
    except Exception as e:  # modify_cadquery_code
        return {
            "code": None,
            "response_text": None,
            "model": CLAUDE_MODEL,
            "error": f"Claude CLI error: {e}",
        }


SHAPE_VALIDATION_PROMPT = """You are a 3D shape validator. You receive SVG wireframe views of a generated 3D-printable part and the original design request. Determine if the shape correctly represents what was requested.

ORIGINAL REQUEST: {prompt}

BOUNDING BOX: {size_x:.1f} x {size_y:.1f} x {size_z:.1f} mm
VOLUME: {volume:.0f} mm³

ISOMETRIC VIEW (SVG):
{svg_iso}

FRONT VIEW (SVG):
{svg_front}

IMPORTANT: Thread features (helical thread geometry) appear as dense overlapping curves in wireframe SVGs. If the request mentions threads and you see complex helical/dense curves around a hole or cylinder, the threads ARE present — do NOT mark them as missing. A cylindrical hole with surrounding helical curves = threaded hole.

Answer in EXACTLY this format (one line each, no extra text):
CATEGORY: <object type — e.g. bracket, enclosure, stool, gear, tube, plate, phone_case, mount, spacer, or "custom">
MATCH: <YES or NO — does the shape match the request?>
MISSING: <comma-separated list of missing/wrong features, or NONE>
PROPORTIONS: <OK, or list of proportion issues>
CONFIDENCE: <1-10 integer>
FIX: <one-line fix instruction if CONFIDENCE < 7, otherwise NONE>
"""


def _parse_validation_response(response: str) -> dict:
    """Parse the structured validation response into a dict."""
    result = {
        "valid": True,
        "confidence": 10,
        "category": None,
        "match": True,
        "missing": None,
        "proportions": None,
        "critique": None,
        "error": None,
    }

    for line in response.splitlines():
        line = line.strip()
        if line.startswith("CATEGORY:"):
            result["category"] = line.split(":", 1)[1].strip().lower()
        elif line.startswith("MATCH:"):
            val = line.split(":", 1)[1].strip().upper()
            result["match"] = val.startswith("YES")
        elif line.startswith("MISSING:"):
            val = line.split(":", 1)[1].strip()
            if val.upper() != "NONE":
                result["missing"] = val
        elif line.startswith("PROPORTIONS:"):
            val = line.split(":", 1)[1].strip()
            if val.upper() != "OK":
                result["proportions"] = val
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("FIX:"):
            val = line.split(":", 1)[1].strip()
            if val.upper() != "NONE":
                result["critique"] = val

    result["valid"] = result["confidence"] >= 7 and result["match"]

    # Build critique from missing + proportions if FIX line was empty
    if not result["valid"] and not result["critique"]:
        parts = []
        if result["missing"]:
            parts.append(f"Missing features: {result['missing']}")
        if result["proportions"]:
            parts.append(f"Proportion issues: {result['proportions']}")
        if parts:
            result["critique"] = ". ".join(parts)

    return result


async def validate_shape_visually(
    prompt: str,
    svg_iso: str,
    svg_front: str,
    metrics: dict,
) -> dict:
    """Validate a generated 3D shape by sending SVG views to Claude.

    Returns dict with: valid, confidence, category, match, missing,
    proportions, critique, error
    """
    size = metrics.get("size") or [0, 0, 0]
    volume = metrics.get("volume") or 0

    full_prompt = SHAPE_VALIDATION_PROMPT.format(
        prompt=prompt,
        size_x=size[0], size_y=size[1], size_z=size[2],
        volume=volume,
        svg_iso=svg_iso or "(not available)",
        svg_front=svg_front or "(not available)",
    )

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI,
            "--print",
            "--model", CLAUDE_MODEL,
            "--tools", "",
            "--no-session-persistence",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=full_prompt.encode()), timeout=60
        )
        response = stdout.decode().strip()

        if proc.returncode != 0 or not response:
            log.warning("Visual validation failed (exit %d)", proc.returncode)
            return {"valid": True, "confidence": 0, "category": None,
                    "critique": None, "error": "validation call failed"}

        return _parse_validation_response(response)

    except asyncio.TimeoutError:
        log.warning("Visual validation timed out")
        return {"valid": True, "confidence": 0, "category": None,
                "critique": None, "error": "validation timed out"}
    except Exception as e:
        log.warning("Visual validation error: %s", e)
        return {"valid": True, "confidence": 0, "category": None,
                "critique": None, "error": str(e)}


async def lookup_dimensions(user_prompt: str) -> str | None:
    """Fast Claude call to look up real-world dimensions for objects in the prompt.

    This is the dynamic "dimension lookup tool" — it queries Claude's training
    knowledge for exact manufacturer specifications of any real-world object.
    No static database needed; works for any object Claude knows about.

    Returns formatted dimension text to inject into the code generation prompt,
    or None if no lookup was needed or the call failed.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI,
            "--print",
            "--model", "haiku",  # Fast model for lookup
            "--tools", "",
            "--no-session-persistence",
            DIMENSION_LOOKUP_PROMPT + user_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=30  # Short timeout for lookup
        )
        response = stdout.decode().strip()

        if proc.returncode != 0 or not response:
            log.warning("Dimension lookup failed (exit %d)", proc.returncode)
            return None

        if "NO_LOOKUP_NEEDED" in response:
            return None

        log.info("Dimension lookup returned %d chars", len(response))
        return response

    except asyncio.TimeoutError:
        log.warning("Dimension lookup timed out")
        return None
    except Exception as e:
        log.warning("Dimension lookup error: %s", e)
        return None
