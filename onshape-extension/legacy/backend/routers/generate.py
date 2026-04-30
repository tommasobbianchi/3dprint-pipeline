"""Generate endpoint — text prompt to STEP file with auto-retry."""
import asyncio
import logging

from pydantic import BaseModel, Field

from fastapi import APIRouter

from ..services.skill_loader import load_system_prompt
from ..services.claude_service import (
    generate_cadquery_code, modify_cadquery_code, lookup_dimensions,
    validate_shape_visually,
)
from ..services.reference_loader import find_matching_references
from ..services.cadquery_service import execute_and_export

router = APIRouter()
log = logging.getLogger(__name__)

MAX_AUTO_RETRIES = 2

_system_prompt = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = load_system_prompt()
    return _system_prompt


def diagnose_error(error: str, metrics: dict | None) -> str:
    """Map execution error to a targeted fix instruction for Claude."""
    if not error:
        return "Fix the error in this code."

    if "StdFail_NotDone" in error:
        return (
            "The .fillet() call crashed the OCC kernel (StdFail_NotDone). "
            "Move ALL .fillet() calls BEFORE any union()/cut()/shell() operations. "
            "If a post-boolean fillet is essential, use NearestToPointSelector "
            "targeting ONE specific edge. Never use broad selectors like "
            '.edges("|Z").fillet(r) after boolean ops.'
        )

    if metrics and metrics.get("solid_count") is not None and metrics["solid_count"] != 1:
        n = metrics["solid_count"]
        return (
            f"Got {n} disconnected solids instead of 1. "
            "Ensure all union() features overlap the parent body by at least 0.1mm. "
            "Remember: Workplane('XZ').extrude(d) goes in the -Y direction. "
            "Check that features are positioned within the body's coordinate span."
        )

    if "SyntaxError" in error:
        return f"Fix this Python syntax error:\n{error}"

    if "Wire not closed" in error:
        return (
            "Wire not closed error. Check that polyline points form a closed loop "
            "with no coincident consecutive points and no self-intersections."
        )

    if "no output" in error.lower() or "STEP file not produced" in error:
        return (
            "Code ran but produced no geometry. Ensure the `result` variable "
            "holds a valid CadQuery Workplane object with solid geometry."
        )

    # Generic: include the traceback so Claude can diagnose
    return f"Fix this runtime error:\n{error}"


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    material: str = Field(default="PLA")
    previous_code: str | None = Field(default=None, max_length=50000)


class GenerateResponse(BaseModel):
    success: bool
    step_base64: str | None = None
    stl_base64: str | None = None
    filename: str | None = None
    metrics: dict | None = None
    error: str | None = None
    model: str | None = None
    code: str | None = None
    attempts: int = 1
    visual_check: dict | None = None


async def _enrich_prompt(prompt: str) -> str:
    """Enrich the user prompt with real-world dimensions from two sources.

    Runs in parallel:
    1. Dynamic lookup — fast Claude call for any real-world object (phones, etc.)
    2. Static references — keyword-matched hardware standards (fasteners, bearings, PCBs)
    """
    dynamic_task = asyncio.create_task(lookup_dimensions(prompt))
    static_refs = find_matching_references(prompt)

    dynamic_dims = await dynamic_task

    parts = []
    if dynamic_dims:
        parts.append(dynamic_dims)
        log.info("Dynamic dimension lookup: %d chars", len(dynamic_dims))
    if static_refs:
        parts.append(static_refs)
        log.info("Static reference match: %d chars", len(static_refs))

    if not parts:
        return prompt

    return "\n\n".join(parts) + "\n\nUser request:\n" + prompt


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    system_prompt = _get_system_prompt()

    # Step 0: Enrich prompt with real-world dimensions (only for new generations)
    enriched_prompt = req.prompt
    if not req.previous_code:
        enriched_prompt = await _enrich_prompt(req.prompt)

    # Step 1: Generate or modify CadQuery code via Claude
    if req.previous_code:
        claude_result = await modify_cadquery_code(
            system_prompt, req.previous_code, req.prompt, req.material
        )
    else:
        claude_result = await generate_cadquery_code(
            system_prompt, enriched_prompt, req.material
        )

    if claude_result["error"] or not claude_result["code"]:
        return GenerateResponse(
            success=False,
            error=claude_result["error"],
            model=claude_result["model"],
            code=claude_result["code"],
        )

    code = claude_result["code"]
    last_error = None
    last_metrics = None
    exec_ok = None
    total_attempts = 0

    # Step 2: Execute with auto-retry loop
    for attempt in range(MAX_AUTO_RETRIES + 1):
        exec_result = await execute_and_export(code)
        total_attempts = attempt + 1

        if exec_result["success"]:
            if attempt > 0:
                log.info("Auto-retry succeeded on attempt %d", attempt + 1)
            exec_ok = exec_result
            break

        last_error = exec_result["error"]
        last_metrics = exec_result["metrics"]

        # Auto-retry: ask Claude to fix the error
        if attempt < MAX_AUTO_RETRIES:
            fix_instruction = diagnose_error(last_error, last_metrics)
            log.info(
                "Auto-retry %d/%d: %s",
                attempt + 1, MAX_AUTO_RETRIES,
                fix_instruction[:80],
            )
            fix_result = await modify_cadquery_code(
                system_prompt, code, fix_instruction, req.material
            )
            if fix_result["error"] or not fix_result["code"]:
                break
            code = fix_result["code"]

    if not exec_ok:
        return GenerateResponse(
            success=False,
            error=last_error,
            metrics=last_metrics,
            model=claude_result["model"],
            code=code,
            attempts=total_attempts,
        )

    # Step 3: Visual shape validation (new generations only)
    visual_check = None
    if not req.previous_code and exec_ok.get("svg_iso"):
        log.info("Running visual shape validation")
        visual_check = await validate_shape_visually(
            req.prompt,
            exec_ok["svg_iso"],
            exec_ok["svg_front"],
            exec_ok["metrics"],
        )
        log.info(
            "Visual check: confidence=%s category=%s valid=%s",
            visual_check.get("confidence"),
            visual_check.get("category"),
            visual_check.get("valid"),
        )

        # Visual retry: if shape is wrong and we have a critique, fix once
        if not visual_check["valid"] and visual_check.get("critique"):
            log.info("Visual retry: %s", visual_check["critique"])
            fix_result = await modify_cadquery_code(
                system_prompt, code, visual_check["critique"], req.material
            )
            if fix_result.get("code"):
                retry_exec = await execute_and_export(fix_result["code"])
                total_attempts += 1
                if retry_exec["success"]:
                    log.info("Visual retry succeeded")
                    code = fix_result["code"]
                    exec_ok = retry_exec
                    visual_check["retried"] = True
                else:
                    log.info("Visual retry failed — keeping original shape")
                    visual_check["retried"] = False

    slug = req.prompt[:40].lower().replace(" ", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    filename = f"{slug}.step"

    return GenerateResponse(
        success=True,
        step_base64=exec_ok["step_base64"],
        stl_base64=exec_ok["stl_base64"],
        filename=filename,
        metrics=exec_ok["metrics"],
        model=claude_result["model"],
        code=code,
        attempts=total_attempts,
        visual_check=visual_check,
    )
