const state = {
  sessionId: null,
  session: null,
  generateProgressTimer: null,
  generateProgressValue: 0,
  pipelineProgressTimer: null,
  pipelineProgressValue: 0,
};

const API_BASE = window.location.port === "8080" ? "http://localhost:8010" : "";

function $(id) {
  return document.getElementById(id);
}

function log(message, data = null) {
  const node = $("log");
  const text = data ? `${message}\n${JSON.stringify(data, null, 2)}\n` : `${message}\n`;
  node.textContent += text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function resolveApiPath(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("/")) return `${API_BASE}${path}`;
  if (path.startsWith("/app/data/")) return `${API_BASE}/data/${path.replace("/app/data/", "")}`;
  return path;
}

function candidatePreviewUrl(originalUrl) {
  if (!originalUrl) return "";
  if (originalUrl.startsWith("http://") || originalUrl.startsWith("https://")) {
    return `${API_BASE}/proxy/image?url=${encodeURIComponent(originalUrl)}`;
  }
  return resolveApiPath(originalUrl);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return payload;
}

function renderSession(session) {
  state.session = session;
  $("sessionId").textContent = session.session_id;
  $("sessionStatus").textContent = session.status;
}

function showSection(id, show) {
  const el = $(id);
  if (!el) return;
  if (show) el.classList.remove("hidden");
  else el.classList.add("hidden");
}

function setGenerateUiDisabled(disabled) {
  ["createSession", "modeLibrary", "modeGenerate", "runGenerate"].forEach((id) => {
    const node = $(id);
    if (node) node.disabled = disabled;
  });
}

function updateGenerateProgress(value, text) {
  const progress = Math.max(0, Math.min(100, value));
  state.generateProgressValue = progress;
  $("generateProgressBar").style.width = `${progress}%`;
  if (text) $("generateProgressText").textContent = text;
}

function resetGenerateProgress() {
  if (state.generateProgressTimer) {
    clearInterval(state.generateProgressTimer);
    state.generateProgressTimer = null;
  }
  state.generateProgressValue = 0;
  const bar = $("generateProgressBar");
  if (bar) {
    bar.classList.remove("error");
    bar.style.width = "0%";
  }
  if ($("generateProgressText")) {
    $("generateProgressText").textContent = "-";
  }
  showSection("generateProgress", false);
  setGenerateUiDisabled(false);
}

function startGenerateProgress() {
  resetGenerateProgress();
  showSection("generateProgress", true);
  setGenerateUiDisabled(true);
  const startedAt = Date.now();
  updateGenerateProgress(3, "Sending request to generation service...");
  state.generateProgressTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    let next = state.generateProgressValue;
    if (next < 25) next += 6;
    else if (next < 45) next += 3;
    else if (next < 70) next += 1.6;
    else if (next < 92) next += 0.6;
    updateGenerateProgress(next, `Generating... ${elapsed}s`);
  }, 900);
}

function finishGenerateProgressSuccess() {
  if (state.generateProgressTimer) {
    clearInterval(state.generateProgressTimer);
    state.generateProgressTimer = null;
  }
  $("generateProgressBar").classList.remove("error");
  updateGenerateProgress(100, "Completed");
  setGenerateUiDisabled(false);
}

function finishGenerateProgressError(message) {
  if (state.generateProgressTimer) {
    clearInterval(state.generateProgressTimer);
    state.generateProgressTimer = null;
  }
  $("generateProgressBar").classList.add("error");
  updateGenerateProgress(state.generateProgressValue || 100, `Failed: ${message}`);
  setGenerateUiDisabled(false);
}

function updatePipelineProgress(value, text) {
  const progress = Math.max(0, Math.min(100, value));
  state.pipelineProgressValue = progress;
  $("pipelineProgressBar").style.width = `${progress}%`;
  if (text) $("pipelineProgressText").textContent = text;
}

function resetPipelineProgress() {
  if (state.pipelineProgressTimer) {
    clearInterval(state.pipelineProgressTimer);
    state.pipelineProgressTimer = null;
  }
  state.pipelineProgressValue = 0;
  const bar = $("pipelineProgressBar");
  if (bar) {
    bar.classList.remove("error");
    bar.style.width = "0%";
  }
  if ($("pipelineProgressText")) {
    $("pipelineProgressText").textContent = "-";
  }
  showSection("pipelineProgress", false);
}

