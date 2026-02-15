"""Proxy endpoint for importing STEP files into Onshape documents."""
import base64
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import ONSHAPE_KEYS_FILE, ONSHAPE_API_BASE

log = logging.getLogger(__name__)

router = APIRouter()


def _load_onshape_keys() -> tuple[str, str]:
    """Load Onshape API keys from disk. Returns (access_key, secret_key)."""
    try:
        text = ONSHAPE_KEYS_FILE.read_text()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Onshape API keys not found at {ONSHAPE_KEYS_FILE}",
        )
    keys = {}
    for line in text.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()
    ak = keys.get("ACCESS_KEY")
    sk = keys.get("SECRET_KEY")
    if not ak or not sk:
        raise HTTPException(
            status_code=500, detail="Onshape API keys file missing ACCESS_KEY or SECRET_KEY"
        )
    return ak, sk


class UploadRequest(BaseModel):
    step_base64: str = Field(..., description="Base64-encoded STEP file")
    filename: str = Field(default="output.step")
    document_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)


class UploadResponse(BaseModel):
    success: bool
    translation_id: str | None = None
    error: str | None = None


@router.post("/api/upload-to-onshape", response_model=UploadResponse)
async def upload_to_onshape(req: UploadRequest):
    """Import STEP file into Onshape document via the Translations API.

    This creates a new Part Studio element with the imported geometry,
    unlike blob upload which just stores the raw file.
    """
    ak, sk = _load_onshape_keys()

    # Decode STEP bytes
    try:
        step_bytes = base64.b64decode(req.step_base64)
    except Exception as e:
        return UploadResponse(success=False, error=f"Invalid base64: {e}")

    # Onshape Translations API — imports file and creates native geometry
    url = f"{ONSHAPE_API_BASE}/translations/d/{req.document_id}/w/{req.workspace_id}"

    auth = httpx.BasicAuth(ak, sk)

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                url,
                auth=auth,
                files={"file": (req.filename, step_bytes, "application/octet-stream")},
                data={
                    "translate": "true",
                    "flattenAssemblies": "true",
                    "allowFaultyParts": "true",
                    "formatName": "",
                },
                headers={"Accept": "application/json"},
            )
        except httpx.RequestError as e:
            return UploadResponse(success=False, error=f"Network error: {e}")

    log.info("Onshape API response: status=%d body=%s", resp.status_code, resp.text[:1000])

    if resp.status_code >= 400:
        return UploadResponse(
            success=False,
            error=f"Onshape API error ({resp.status_code}): {resp.text[:500]}",
        )

    data = resp.json()
    log.info("Translation started: id=%s requestState=%s", data.get("id"), data.get("requestState"))
    return UploadResponse(
        success=True,
        translation_id=data.get("id"),
    )
