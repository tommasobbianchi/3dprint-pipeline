"""Proxy endpoint for importing STEP files into Onshape documents.

Flow when element_id (current Part Studio) is provided:
  1. Delete previous Derived feature + previous source tab (if re-uploading)
  2. Upload STEP → Translations API creates a source Part Studio
  3. Poll until DONE → get source element ID
  4. Get current document microversion
  5. Add importDerived feature to current Part Studio referencing the source
  → Geometry appears directly in the user's current Part Studio
  → Source tab must remain (Derived maintains a live reference)

On re-upload, old source tab + old Derived feature are cleaned up first,
so only ONE extra tab exists at any time.

Fallback (no element_id):
  Creates a new Part Studio tab as before.
"""
import asyncio
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
    element_id: str | None = Field(
        default=None,
        description="Current Part Studio element — geometry is Derived into this tab",
    )
    derived_feature_id: str | None = Field(
        default=None,
        description="Previous Derived feature ID to delete before re-importing",
    )
    source_element_id: str | None = Field(
        default=None,
        description="Previous source Part Studio to delete on re-upload",
    )


class UploadResponse(BaseModel):
    success: bool
    translation_id: str | None = None
    element_id: str | None = None
    derived_feature_id: str | None = None
    source_element_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _poll_translation(client: httpx.AsyncClient, auth, translation_id: str) -> dict | None:
    """Poll translation status until DONE or FAILED. Returns result or None."""
    url = f"{ONSHAPE_API_BASE}/translations/{translation_id}"
    for _ in range(45):  # max 90s (45 * 2s)
        await asyncio.sleep(2)
        try:
            resp = await client.get(url, auth=auth, headers={"Accept": "application/json"})
            data = resp.json()
            state = data.get("requestState")
            if state == "DONE":
                return data
            if state == "FAILED":
                log.warning("Translation failed: %s", data.get("failureReason"))
                return None
        except Exception as e:
            log.warning("Poll error: %s", e)
    return None


async def _delete_element(client: httpx.AsyncClient, auth, did: str, wid: str, eid: str):
    """Delete an element (tab) from the document. Best-effort, non-fatal."""
    url = f"{ONSHAPE_API_BASE}/elements/d/{did}/w/{wid}/e/{eid}"
    try:
        resp = await client.delete(url, auth=auth, headers={"Accept": "application/json"})
        if resp.status_code < 300:
            log.info("Deleted element %s", eid)
        else:
            log.warning("Failed to delete element %s: %d", eid, resp.status_code)
    except Exception as e:
        log.warning("Delete element error: %s", e)


async def _delete_feature(
    client: httpx.AsyncClient, auth, did: str, wid: str, eid: str, fid: str
):
    """Delete a feature from a Part Studio. Best-effort, non-fatal."""
    url = f"{ONSHAPE_API_BASE}/partstudios/d/{did}/w/{wid}/e/{eid}/features/featureid/{fid}"
    try:
        resp = await client.delete(url, auth=auth, headers={"Accept": "application/json"})
        if resp.status_code < 300:
            log.info("Deleted feature %s from element %s", fid, eid)
        else:
            log.warning("Failed to delete feature %s: %d", fid, resp.status_code)
    except Exception as e:
        log.warning("Delete feature error: %s", e)


async def _get_microversion(client: httpx.AsyncClient, auth, did: str, wid: str) -> str | None:
    """Get the current document microversion."""
    url = f"{ONSHAPE_API_BASE}/documents/d/{did}/w/{wid}/currentmicroversion"
    try:
        resp = await client.get(url, auth=auth, headers={"Accept": "application/json"})
        return resp.json().get("microversion")
    except Exception as e:
        log.warning("Get microversion error: %s", e)
        return None