function startPipelineProgress() {
  resetPipelineProgress();
  showSection("pipelineProgress", true);
  const startedAt = Date.now();
  updatePipelineProgress(4, "Starting vectorization...");
  state.pipelineProgressTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    let next = state.pipelineProgressValue;
    if (next < 20) next += 5;
    else if (next < 50) next += 2.2;
    else if (next < 80) next += 1.2;
    else if (next < 95) next += 0.5;
    let stageText = "Vectorizing selected image...";
    if (next >= 40) stageText = "Segmenting layers by color...";
    updatePipelineProgress(next, `${stageText} ${elapsed}s`);
  }, 850);
}

function finishPipelineProgressSuccess() {
  if (state.pipelineProgressTimer) {
    clearInterval(state.pipelineProgressTimer);
    state.pipelineProgressTimer = null;
  }
  $("pipelineProgressBar").classList.remove("error");
  updatePipelineProgress(100, "Completed");
}

function finishPipelineProgressError(message) {
  if (state.pipelineProgressTimer) {
    clearInterval(state.pipelineProgressTimer);
    state.pipelineProgressTimer = null;
  }
  $("pipelineProgressBar").classList.add("error");
  updatePipelineProgress(state.pipelineProgressValue || 100, `Failed: ${message}`);
}

function resetFlowViews() {
  $("libraryContainer").innerHTML = "";
  $("generatedContainer").innerHTML = "";
  $("variantContainer").innerHTML = "";
  resetGenerateProgress();
  resetPipelineProgress();
}

function renderLibraryItems(items) {
  const root = $("libraryContainer");
  root.innerHTML = "";
  if (!items.length) {
    root.textContent = "Библиотека пуста.";
    return;
  }
  items.forEach((item, idx) => {
    const box = document.createElement("div");
    box.className = "box";
    const preview = resolveApiPath(item.preview_uri);
    box.innerHTML = `<b>${idx + 1}. ${escapeHtml(item.pack_id)}</b><br/>theme=${escapeHtml(item.theme)}<br/>difficulty=${escapeHtml(item.difficulty)}<br/>colors=${escapeHtml((item.colors || []).join(", "))}`;
    if (preview) {
      const img = document.createElement("img");
      img.src = preview;
      img.alt = `preview_${item.pack_id}`;
      img.style.maxWidth = "220px";
      img.style.maxHeight = "220px";
      img.style.display = "block";
      img.style.margin = "8px 0";
      box.appendChild(img);
    }
    const btn = document.createElement("button");
    btn.textContent = "Выбрать и отправить в работу";
    btn.onclick = async () => {
      try {
        const session = await api(`/sessions/${state.sessionId}/library/select`, {
          method: "POST",
          body: JSON.stringify({ pack_id: item.pack_id }),
        });
        renderSession(session);
        log("Library item selected. Session is ready_for_runtime", session);
      } catch (err) {
        log("Library selection failed", { error: err.message });
      }
    };
    box.appendChild(btn);
    root.appendChild(box);
  });
}

