/**
 * Onshape REST API helper — blob upload for STEP files.
 *
 * Auth: Basic (API key pair) stored in localStorage.
 * Onshape injects URL params: documentId, workspaceOrVersionId, elementId
 */
const OnshapeAPI = (() => {
  const BASE = "https://cad.onshape.com/api/v6";

  function getKeys() {
    const ak = localStorage.getItem("onshape_access_key");
    const sk = localStorage.getItem("onshape_secret_key");
    if (ak && sk) return { accessKey: ak, secretKey: sk };
    return null;
  }

  function saveKeys(accessKey, secretKey) {
    localStorage.setItem("onshape_access_key", accessKey);
    localStorage.setItem("onshape_secret_key", secretKey);
  }

  function clearKeys() {
    localStorage.removeItem("onshape_access_key");
    localStorage.removeItem("onshape_secret_key");
  }

  function hasKeys() {
    return getKeys() !== null;
  }

  function getAuthHeader() {
    const keys = getKeys();
    if (!keys) return null;
    return "Basic " + btoa(keys.accessKey + ":" + keys.secretKey);
  }

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
   * Upload STEP file as a blob element in the Onshape document.
   * Returns the translation status URL or throws.
   */
  async function uploadSTEP(stepBase64, filename) {
    const auth = getAuthHeader();
    if (!auth) throw new Error("No Onshape API keys configured");

    const ctx = getContext();
    if (!ctx) throw new Error("No Onshape document context (not in iframe?)");

    // Decode base64 to blob
    const bytes = Uint8Array.from(atob(stepBase64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: "application/octet-stream" });

    const formData = new FormData();
    formData.append("file", blob, filename);

    const url = `${BASE}/blobelements/d/${ctx.documentId}/w/${ctx.workspaceId}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Authorization": auth },
      body: formData,
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Onshape upload failed (${resp.status}): ${text}`);
    }

    return await resp.json();
  }

  return { getKeys, saveKeys, clearKeys, hasKeys, getContext, uploadSTEP };
})();
