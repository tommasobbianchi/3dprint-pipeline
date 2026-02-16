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
  const startNewBtn = document.getElementById("start-new-btn");
  const modeIndicator = document.getElementById("mode-indicator");

  let lastResult = null;
  let lastCode = null;
  let lastPrompt = null;

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
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 min timeout

      const payload = {
        prompt: prompt,
        material: materialEl.value,
      };
      if (lastCode) {
        payload.previous_code = lastCode;
      }

      const resp = await fetch(API_BASE + "/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const data = await resp.json();
      lastResult = data;

      // Store code for iterative refinement (even on failure)
      if (data.code) {
        lastCode = data.code;
        if (!lastPrompt) lastPrompt = prompt;
        enterModifyMode();
      }

      if (data.success) {
        showResult(data);
      } else {
        showError(data.error || "Generation failed");
      }
    } catch (e) {
      if (e.name === "AbortError") {
        showError("Generation timed out (>3 min). Try a simpler prompt.");
      } else {
        showError("Network error: " + e.message + ". Try again.");
      }
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
      html += `<b>Solids:</b> <span>${m.solid_count}</span><br>`;
    }
    if (data.attempts && data.attempts > 1) {
      html += `<b>Auto-fixed:</b> <span>succeeded on attempt ${data.attempts}</span><br>`;
    }
    if (data.visual_check) {
      const vc = data.visual_check;
      const conf = vc.confidence || 0;
      const color = conf >= 7 ? "#38a169" : conf >= 4 ? "#d69e2e" : "#e53e3e";
      const icon = vc.valid ? "\u2713" : "\u2717";
      html += `<b>Shape check:</b> <span class="vc-badge" style="color:${color}">${icon} ${conf}/10</span>`;
      if (vc.category) {
        html += ` <span>${vc.category}</span>`;
      }
      if (vc.retried) {
        html += ` <span class="vc-retry">visual retry applied</span>`;
      }
      html += "<br>";
      if (vc.missing && !vc.valid) {
        html += `<span class="vc-note">Missing: ${vc.missing}</span><br>`;
      }
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
      const fname = lastResult.filename || "output.step";
      const result = await OnshapeAPI.uploadSTEP(
        lastResult.step_base64,
        fname
      );
      const tabName = fname.replace(/\.step$/i, "");
      uploadStatus.textContent = `Imported! Look for the new "${tabName}" tab at the bottom.`;
    } catch (e) {
      uploadStatus.textContent = "Upload failed: " + e.message;
    } finally {
      uploadBtn.disabled = false;
    }
  });

  // --- Mode switching ---
  function enterModifyMode() {
    generateBtn.textContent = "Modify";
    promptEl.placeholder = 'Modify: e.g. "make walls 3mm thick"';
    promptEl.value = "";
    startNewBtn.style.display = "inline-block";
    if (lastPrompt) {
      const truncated = lastPrompt.length > 50 ? lastPrompt.slice(0, 50) + "..." : lastPrompt;
      modeIndicator.textContent = "Modifying: \"" + truncated + "\"";
      modeIndicator.style.display = "block";
    }
  }

  function enterGenerateMode() {
    lastCode = null;
    lastPrompt = null;
    lastResult = null;
    generateBtn.textContent = "Generate";
    promptEl.placeholder = "e.g. 30mm cube with a 10mm center through-hole";
    promptEl.value = "";
    startNewBtn.style.display = "none";
    modeIndicator.style.display = "none";
    resultEl.style.display = "none";
    errorEl.style.display = "none";
    uploadStatus.textContent = "";
  }

  startNewBtn.addEventListener("click", enterGenerateMode);

  // --- Keyboard shortcut ---
  promptEl.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      generateBtn.click();
    }
  });

  init();
})();
