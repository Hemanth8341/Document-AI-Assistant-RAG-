const API_BASE_URL = 'http://127.0.0.1:8000';

const state = {
  selectedFiles: [],
  sources: [],
  history: [],
  currentStep: null,
};

const elements = {
  themeToggleBtn: document.getElementById('themeToggleBtn'),
  dropZone: document.getElementById('dropZone'),
  fileInput: document.getElementById('fileInput'),
  browseBtn: document.getElementById('browseBtn'),
  uploadBtn: document.getElementById('uploadBtn'),
  clearIndexBtn: document.getElementById('clearIndexBtn'),
  uploadedFiles: document.getElementById('uploadedFiles'),
  fileCountBadge: document.getElementById('fileCountBadge'),
  
  // Workflow Stepper & Logs
  stepRetrieve: document.getElementById('stepRetrieve'),
  stepGrade: document.getElementById('stepGrade'),
  stepRewrite: document.getElementById('stepRewrite'),
  stepGenerate: document.getElementById('stepGenerate'),
  agentLog: document.getElementById('agentLog'),
  copyLogsBtn: document.getElementById('copyLogsBtn'),
  chatHistory: document.getElementById('chatHistory'),
  historyCountBadge: document.getElementById('historyCountBadge'),
  
  // Question & Answers
  questionInput: document.getElementById('questionInput'),
  askBtn: document.getElementById('askBtn'),
  clearBtn: document.getElementById('clearBtn'),
  loadingState: document.getElementById('loadingState'),
  loadingText: document.getElementById('loadingText'),
  answerOutput: document.getElementById('answerOutput'),
  sourceOutput: document.getElementById('sourceOutput'),
  confidenceOutput: document.getElementById('confidenceOutput'),
  confidenceBar: document.getElementById('confidenceBar'),
  copyAnswerBtn: document.getElementById('copyAnswerBtn'),
  
  // Header System Status
  serverStatus: document.getElementById('serverStatus'),
  serverStatusText: document.getElementById('serverStatusText'),
  statPdfCount: document.getElementById('statPdfCount'),
  statIndexStatus: document.getElementById('statIndexStatus'),
  statOllamaStatus: document.getElementById('statOllamaStatus'),
  
  // Modal & Toast
  snippetModal: new bootstrap.Modal(document.getElementById('snippetModal')),
  modalDocBadge: document.getElementById('modalDocBadge'),
  modalPageBadge: document.getElementById('modalPageBadge'),
  snippetModalBody: document.getElementById('snippetModalBody'),
  toast: new bootstrap.Toast(document.getElementById('liveToast')),
  toastMessage: document.getElementById('toastMessage'),
};

