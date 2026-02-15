"""Materials endpoint — returns available materials from materials.json."""
import json

from fastapi import APIRouter

from ..config import MATERIALS_FILE

router = APIRouter()

_materials_cache = None


def _load_materials() -> dict:
    global _materials_cache
    if _materials_cache is None:
        with open(MATERIALS_FILE) as f:
            _materials_cache = json.load(f)
    return _materials_cache


@router.get("/api/materials")
async def get_materials():
    data = _load_materials()
    # Return simplified list for the dropdown
    materials = []
    for key, info in data.items():
        materials.append({
            "id": key,
            "name": info["full_name"],
            "wall_min_mm": info["wall_min_mm"],
            "temp_max_service": info["temp_max_service"],
        })
    return {"materials": materials}
