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
