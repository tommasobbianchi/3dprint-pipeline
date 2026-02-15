"""CadQuery execution — subprocess with validation and STEP export."""
import base64
import os
import re
import subprocess
import tempfile
from pathlib import Path

from ..config import EXEC_TIMEOUT

MEASUREMENT_CODE = """
# === MEASUREMENT ===
_r = result
_bb = _r.val().BoundingBox()
_vol = _r.val().Volume()
_solids = len(_r.val().Solids())
print(f"BBOX:{_bb.xmin:.2f},{_bb.ymin:.2f},{_bb.zmin:.2f},{_bb.xmax:.2f},{_bb.ymax:.2f},{_bb.zmax:.2f}")
print(f"SIZE:{_bb.xlen:.2f}x{_bb.ylen:.2f}x{_bb.zlen:.2f}")
print(f"VOLUME:{_vol:.2f}")
print(f"SOLIDS:{_solids}")
"""

EXPORT_CODE = """
# === EXPORT ===
import os as _os
_out = _os.environ.get("OUT_DIR", ".")
import cadquery as _cq
_cq.exporters.export(result, _os.path.join(_out, "output.step"))
_cq.exporters.export(result, _os.path.join(_out, "output.stl"))
"""


def parse_metrics(stdout: str) -> dict:
    """Parse BBOX, SIZE, VOLUME, SOLIDS from CadQuery output."""
    metrics = {
        "bounding_box": None,
        "size": None,
        "volume": None,
        "solid_count": None,
    }
    bbox_match = re.search(
        r"BBOX:([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)",
        stdout,
    )
    if bbox_match:
        metrics["bounding_box"] = {
            "min": [float(bbox_match.group(i)) for i in range(1, 4)],
            "max": [float(bbox_match.group(i)) for i in range(4, 7)],
        }
    size_match = re.search(r"SIZE:([-\d.]+)x([-\d.]+)x([-\d.]+)", stdout)
    if size_match:
        metrics["size"] = [float(size_match.group(i)) for i in range(1, 4)]
    vol_match = re.search(r"VOLUME:([-\d.]+)", stdout)
    if vol_match:
        metrics["volume"] = float(vol_match.group(1))
    sol_match = re.search(r"SOLIDS:(\d+)", stdout)
    if sol_match:
        metrics["solid_count"] = int(sol_match.group(1))
    return metrics


async def execute_and_export(code: str) -> dict:
    """Execute CadQuery code in subprocess, return STEP bytes + metrics.

    Returns dict with keys: success, step_base64, stl_base64, metrics, error
    """
    with tempfile.TemporaryDirectory(prefix="cadgen_") as tmpdir:
        script_path = Path(tmpdir) / "code.py"
        full_code = code + "\n" + MEASUREMENT_CODE + "\n" + EXPORT_CODE
        script_path.write_text(full_code)

        try:
            proc = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT,
                env={**os.environ, "OUT_DIR": tmpdir},
            )
            success = proc.returncode == 0
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "step_base64": None,
                "stl_base64": None,
                "metrics": None,
                "error": f"Execution timed out after {EXEC_TIMEOUT}s",
            }

        if not success:
            return {
                "success": False,
                "step_base64": None,
                "stl_base64": None,
                "metrics": None,
                "error": stderr[:500] if stderr else "CadQuery execution failed",
            }

        metrics = parse_metrics(stdout)

        # Validate single solid
        if metrics["solid_count"] is not None and metrics["solid_count"] != 1:
            return {
                "success": False,
                "step_base64": None,
                "stl_base64": None,
                "metrics": metrics,
                "error": f"Expected 1 solid, got {metrics['solid_count']}",
            }

        # Read STEP file
        step_path = Path(tmpdir) / "output.step"
        stl_path = Path(tmpdir) / "output.stl"

        step_b64 = None
        stl_b64 = None
        if step_path.exists():
            step_b64 = base64.b64encode(step_path.read_bytes()).decode()
        if stl_path.exists():
            stl_b64 = base64.b64encode(stl_path.read_bytes()).decode()

        if not step_b64:
            return {
                "success": False,
                "step_base64": None,
                "stl_base64": None,
                "metrics": metrics,
                "error": "STEP file not produced",
            }

        return {
            "success": True,
            "step_base64": step_b64,
            "stl_base64": stl_b64,
            "metrics": metrics,
            "error": None,
        }