// Simple Lightweight Markdown Parser
function parseMarkdown(text) {
  if (!text) return '';
  let html = text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');

  // Code blocks
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
  // Bullet lists
  html = html.replace(/^\s*[\-\*]\s+(.*)$/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
  // Clean double UL wrapper tags
  html = html.replace(/<\/ul>\s*<ul>/g, '');
  // Line breaks
  html = html.replace(/\n\n/g, '<p></p>');
  html = html.replace(/\n/g, '<br>');

  return html;
}

function showToast(message) {
  elements.toastMessage.textContent = message;
  elements.toast.show();
}

function initTheme() {
  const savedTheme = localStorage.getItem('docutrust-theme') || 'dark';
  document.body.classList.toggle('light-theme', savedTheme === 'light');
  elements.themeToggleBtn.innerHTML = savedTheme === 'light' ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
}

function toggleTheme() {
  const isLight = document.body.classList.toggle('light-theme');
  localStorage.setItem('docutrust-theme', isLight ? 'light' : 'dark');
  elements.themeToggleBtn.innerHTML = isLight ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
}

function formatFileSize(bytes) {
  if (!bytes) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// System Health & Stats Polling
async function checkSystemHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/stats`);
    if (!res.ok) throw new Error();
    const data = await res.json();

    elements.serverStatus.className = 'status-pill status-online';
    elements.serverStatusText.textContent = 'Online';

    elements.statPdfCount.textContent = data.file_count || 0;
    elements.statIndexStatus.textContent = data.has_index ? 'FAISS Ready' : 'No Index';
    elements.statOllamaStatus.textContent = data.ollama_online ? 'Ollama Active' : 'Ollama Offline';
  } catch (err) {
    elements.serverStatus.className = 'status-pill status-offline';
    elements.serverStatusText.textContent = 'Backend Offline';
    elements.statOllamaStatus.textContent = 'Offline';
  }
}

// Stepper workflow logic
function setWorkflowStep(stepName) {
  state.currentStep = stepName;
  const steps = ['retrieve', 'grade', 'rewrite', 'generate'];
  const currentIndex = steps.indexOf(stepName);

  steps.forEach((s, idx) => {
    const el = document.getElementById(`step${s.charAt(0).toUpperCase() + s.slice(1)}`);
    if (!el) return;
    el.classList.remove('active', 'completed');
    if (idx < currentIndex) el.classList.add('completed');
    if (idx === currentIndex) el.classList.add('active');
  });
}

function clearWorkflowStepper() {
  ['stepRetrieve', 'stepGrade', 'stepRewrite', 'stepGenerate'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active', 'completed');
  });
}

// Agent Log Renderer
function addLog(message, type = 'info') {
  const entry = document.createElement('div');
  const lower = message.toLowerCase();

  let logType = type;
  if (lower.includes('retriev')) {
    logType = 'step';
    setWorkflowStep('retrieve');
  } else if (lower.includes('grad') || lower.includes('relevance')) {
    logType = 'info';
    setWorkflowStep('grade');
  } else if (lower.includes('rewrote') || lower.includes('rewrite')) {
    logType = 'warning';
    setWorkflowStep('rewrite');
  } else if (lower.includes('generat') || lower.includes('grounded')) {
    logType = 'success';
    setWorkflowStep('generate');
  } else if (lower.includes('error') || lower.includes('failed')) {
    logType = 'error';
  } else if (lower.includes('saved') || lower.includes('ready')) {
    logType = 'success';
  }

  entry.className = `log-entry log-${logType}`;
  entry.innerHTML = `
    <span class="log-time">[${formatTime()}]</span>
    <span class="log-text">${escapeHtml(message)}</span>
  `;
  elements.agentLog.appendChild(entry);
  elements.agentLog.scrollTop = elements.agentLog.scrollHeight;
}

function replaceLogs(messages) {
  elements.agentLog.innerHTML = '';
  if (!messages || !messages.length) {
    elements.agentLog.innerHTML = '<div class="text-muted p-2 fs-xs">System idle. Ready for documents or questions.</div>';
    return;
  }
  messages.forEach((msg) => addLog(typeof msg === 'string' ? msg : msg.message));
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// Render Selected Files
function renderUploadedFiles() {
  elements.fileCountBadge.textContent = state.selectedFiles.length;

  if (!state.selectedFiles.length) {
    elements.uploadedFiles.innerHTML = '<li class="text-muted p-2 text-center fs-xs">No PDFs selected.</li>';
    return;
  }

  elements.uploadedFiles.innerHTML = state.selectedFiles
    .map((file, idx) => `
      <li class="file-item">
        <div class="d-flex align-items-center gap-2 text-truncate">
          <i class="fa-solid fa-file-pdf text-danger fs-5"></i>
          <div class="text-truncate">
            <div class="fw-bold text-truncate" style="max-width: 140px;" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
            <div class="text-muted fs-xs">${formatFileSize(file.size)}</div>
          </div>
        </div>
        <button class="btn-delete-file" onclick="removeSelectedFile(${idx})" title="Remove">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </li>
    `)
    .join('');
}

function removeSelectedFile(index) {
  state.selectedFiles.splice(index, 1);
  renderUploadedFiles();
}

function handleFiles(fileList) {
  const validFiles = Array.from(fileList).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
  if (!validFiles.length) {
    showToast('Please select valid PDF files.');
    return;
  }
  state.selectedFiles = [...state.selectedFiles, ...validFiles];
  renderUploadedFiles();
  addLog(`${validFiles.length} PDF(s) added to file selection queue.`, 'info');
}

// Upload & Index PDFs
async function uploadFiles() {
  if (!state.selectedFiles.length) {
    showToast('Select one or more PDFs to upload.');
    return;
  }

  const formData = new FormData();
  state.selectedFiles.forEach((file) => formData.append('files', file));

  setLoading(true, 'Indexing PDFs & Building Vectors...');
  clearWorkflowStepper();

  try {
    const res = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    replaceLogs(data.logs || []);
    showToast('PDFs uploaded & FAISS index built!');
    checkSystemHealth();
  } catch (err) {
    addLog(`Upload failure: ${err.message}`, 'error');
    showToast(`Error: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

// Clear Stores
async function clearStoreAndIndex() {
  if (!confirm('Are you sure you want to clear all uploaded PDFs and reset the vector store?')) return;
  setLoading(true, 'Clearing Document Vector Store...');
  try {
    const res = await fetch(`${API_BASE_URL}/clear`, { method: 'POST' });
    const data = await res.json();
    state.selectedFiles = [];
    renderUploadedFiles();
    replaceLogs(data.logs || []);
    showToast('Vector store & files cleared.');
    checkSystemHealth();
  } catch (err) {
    showToast('Failed to clear index.');
  } finally {
    setLoading(false);
  }
}

// Ask Question Workflow
async function askQuestion() {
  const question = elements.questionInput.value.trim();
  if (!question) {
    showToast('Please enter a question.');
    return;
  }

  setLoading(true, 'Running LangGraph Self-Correcting RAG...');
  clearWorkflowStepper();

  elements.answerOutput.innerHTML = '<span class="text-muted"><i class="fa-solid fa-spinner fa-spin me-2"></i>Searching documents and formulating answer...</span>';
  elements.sourceOutput.innerHTML = '<span class="text-muted">Retrieving page citations...</span>';
  elements.confidenceOutput.textContent = '--';
  elements.confidenceBar.style.width = '0%';
  elements.copyAnswerBtn.classList.add('d-none');

  try {
    const res = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to generate answer.');

    // Render Answer Markdown
    elements.answerOutput.innerHTML = parseMarkdown(data.answer);
    elements.answerOutput.classList.remove('is-placeholder');
    elements.copyAnswerBtn.classList.remove('d-none');

    // Confidence Calculation
    const confPercent = Math.round(data.confidence * 100);
    elements.confidenceOutput.textContent = `${confPercent}%`;
    elements.confidenceBar.style.width = `${confPercent}%`;

    if (confPercent >= 70) {
      elements.confidenceOutput.style.color = 'var(--success)';
      elements.confidenceBar.style.background = 'var(--success)';
    } else if (confPercent < 40) {
      elements.confidenceOutput.style.color = 'var(--danger)';
      elements.confidenceBar.style.background = 'var(--danger)';
    } else {
      elements.confidenceOutput.style.color = 'var(--warning)';
      elements.confidenceBar.style.background = 'var(--warning)';
    }

    // Sources Render
    state.sources = data.sources || [];
    if (!state.sources.length) {
      elements.sourceOutput.innerHTML = '<span class="text-muted fs-xs">No direct sources found.</span>';
    } else {
      elements.sourceOutput.innerHTML = state.sources
        .map(
          (src, idx) => `
        <span class="source-badge" onclick="openSnippetModal(${idx})">
          <i class="fa-solid fa-book-open"></i> Page ${src.page} • ${escapeHtml(src.file_name || 'Doc')}
        </span>
      `,
        )
        .join('');
    }

    // Logs & History
    replaceLogs(data.logs || []);
    addChatHistory(question, data.answer);
  } catch (err) {
    elements.answerOutput.innerHTML = `<span class="text-danger"><i class="fa-solid fa-circle-exclamation me-1"></i> ${escapeHtml(err.message)}</span>`;
    addLog(`Error: ${err.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

function openSnippetModal(index) {
  const src = state.sources[index];
  if (!src) return;
  elements.modalDocBadge.textContent = src.file_name || 'Document';
  elements.modalPageBadge.textContent = `Page ${src.page}`;
  elements.snippetModalBody.textContent = src.snippet || 'No text snippet preview available.';
  elements.snippetModal.show();
}

function addChatHistory(q, a) {
  state.history.unshift({ q, a });
  elements.historyCountBadge.textContent = state.history.length;

  elements.chatHistory.innerHTML = state.history
    .map(
      (item, idx) => `
    <div class="chat-item" onclick="reaskHistory(${idx})">
      <div class="fw-bold text-truncate"><i class="fa-regular fa-comment me-1 text-accent"></i> ${escapeHtml(item.q)}</div>
      <div class="text-muted fs-xs text-truncate">${escapeHtml(item.a)}</div>
    </div>
  `,
    )
    .join('');
}

function reaskHistory(index) {
  const item = state.history[index];
  if (item) {
    elements.questionInput.value = item.q;
    askQuestion();
  }
}

function setLoading(isLoading, text = 'Processing...') {
  elements.loadingState.classList.toggle('d-none', !isLoading);
  elements.loadingText.textContent = text;
  elements.askBtn.disabled = isLoading;
  elements.uploadBtn.disabled = isLoading;
}

function clearQuestion() {
  elements.questionInput.value = '';
  elements.answerOutput.innerHTML = 'Your grounded answer will appear here after asking a question.';
  elements.answerOutput.classList.add('is-placeholder');
  elements.sourceOutput.innerHTML = 'No sources cited yet.';
  elements.confidenceOutput.textContent = '--';
  elements.confidenceBar.style.width = '0%';
  elements.copyAnswerBtn.classList.add('d-none');
}

function copyAnswerToClipboard() {
  const text = elements.answerOutput.innerText;
  if (!text) return;
  navigator.clipboard.writeText(text);
  showToast('Answer copied to clipboard!');
}

function copyLogsToClipboard() {
  const text = elements.agentLog.innerText;
  if (!text) return;
  navigator.clipboard.writeText(text);
  showToast('Logs copied to clipboard!');
}

function bindEvents() {
  elements.themeToggleBtn.addEventListener('click', toggleTheme);
  elements.browseBtn.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
  elements.uploadBtn.addEventListener('click', uploadFiles);
  elements.clearIndexBtn.addEventListener('click', clearStoreAndIndex);
  elements.askBtn.addEventListener('click', askQuestion);
  elements.clearBtn.addEventListener('click', clearQuestion);
  elements.copyAnswerBtn.addEventListener('click', copyAnswerToClipboard);
  elements.copyLogsBtn.addEventListener('click', copyLogsToClipboard);

  // Preset Chips
  document.querySelectorAll('.preset-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      elements.questionInput.value = chip.dataset.prompt;
      askQuestion();
    });
  });

  // Ctrl+Enter Keyboard Shortcut
  elements.questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      askQuestion();
    }
  });

  // Drag and Drop
  ['dragenter', 'dragover'].forEach((evt) => {
    elements.dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      elements.dropZone.classList.add('dragover');
    });
  });
  ['dragleave', 'drop'].forEach((evt) => {
    elements.dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      elements.dropZone.classList.remove('dragover');
    });
  });
  elements.dropZone.addEventListener('drop', (e) => {
    handleFiles(e.dataTransfer.files);
  });
}

// Initial Boostrap
initTheme();
bindEvents();
renderUploadedFiles();
replaceLogs([]);
checkSystemHealth();
setInterval(checkSystemHealth, 15000);

