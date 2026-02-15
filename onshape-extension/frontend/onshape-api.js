/**
 * Onshape integration helper — upload via backend proxy.
 *
 * Onshape injects URL params: documentId, workspaceOrVersionId, elementId
 * Upload goes through our backend (avoids CORS issues with Onshape API).
 */
const OnshapeAPI = (() => {

  /** Get Onshape context from URL params (injected by Onshape iframe). */
  function getContext() {
    const params = new URLSearchParams(window.location.search);
    const documentId = params.get("documentId");
    const workspaceId = params.get("workspaceOrVersionId");
    if (documentId && workspaceId) {
      return { documentId, workspaceId };
    }
    return null;
  }

  /**
   * Upload STEP file to Onshape via the backend proxy.
   * The backend has the API keys and calls Onshape server-side.
   */
  async function uploadSTEP(stepBase64, filename) {
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
