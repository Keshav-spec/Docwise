// Docwise Frontend Controller
// Handles file upload, semantic query submission, citations rendering, and session state.

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const statusIndicator = document.getElementById("system-status-indicator");
  const statusText = document.getElementById("status-text");
  const settingsToggleBtn = document.getElementById("settings-toggle-btn");
  const settingsModal = document.getElementById("settings-modal");
  const closeModalBtn = document.getElementById("close-modal-btn");
  const saveSettingsBtn = document.getElementById("save-settings-btn");
  const apiKeyInput = document.getElementById("api-key-input");
  const modelSelect = document.getElementById("model-select");
  const topKInput = document.getElementById("top-k-input");
  const clearSessionBtn = document.getElementById("clear-session-btn");

  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("pdf-file-input");
  const browseBtn = document.getElementById("browse-btn");
  const uploadProgress = document.getElementById("upload-progress-container");
  const uploadStatusText = document.getElementById("upload-status-text");

  const docMetaSection = document.getElementById("doc-meta-section");
  const metaFilename = document.getElementById("meta-filename");
  const metaPages = document.getElementById("meta-pages");
  const metaChunks = document.getElementById("meta-chunks");
  const metaChars = document.getElementById("meta-chars");
  const metaEngineBadge = document.getElementById("meta-engine-badge");
  const docSummaryText = document.getElementById("doc-summary-text");
  const starterQuestionsList = document.getElementById("starter-questions-list");

  const chatMessagesContainer = document.getElementById("chat-messages-container");
  const welcomeMessageCard = document.getElementById("welcome-message-card");
  const queryForm = document.getElementById("query-form");
  const queryInput = document.getElementById("query-input");
  const submitQueryBtn = document.getElementById("submit-query-btn");
  const exportBtn = document.getElementById("export-btn");
  const engineStatusText = document.getElementById("engine-status-text");

  // State Management
  let state = {
    apiKey: localStorage.getItem("docwise_api_key") || "",
    model: localStorage.getItem("docwise_model") || "gemini-1.5-flash",
    topK: parseInt(localStorage.getItem("docwise_top_k") || "4", 10),
    hasUploadedDocument: false,
    activeDocument: null,
    isProcessingQuery: false
  };

  // Initialize input fields from state
  apiKeyInput.value = state.apiKey;
  modelSelect.value = state.model;
  topKInput.value = state.topK;

  // Poll system status
  async function checkSystemStatus() {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        statusIndicator.classList.remove("offline");
        statusText.textContent = data.has_api_key || state.apiKey ? "Ready" : "API Key Required";
        if (data.indexed_chunks_count > 0) {
          engineStatusText.textContent = `Indexed Chunks: ${data.indexed_chunks_count} | Mode: ${data.use_dense_embeddings ? "Dense Embeddings" : "Lexical Index"}`;
        }
      }
    } catch (e) {
      statusIndicator.classList.add("offline");
      statusText.textContent = "Server Offline";
    }
  }

  checkSystemStatus();

  // Settings Modal Handlers
  settingsToggleBtn.addEventListener("click", () => {
    settingsModal.classList.remove("hidden");
  });

  closeModalBtn.addEventListener("click", () => {
    settingsModal.classList.add("hidden");
  });

  settingsModal.addEventListener("click", (e) => {
    if (e.target === settingsModal) {
      settingsModal.classList.add("hidden");
    }
  });

  saveSettingsBtn.addEventListener("click", async () => {
    state.apiKey = apiKeyInput.value.trim();
    state.model = modelSelect.value;
    state.topK = parseInt(topKInput.value, 10) || 4;

    localStorage.setItem("docwise_api_key", state.apiKey);
    localStorage.setItem("docwise_model", state.model);
    localStorage.setItem("docwise_top_k", state.topK.toString());

    if (state.apiKey) {
      try {
        await fetch("/api/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: state.apiKey, model_name: state.model })
        });
      } catch (err) {
        console.error("Failed to sync config with server", err);
      }
    }

    settingsModal.classList.add("hidden");
    checkSystemStatus();
  });

  // File Upload Handlers
  browseBtn.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-active");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-active");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-active");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please upload a PDF file.");
      return;
    }

    uploadProgress.classList.remove("hidden");
    uploadStatusText.textContent = `Extracting pages and building embeddings for ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);
    if (state.apiKey) {
      formData.append("api_key", state.apiKey);
    }

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const data = await res.json();
      renderDocumentDetails(data.document, data.dense_embeddings_active);
      state.hasUploadedDocument = true;
      state.activeDocument = data.document;

      if (welcomeMessageCard) {
        welcomeMessageCard.classList.add("hidden");
      }

      uploadStatusText.textContent = "Processing complete";
      setTimeout(() => uploadProgress.classList.add("hidden"), 1000);
      checkSystemStatus();
    } catch (err) {
      alert(`Upload Error: ${err.message}`);
      uploadProgress.classList.add("hidden");
    }
  }

  function renderDocumentDetails(doc, isDense) {
    metaFilename.textContent = doc.filename;
    metaPages.textContent = doc.total_pages;
    metaChunks.textContent = doc.chunk_count;
    metaChars.textContent = doc.total_characters.toLocaleString();

    metaEngineBadge.textContent = isDense ? "Dense Embeddings" : "Lexical Index";
    metaEngineBadge.style.color = isDense ? "var(--accent-cyan)" : "var(--accent-amber)";

    docSummaryText.textContent = doc.summary;

    // Render starter questions
    starterQuestionsList.innerHTML = "";
    if (doc.starter_questions && doc.starter_questions.length > 0) {
      doc.starter_questions.forEach(q => {
        const chip = document.createElement("button");
        chip.className = "question-chip";
        chip.textContent = q;
        chip.addEventListener("click", () => {
          queryInput.value = q;
          queryForm.dispatchEvent(new Event("submit"));
        });
        starterQuestionsList.appendChild(chip);
      });
    }

    docMetaSection.classList.remove("hidden");
  }

  // Conversation & Query Handlers
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      queryForm.dispatchEvent(new Event("submit"));
    }
  });

  queryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();

    if (!query) return;

    if (!state.apiKey) {
      alert("Please configure your Google Gemini API key in Settings before submitting queries.");
      settingsModal.classList.remove("hidden");
      return;
    }

    if (state.isProcessingQuery) return;

    // Append user message to view
    appendUserMessage(query);
    queryInput.value = "";
    state.isProcessingQuery = true;
    submitQueryBtn.disabled = true;

    // Show temporary thinking message
    const tempResponseId = appendAssistantMessage("Retrieving document chunks and analyzing query with Gemini...", []);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: query,
          api_key: state.apiKey,
          model_name: state.model,
          top_k: state.topK
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Query failed");
      }

      const data = await res.json();
      updateAssistantMessage(tempResponseId, data.answer, data.citations);
    } catch (err) {
      updateAssistantMessage(tempResponseId, `Error: ${err.message}`, []);
    } finally {
      state.isProcessingQuery = false;
      submitQueryBtn.disabled = false;
    }
  });

  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `
      <div class="message-bubble">
        <div class="message-sender">You</div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;
    chatMessagesContainer.appendChild(row);
    scrollToBottom();
  }

  let messageCounter = 0;
  function appendAssistantMessage(text, citations) {
    messageCounter++;
    const messageId = `msg-${messageCounter}`;
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.id = messageId;

    row.innerHTML = `
      <div class="message-bubble">
        <div class="message-sender">Docwise</div>
        <div class="message-text">${escapeHtml(text)}</div>
        <div class="citations-container"></div>
      </div>
    `;

    chatMessagesContainer.appendChild(row);
    if (citations && citations.length > 0) {
      renderCitations(row.querySelector(".citations-container"), citations);
    }
    scrollToBottom();
    return messageId;
  }

  function updateAssistantMessage(messageId, text, citations) {
    const row = document.getElementById(messageId);
    if (!row) return;

    const textEl = row.querySelector(".message-text");
    if (textEl) {
      textEl.textContent = text;
    }

    const citationsContainer = row.querySelector(".citations-container");
    if (citationsContainer && citations && citations.length > 0) {
      renderCitations(citationsContainer, citations);
    }
    scrollToBottom();
  }

  function renderCitations(container, citations) {
    let citationsHtml = `
      <div class="citations-wrapper">
        <div class="citations-header">Source Citations (${citations.length})</div>
        <div class="citations-list">
    `;

    citations.forEach(c => {
      citationsHtml += `
        <div class="citation-item">
          <div class="citation-meta">
            <span class="page-badge">Page ${c.page_num}</span>
            <span class="score-badge">Relevance: ${c.score}</span>
          </div>
          <div class="citation-snippet">"${escapeHtml(c.snippet)}"</div>
        </div>
      `;
    });

    citationsHtml += `</div></div>`;
    container.innerHTML = citationsHtml;
  }

  function scrollToBottom() {
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Clear Session Handler
  clearSessionBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to reset the current document index and chat history?")) {
      return;
    }

    try {
      await fetch("/api/clear", { method: "POST" });
      chatMessagesContainer.innerHTML = "";
      if (welcomeMessageCard) {
        chatMessagesContainer.appendChild(welcomeMessageCard);
        welcomeMessageCard.classList.remove("hidden");
      }
      docMetaSection.classList.add("hidden");
      state.hasUploadedDocument = false;
      state.activeDocument = null;
      checkSystemStatus();
    } catch (err) {
      alert("Failed to reset session: " + err.message);
    }
  });

  // Export Transcript Handler
  exportBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/export?format=markdown");
      const data = await res.json();
      const blob = new Blob([data.content], { type: "text/markdown;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `docwise-export-${new Date().toISOString().slice(0, 10)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to export transcript: " + err.message);
    }
  });
});
