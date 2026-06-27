const API_BASE_URL = 'http://127.0.0.1:8000';

const state = {
  selectedFiles: [],
  uploadedFiles: [],
};

const elements = {
  themeToggle: document.getElementById('themeToggle'),
  dropZone: document.getElementById('dropZone'),
  fileInput: document.getElementById('fileInput'),
  browseBtn: document.getElementById('browseBtn'),
  uploadBtn: document.getElementById('uploadBtn'),
  uploadedFiles: document.getElementById('uploadedFiles'),
  agentLog: document.getElementById('agentLog'),
  chatHistory: document.getElementById('chatHistory'),
  questionInput: document.getElementById('questionInput'),
  askBtn: document.getElementById('askBtn'),
  clearBtn: document.getElementById('clearBtn'),
  loadingState: document.getElementById('loadingState'),
  answerOutput: document.getElementById('answerOutput'),
  sourceOutput: document.getElementById('sourceOutput'),
  confidenceOutput: document.getElementById('confidenceOutput'),
};

const UPLOAD_LOG_STEPS = [
  { message: 'Receiving PDF file(s)...', type: 'step' },
  { message: 'Validating and saving files...', type: 'step' },
  { message: 'Loading PDF pages...', type: 'info' },
  { message: 'Splitting text into chunks...', type: 'info' },
  { message: 'Creating embeddings...', type: 'info' },
  { message: 'Building FAISS index...', type: 'info' },
];

const ASK_LOG_STEPS = [
  { message: 'Loading FAISS vector index...', type: 'step' },
  { message: 'Searching relevant document chunks...', type: 'info' },
  { message: 'Grading context relevance...', type: 'info' },
  { message: 'Generating grounded answer...', type: 'info' },
];

function initTheme() {
  const savedTheme = localStorage.getItem('docutrust-theme') || 'dark';
  document.body.classList.toggle('light-theme', savedTheme === 'light');
  elements.themeToggle.checked = savedTheme === 'dark';
}

function saveTheme(isDark) {
  localStorage.setItem('docutrust-theme', isDark ? 'dark' : 'light');
}

function formatFileSize(bytes) {
  if (!bytes) return '0 KB';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function classifyLogType(message) {
  const lower = message.toLowerCase();
  if (lower.includes('error') || lower.includes('failed')) return 'error';
  if (lower.includes('ready') || lower.includes('success') || lower.includes('saved') || lower.includes('indexed')) {
    return 'success';
  }
  if (lower.includes('rewrite') || lower.includes('weak') || lower.includes('fallback')) return 'warning';
  if (lower.includes('search') || lower.includes('retriev') || lower.includes('loading') || lower.includes('receiving')) {
    return 'step';
  }
  return 'info';
}

function renderUploadedFiles() {
  if (!state.selectedFiles.length) {
    elements.uploadedFiles.innerHTML = '<li class="file-item muted">No files selected.</li>';
    return;
  }

  elements.uploadedFiles.innerHTML = state.selectedFiles
    .map((file) => `
      <li class="file-item">
        <div>
          <div class="fw-semibold">${escapeHtml(file.name)}</div>
          <div class="file-meta">${formatFileSize(file.size)}</div>
        </div>
        <span class="file-badge">PDF</span>
      </li>
    `)
    .join('');
}

function addLog(message, type = null) {
  const entry = document.createElement('div');
  const logType = type || classifyLogType(message);
  entry.className = `log-entry log-${logType}`;
  entry.innerHTML = `
    <span class="log-time">${formatTime()}</span>
    <span class="log-text">${escapeHtml(message)}</span>
  `;
  elements.agentLog.appendChild(entry);
  elements.agentLog.scrollTop = elements.agentLog.scrollHeight;
}

function replaceLogs(messages) {
  elements.agentLog.innerHTML = '';
  if (!messages.length) {
    const empty = document.createElement('div');
    empty.className = 'log-entry muted-empty';
    empty.textContent = 'Awaiting upload or question.';
    elements.agentLog.appendChild(empty);
    return;
  }

  messages.forEach((item) => {
    if (typeof item === 'string') {
      addLog(item);
      return;
    }
    addLog(item.message, item.type);
  });
}

function showProgressLogs(steps) {
  replaceLogs(steps);
}

function addChatHistory(question, answer) {
  const entry = document.createElement('div');
  entry.className = 'chat-item';
  entry.innerHTML = `
    <div class="chat-question fw-semibold">Q: ${escapeHtml(question)}</div>
    <div class="chat-answer">A: ${escapeHtml(answer)}</div>
  `;
  elements.chatHistory.prepend(entry);
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setLoading(isLoading) {
  elements.loadingState.classList.toggle('d-none', !isLoading);
  elements.askBtn.disabled = isLoading;
  elements.uploadBtn.disabled = isLoading;
}

function setConfidenceDisplay(confidence) {
  elements.confidenceOutput.classList.remove('confidence-low', 'confidence-high');

  if (typeof confidence !== 'number') {
    elements.confidenceOutput.textContent = '--';
    return;
  }

  const percent = Math.round(confidence * 100);
  elements.confidenceOutput.textContent = `${percent}%`;

  if (percent >= 70) {
    elements.confidenceOutput.classList.add('confidence-high');
  } else if (percent < 40) {
    elements.confidenceOutput.classList.add('confidence-low');
  }
}

function updateAnswerPanel(answer, sources, confidence) {
  elements.answerOutput.textContent = answer;
  elements.answerOutput.classList.toggle('is-placeholder', !answer);

  if (!sources || !sources.length) {
    elements.sourceOutput.textContent = 'No source citations available.';
    elements.sourceOutput.classList.add('is-placeholder');
  } else {
    elements.sourceOutput.classList.remove('is-placeholder');
    elements.sourceOutput.innerHTML = sources
      .map((source) => {
        const fileName = source.file_name ? `${source.file_name}` : 'document';
        return `<div class="source-badge me-2 mb-2 d-inline-block">Page ${source.page} • ${escapeHtml(fileName)}</div>`;
      })
      .join('');
  }

  setConfidenceDisplay(confidence);
}

function setError(message) {
  elements.answerOutput.textContent = message;
  elements.answerOutput.classList.remove('is-placeholder');
  elements.sourceOutput.textContent = 'No sources available.';
  elements.sourceOutput.classList.add('is-placeholder');
  setConfidenceDisplay(null);
}

function handleFiles(fileList) {
  state.selectedFiles = Array.from(fileList).filter(
    (file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'),
  );
  renderUploadedFiles();

  if (!state.selectedFiles.length) {
    addLog('Only PDF files are supported.', 'warning');
    return;
  }

  addLog(`${state.selectedFiles.length} PDF file(s) selected and ready for upload.`, 'success');
}

async function uploadFiles() {
  if (!state.selectedFiles.length) {
    addLog('Select one or more PDFs before uploading.', 'warning');
    return;
  }

  const formData = new FormData();
  state.selectedFiles.forEach((file) => formData.append('files', file));

  setLoading(true);
  showProgressLogs(UPLOAD_LOG_STEPS);

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || 'Upload failed.');
    }

    state.uploadedFiles = payload.files || [];
    replaceLogs(payload.logs || [payload.message || 'Upload completed.']);

    if (payload.page_count && payload.chunk_count) {
      addLog(`Indexed ${payload.page_count} page(s) into ${payload.chunk_count} chunk(s).`, 'success');
    }
  } catch (error) {
    addLog(`Upload error: ${error.message}`, 'error');
    setError(error.message);
  } finally {
    setLoading(false);
  }
}

