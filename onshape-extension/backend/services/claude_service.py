"""Claude CLI integration — prompt to CadQuery code generation.

Uses `claude --print` (Claude Code CLI) which authenticates via the user's
Max/Pro subscription.  No separate API key required.
"""

import asyncio
import os
import re

from ..config import CLAUDE_CLI, CLAUDE_MODEL, CLAUDE_TIMEOUT

CODE_WRAPPER = """You are a CadQuery code generator. Generate ONLY a complete, runnable Python CadQuery script.

CRITICAL RULES:
- Output ONLY Python code inside a single ```python``` block
- Do NOT explain, validate, execute, or export — just output the code
- The script must assign the final shape to a variable named `result`
- Include proper parametric variables with [mm] comments
- Export to "output.step" and "output.stl" at the end
- Follow all CadQuery best practices from your system prompt

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
    except Exception as e:
        return {
            "code": None,
            "response_text": None,
            "model": CLAUDE_MODEL,
            "error": f"Claude CLI error: {e}",
        }
