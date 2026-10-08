// Docwise Frontend Controller
// Handles file upload, semantic query submission, citations rendering, and session state.

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const statusIndicator = document.getElementById("system-status-indicator");
  const statusText = document.getElementById("status-text");
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
    hasUploadedDocument: false,
    activeDocument: null,
    isProcessingQuery: false
  };

  // Poll system status
  async function checkSystemStatus() {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        statusIndicator.classList.remove("offline");
        statusText.textContent = data.has_api_key ? "Docwise Engine Active" : "Server Key Missing";
        if (data.indexed_chunks_count > 0) {
          engineStatusText.textContent = `Indexed Chunks: ${data.indexed_chunks_count} | Engine: ${data.use_dense_embeddings ? "Dense Embeddings" : "Lexical Index"} | Model: ${data.model}`;
        } else {
          engineStatusText.textContent = `Model: ${data.model} | Embeddings: Ready`;
        }
      }
    } catch (e) {
      statusIndicator.classList.add("offline");
      statusText.textContent = "Server Offline";
    }
  }

  checkSystemStatus();

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

    docSummaryText.innerHTML = formatMarkdown(doc.summary);

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
          question: query
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
        <div class="message-text">${formatMarkdown(text)}</div>
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
      textEl.innerHTML = formatMarkdown(text);
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
      let scoreLabel = "";
      if (typeof c.score === "number") {
        if (c.score <= 1.0 && c.score > 0) {
          scoreLabel = `Relevance: ${Math.round(c.score * 100)}%`;
        } else {
          scoreLabel = `Relevance: ${c.score}`;
        }
      } else {
        scoreLabel = `Relevance: ${c.score || "Context"}`;
      }

      citationsHtml += `
        <div class="citation-item">
          <div class="citation-meta">
            <span class="page-badge">Page ${c.page_num}</span>
            <span class="score-badge">${scoreLabel}</span>
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

  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);
    // Bold text: **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Markdown headers: ### Header, ## Header
    formatted = formatted.replace(/^###\s+(.*)$/gm, "<h4 style='margin: 8px 0 4px; color: #f8fafc;'>$1</h4>");
    formatted = formatted.replace(/^##\s+(.*)$/gm, "<h3 style='margin: 10px 0 6px; color: #f8fafc;'>$1</h3>");
    // Bullet list items
    formatted = formatted.replace(/^[\*\-]\s+(.*)$/gm, "<div style='margin-left: 12px; margin-bottom: 3px;'>• $1</div>");
    return formatted;
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
