"""Health check endpoint."""
import subprocess

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health():
    # Check CadQuery availability
    cq_ok = False
    try:
        proc = subprocess.run(
            ["python3", "-c", "import cadquery; print('ok')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        cq_ok = proc.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return {"status": "ok", "cadquery": cq_ok}