async def _add_derived_feature(
    client: httpx.AsyncClient,
    auth,
    did: str,
    wid: str,
    target_eid: str,
    source_eid: str,
    microversion: str,
) -> str | None:
    """Add an importDerived feature to target Part Studio referencing source.

    Returns the new feature ID, or None on failure.
    """
    url = f"{ONSHAPE_API_BASE}/partstudios/d/{did}/w/{wid}/e/{target_eid}/features"
    feature = {
        "btType": "BTMFeature-134",
        "featureType": "importDerived",
        "name": "CAD Generator Import",
        "namespace": "",
        "parameters": [
            {
                "btType": "BTMParameterBoolean-144",
                "parameterId": "newUI",
                "value": True,
            },
            {
                "btType": "BTMParameterReferencePartStudio-3302",
                "parameterId": "partStudio",
                "namespace": f"e{source_eid}::m{microversion}",
                "partQuery": {
                    "btType": "BTMParameterQueryList-148",
                    "parameterId": "partQuery",
                    "queries": [
                        {
                            "btType": "BTMIndividualQuery-138",
                            "queryString": "query = qUnion([ qEverything(EntityType.BODY)]);",
                        }
                    ],
                },
                "configuration": [],
                "partIdentity": {"btType": "BTPSOIdentity-2741", "theId": ""},
                "standardContentParametersId": "",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "parameterId": "preserveActiveSheetMetal",
                "value": False,
            },
            {
                "btType": "BTMParameterQueryList-148",
                "parameterId": "location",
                "queries": [],
                "filter": {"btType": "BTBodyTypeFilter-112", "bodyType": "MATE_CONNECTOR"},
            },
            {
                "btType": "BTMParameterEnum-145",
                "parameterId": "placement",
                "enumName": "DerivedPlacementType",
                "value": "AT_ORIGIN",
            },
            {
                "btType": "BTMParameterQuantity-147",
                "parameterId": "mateConnectorIndex",
                "isInteger": True,
                "expression": "-1",
            },
            {
                "btType": "BTMParameterQuantity-147",
                "parameterId": "mateConnectorId",
                "isInteger": False,
                "expression": "0",
            },
            {
                "btType": "BTMParameterQuantity-147",
                "parameterId": "mateConnectorIndexInFeature",
                "isInteger": True,
                "expression": "-1",
            },
            {
                "btType": "BTMParameterBoolean-144",
                "parameterId": "includeMateConnectors",
                "value": True,
            },
            {
                "btType": "BTMParameterBoolean-144",
                "parameterId": "includeProperties",
                "value": True,
            },
            {
                "btType": "BTMParameterQueryList-148",
                "parameterId": "parts",
                "queries": [],
            },
            {
                "btType": "BTMParameterDerived-864",
                "parameterId": "buildFunction",
                "namespace": "",
                "imports": [],
                "configuration": [],
            },
        ],
    }

    try:
        resp = await client.post(
            url,
            auth=auth,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={"feature": feature},
        )
        if resp.status_code >= 400:
            log.warning("Add derived feature failed: %d %s", resp.status_code, resp.text[:500])
            return None
        data = resp.json()
        feat = data.get("feature", {})
        fid = feat.get("featureId")
        status = data.get("featureState", {}).get("featureStatus")
        log.info("Derived feature added: id=%s status=%s", fid, status)
        return fid
    except Exception as e:
        log.warning("Add derived feature error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/api/upload-to-onshape", response_model=UploadResponse)
async def upload_to_onshape(req: UploadRequest):
    """Import STEP file into Onshape document.

    If element_id is provided (Onshape iframe context), the geometry is
    Derived into the current Part Studio so it appears in the user's
    active tab — no tab switching needed.

    The source Part Studio (created by translation) must remain alive
    because the Derived feature maintains a live reference. On re-upload,
    the old source + old Derived feature are cleaned up first.
    """
    log.info(
        "Upload request: doc=%s ws=%s element_id=%s derived_fid=%s source_eid=%s",
        req.document_id, req.workspace_id, req.element_id,
        req.derived_feature_id, req.source_element_id,
    )

    ak, sk = _load_onshape_keys()

    try:
        step_bytes = base64.b64decode(req.step_base64)
    except Exception as e:
        return UploadResponse(success=False, error=f"Invalid base64: {e}")

    auth = httpx.BasicAuth(ak, sk)

    async with httpx.AsyncClient(timeout=120) as client:
        # --- Step 1: Clean up previous upload (Derived feature + source tab) ---
        if req.derived_feature_id:
            await _delete_feature(
                client, auth, req.document_id, req.workspace_id,
                req.element_id, req.derived_feature_id,
            )
        if req.source_element_id:
            await _delete_element(
                client, auth, req.document_id, req.workspace_id,
                req.source_element_id,
            )

        # --- Step 2: Upload STEP via Translations API ---
        url = f"{ONSHAPE_API_BASE}/translations/d/{req.document_id}/w/{req.workspace_id}"
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

        log.info("Translation response: status=%d body=%s", resp.status_code, resp.text[:1000])

        if resp.status_code >= 400:
            return UploadResponse(
                success=False,
                error=f"Onshape API error ({resp.status_code}): {resp.text[:500]}",
            )

        data = resp.json()
        translation_id = data.get("id")
        log.info("Translation started: id=%s", translation_id)

        # --- Step 3: Poll until translation completes ---
        source_element_id = None
        if translation_id:
            result = await _poll_translation(client, auth, translation_id)
            if result:
                eids = result.get("resultElementIds") or []
                if eids:
                    source_element_id = eids[0]
                    log.info("Source element created: %s", source_element_id)

        if not source_element_id:
            return UploadResponse(
                success=False,
                translation_id=translation_id,
                error="Translation did not produce an element",
            )

        # --- If no target Part Studio, return the new element (legacy flow) ---
        if not req.element_id:
            return UploadResponse(
                success=True,
                translation_id=translation_id,
                element_id=source_element_id,
            )

        # --- Step 4: Get microversion and add Derived feature ---
        mv = await _get_microversion(client, auth, req.document_id, req.workspace_id)
        if not mv:
            return UploadResponse(
                success=True,
                translation_id=translation_id,
                element_id=source_element_id,
                error="Could not get microversion; geometry is in a new tab",
            )

        derived_fid = await _add_derived_feature(
            client, auth, req.document_id, req.workspace_id,
            req.element_id, source_element_id, mv,
        )

        if not derived_fid:
            return UploadResponse(
                success=True,
                translation_id=translation_id,
                element_id=source_element_id,
                error="Derived feature failed; geometry is in a new tab",
            )

        # Source element must stay alive (Derived maintains a live reference).
        # It will be cleaned up on the next re-upload.
        return UploadResponse(
            success=True,
            translation_id=translation_id,
            derived_feature_id=derived_fid,
            source_element_id=source_element_id,
        )
