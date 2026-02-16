/**
 * Onshape integration helper — upload via backend proxy.
 *
 * Onshape injects URL params: documentId, workspaceOrVersionId, elementId
 * Upload goes through our backend (avoids CORS issues with Onshape API).
 *
 * The backend Derives the geometry into the current Part Studio so the user
 * never has to switch tabs. Temp Part Studios are cleaned up automatically.
 */
const OnshapeAPI = (() => {

  /** Get Onshape context from URL params (injected by Onshape iframe). */
  function getContext() {
    const params = new URLSearchParams(window.location.search);
    const documentId = params.get("documentId");
    const workspaceId = params.get("workspaceOrVersionId");
    const elementId = params.get("elementId");
    if (documentId && workspaceId) {
      return { documentId, workspaceId, elementId };
    }
    return null;
  }

  /**
   * Upload STEP file to Onshape via the backend proxy.
   *
   * When element_id is available (Onshape iframe), the backend:
   *   1. Cleans up previous source tab + Derived feature (if re-uploading)
   *   2. Uploads STEP → creates source Part Studio
   *   3. Adds a Derived feature to the current Part Studio
   *   → Source tab stays alive (Derived needs the live reference)
   *   → On next upload, old source + Derived are cleaned up
   */
  async function uploadSTEP(stepBase64, filename, derivedFeatureId, sourceElementId) {
    const ctx = getContext();
    if (!ctx) throw new Error("No Onshape document context (not in iframe?)");

    const resp = await fetch("/api/upload-to-onshape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        step_base64: stepBase64,
        filename: filename,
        document_id: ctx.documentId,
        workspace_id: ctx.workspaceId,
        element_id: ctx.elementId,
        derived_feature_id: derivedFeatureId || null,
        source_element_id: sourceElementId || null,
      }),
    });

    const data = await resp.json();
    if (!data.success) {
      throw new Error(data.error || "Upload failed");
    }
    return data;
  }

  return { getContext, uploadSTEP };
})();
