"""Generate endpoint — text prompt to STEP file."""
from pydantic import BaseModel, Field

from fastapi import APIRouter

from ..services.skill_loader import load_system_prompt
from ..services.claude_service import generate_cadquery_code
from ..services.cadquery_service import execute_and_export

router = APIRouter()

_system_prompt = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = load_system_prompt()
    return _system_prompt


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    material: str = Field(default="PLA")


class GenerateResponse(BaseModel):
    success: bool
    step_base64: str | None = None
    stl_base64: str | None = None
    filename: str | None = None
    metrics: dict | None = None
    error: str | None = None
    model: str | None = None


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    system_prompt = _get_system_prompt()

    # Step 1: Generate CadQuery code via Claude
    claude_result = await generate_cadquery_code(
        system_prompt, req.prompt, req.material
    )
    if claude_result["error"]:
        return GenerateResponse(
            success=False,
            error=claude_result["error"],
            model=claude_result["model"],
        )

    # Step 2: Execute CadQuery and produce STEP
    exec_result = await execute_and_export(claude_result["code"])
    if not exec_result["success"]:
        return GenerateResponse(
            success=False,
            error=exec_result["error"],
            metrics=exec_result["metrics"],
            model=claude_result["model"],
        )

    # Generate filename from prompt
    slug = req.prompt[:40].lower().replace(" ", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    filename = f"{slug}.step"

    return GenerateResponse(
        success=True,
        step_base64=exec_result["step_base64"],
        stl_base64=exec_result["stl_base64"],
        filename=filename,
        metrics=exec_result["metrics"],
        model=claude_result["model"],
    )