async function askQuestion() {
  const question = elements.questionInput.value.trim();
  if (!question) {
    addLog('Enter a question before asking the assistant.', 'warning');
    return;
  }

  setLoading(true);
  showProgressLogs([
    { message: `Loading index for question: "${question}"`, type: 'step' },
    ...ASK_LOG_STEPS.slice(1),
  ]);

  elements.answerOutput.textContent = 'Thinking...';
  elements.answerOutput.classList.remove('is-placeholder');
  elements.sourceOutput.textContent = 'Retrieving citations...';
  elements.sourceOutput.classList.add('is-placeholder');
  setConfidenceDisplay(null);

  try {
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || 'Question request failed.');
    }

    updateAnswerPanel(payload.answer, payload.sources, payload.confidence);
    replaceLogs(payload.logs || ASK_LOG_STEPS.map((step) => step.message));
    addChatHistory(question, payload.answer);
  } catch (error) {
    addLog(`Answer error: ${error.message}`, 'error');
    setError(error.message);
  } finally {
    setLoading(false);
  }
}

function clearQuestion() {
  elements.questionInput.value = '';
  elements.answerOutput.textContent = 'Your answer will appear here.';
  elements.answerOutput.classList.add('is-placeholder');
  elements.sourceOutput.textContent = 'No sources yet.';
  elements.sourceOutput.classList.add('is-placeholder');
  setConfidenceDisplay(null);
}

function setupDragAndDrop() {
  ['dragenter', 'dragover'].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropZone.classList.remove('dragover');
    });
  });

  elements.dropZone.addEventListener('drop', (event) => {
    handleFiles(event.dataTransfer.files);
  });
}

function bindEvents() {
  elements.themeToggle.addEventListener('change', () => {
    const isDark = elements.themeToggle.checked;
    document.body.classList.toggle('light-theme', !isDark);
    saveTheme(isDark);
  });

  elements.browseBtn.addEventListener('click', () => elements.fileInput.click());
  elements.fileInput.addEventListener('change', (event) => handleFiles(event.target.files));
  elements.uploadBtn.addEventListener('click', uploadFiles);
  elements.askBtn.addEventListener('click', askQuestion);
  elements.clearBtn.addEventListener('click', clearQuestion);

  elements.questionInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      askQuestion();
    }
  });
}

initTheme();
bindEvents();
setupDragAndDrop();
renderUploadedFiles();
replaceLogs([]);