async function autoSelectCandidate(candidateId) {
  showSection("variantsStep", true);
  $("variantContainer").innerHTML = "";
  startPipelineProgress();
  const updated = await api(`/sessions/${state.sessionId}/generate/select`, {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
  finishPipelineProgressSuccess();
  renderSession(updated);
  renderVectorizedResult(updated);
  showSection("variantsStep", true);
  log("Single candidate auto-selected. Vectorize/segmentation completed", updated);
}

async function renderGeneratedCandidates(session) {
  const root = $("generatedContainer");
  root.innerHTML = "";
  const candidates = session.candidates || [];
  if (!candidates.length) {
    root.textContent = "Кандидаты не получены.";
    return;
  }
  candidates.forEach((c, idx) => {
    const box = document.createElement("div");
    box.className = "box";
    box.innerHTML = `<b>Вариант ${idx + 1}</b><br/>id=${escapeHtml(c.candidate_id)}<br/>score=${escapeHtml(c.score)}`;
    const preview = candidatePreviewUrl(c.uri);
    if (preview) {
      const img = document.createElement("img");
      img.src = preview;
      img.alt = `candidate_${c.candidate_id}`;
      img.style.maxWidth = "220px";
      img.style.maxHeight = "220px";
      img.style.display = "block";
      img.style.margin = "8px 0";
      box.appendChild(img);
    }
    const note = document.createElement("div");
    note.className = "muted";
    note.textContent = "Вариант выбирается автоматически.";
    box.appendChild(note);
    root.appendChild(box);
  });

  try {
    await autoSelectCandidate(candidates[0].candidate_id);
  } catch (err) {
    finishPipelineProgressError(err.message);
    log("Auto candidate selection failed", { error: err.message });
  }
}

function renderVectorizedResult(session) {
  const root = $("variantContainer");
  root.innerHTML = "";
  const box = document.createElement("div");
  box.className = "box";
  box.innerHTML = `<b>Векторизация завершена</b><br/>status=${escapeHtml(session.status)}`;

  const preview = resolveApiPath(session.vector_preview_uri || "");
  if (preview) {
    const img = document.createElement("img");
    img.src = preview;
    img.alt = "vectorized_preview";
    img.style.maxWidth = "220px";
    img.style.maxHeight = "220px";
    img.style.display = "block";
    img.style.margin = "8px 0";
    box.appendChild(img);
  } else {
    const note = document.createElement("div");
    note.textContent = "Preview not available";
    box.appendChild(note);
  }
  root.appendChild(box);
}

$("createSession").onclick = async () => {
  try {
    const session = await api("/sessions", { method: "POST" });
    state.sessionId = session.session_id;
    renderSession(session);
    resetFlowViews();
    showSection("libraryStep", false);
    showSection("generateStep", false);
    showSection("variantsStep", false);
    log("Session created", session);
  } catch (err) {
    log("Create session failed", { error: err.message });
  }
};

$("modeLibrary").onclick = async () => {
  try {
    if (!state.sessionId) throw new Error("Сначала создайте сессию");
    const session = await api(`/sessions/${state.sessionId}/mode`, {
      method: "POST",
      body: JSON.stringify({ mode: "library" }),
    });
    renderSession(session);
    showSection("libraryStep", true);
    showSection("generateStep", false);
    showSection("variantsStep", false);
    resetGenerateProgress();
    resetPipelineProgress();
    const items = await api("/library/items");
    renderLibraryItems(items);
    log("Library mode selected", { items: items.length });
  } catch (err) {
    log("Set mode library failed", { error: err.message });
  }
};

$("modeGenerate").onclick = async () => {
  try {
    if (!state.sessionId) throw new Error("Сначала создайте сессию");
    const session = await api(`/sessions/${state.sessionId}/mode`, {
      method: "POST",
      body: JSON.stringify({ mode: "generate" }),
    });
    renderSession(session);
    showSection("libraryStep", false);
    showSection("generateStep", true);
    showSection("variantsStep", false);
    resetGenerateProgress();
    resetPipelineProgress();
    $("generatedContainer").innerHTML = "";
    $("variantContainer").innerHTML = "";
    log("Generate mode selected");
  } catch (err) {
    log("Set mode generate failed", { error: err.message });
  }
};

$("loadLibrary").onclick = async () => {
  try {
    const items = await api("/library/items");
    renderLibraryItems(items);
    log("Library refreshed", { items: items.length });
  } catch (err) {
    log("Load library failed", { error: err.message });
  }
};

$("runGenerate").onclick = async () => {
  try {
    if (!state.sessionId) throw new Error("Сначала создайте сессию");
    const prompt = $("userPrompt").value.trim();
    const minColors = Number($("minColors").value);
    const maxColors = Number($("maxColors").value);
    startGenerateProgress();
    const session = await api(`/sessions/${state.sessionId}/generate/start`, {
      method: "POST",
      body: JSON.stringify({
        prompt,
        min_colors: minColors,
        max_colors: maxColors,
      }),
    });
    finishGenerateProgressSuccess();
    renderSession(session);
    await renderGeneratedCandidates(session);
    log("Generated 1 variant", { candidates: (session.candidates || []).length });
  } catch (err) {
    finishGenerateProgressError(err.message);
    log("Generate step failed", { error: err.message });
  }
};
