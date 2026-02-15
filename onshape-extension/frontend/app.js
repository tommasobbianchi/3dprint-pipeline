/**
 * Main application logic — generate flow, UI state management.
 */
(function() {
  // DOM refs
  const promptEl = document.getElementById("prompt");
  const materialEl = document.getElementById("material");
  const generateBtn = document.getElementById("generate-btn");
  const statusEl = document.getElementById("status");
  const statusText = document.getElementById("status-text");
  const progressFill = document.getElementById("progress-fill");
  const resultEl = document.getElementById("result");
  const metricsEl = document.getElementById("metrics");
  const errorEl = document.getElementById("error");
  const errorText = document.getElementById("error-text");
  const downloadStepBtn = document.getElementById("download-step-btn");
  const downloadStlBtn = document.getElementById("download-stl-btn");
  const uploadBtn = document.getElementById("upload-onshape-btn");
  const uploadStatus = document.getElementById("upload-status");

  let lastResult = null;

  // Determine backend URL (same origin when served by FastAPI)
  const API_BASE = "";

  // --- Init ---
  async function init() {
    await loadMaterials();

    // Show upload button if running inside Onshape iframe
    if (OnshapeAPI.getContext()) {
      uploadBtn.style.display = "inline-block";
    }
  }

  async function loadMaterials() {
    try {
      const resp = await fetch(API_BASE + "/api/materials");
      const data = await resp.json();
      materialEl.innerHTML = "";
      for (const mat of data.materials) {
        const opt = document.createElement("option");
        opt.value = mat.id;
        opt.textContent = mat.id;
        materialEl.appendChild(opt);
      }
    } catch (e) {
      console.error("Failed to load materials:", e);
    }
  }

  // --- Generate ---
  generateBtn.addEventListener("click", async () => {
    const prompt = promptEl.value.trim();
    if (!prompt) { promptEl.focus(); return; }

    // Reset UI
    resultEl.style.display = "none";
    errorEl.style.display = "none";
    statusEl.style.display = "block";
    statusText.textContent = "Calling Claude API...";
    progressFill.className = "indeterminate";
    progressFill.style.width = "30%";
    generateBtn.disabled = true;

    try {
      const resp = await fetch(API_BASE + "/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt,
          material: materialEl.value,
        }),
      });

      const data = await resp.json();
      lastResult = data;

      if (data.success) {
        showResult(data);
      } else {
        showError(data.error || "Generation failed");
      }
    } catch (e) {
      showError("Network error: " + e.message);
    } finally {
      statusEl.style.display = "none";
      progressFill.className = "";
      progressFill.style.width = "0%";
      generateBtn.disabled = false;
    }
  });

  function showResult(data) {
    resultEl.style.display = "block";
    const m = data.metrics;
    let html = "";
    if (m && m.size) {
      html += `<b>Size:</b> <span>${m.size[0].toFixed(1)} x ${m.size[1].toFixed(1)} x ${m.size[2].toFixed(1)} mm</span><br>`;
    }
    if (m && m.volume) {
      html += `<b>Volume:</b> <span>${m.volume.toFixed(0)} mm&sup3;</span><br>`;
    }
    if (m && m.solid_count) {
      html += `<b>Solids:</b> <span>${m.solid_count}</span>`;
    }
    metricsEl.innerHTML = html;

    downloadStepBtn.style.display = data.step_base64 ? "inline-block" : "none";
    downloadStlBtn.style.display = data.stl_base64 ? "inline-block" : "none";
  }

  function showError(msg) {
    errorEl.style.display = "block";
    errorText.textContent = msg;
  }

  // --- Downloads ---
  function downloadBase64(base64, filename, mime) {
    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  downloadStepBtn.addEventListener("click", () => {
    if (lastResult && lastResult.step_base64) {
      downloadBase64(lastResult.step_base64, lastResult.filename || "output.step", "application/step");
    }
  });

  downloadStlBtn.addEventListener("click", () => {
    if (lastResult && lastResult.stl_base64) {
      const stlName = (lastResult.filename || "output.step").replace(".step", ".stl");
      downloadBase64(lastResult.stl_base64, stlName, "application/sla");
    }
  });

  // --- Onshape Upload ---
  uploadBtn.addEventListener("click", async () => {
    if (!lastResult || !lastResult.step_base64) return;

    uploadBtn.disabled = true;
    uploadStatus.textContent = "Uploading to Onshape...";

    try {
      const result = await OnshapeAPI.uploadSTEP(
        lastResult.step_base64,
        lastResult.filename || "output.step"
      );
      uploadStatus.textContent = "Import started! A new Part Studio tab will appear shortly.";
    } catch (e) {
      uploadStatus.textContent = "Upload failed: " + e.message;
    } finally {
      uploadBtn.disabled = false;
    }
  });

  // --- Keyboard shortcut ---
  promptEl.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      generateBtn.click();
    }
  });

  init();
})();
