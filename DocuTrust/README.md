# DocuTrust - Enterprise Advanced RAG Platform with Automated Self-Correction

DocuTrust is a full-stack, enterprise-grade AI document assistant that lets users upload PDF files, index them locally into a FAISS vector store, and ask grounded questions that are answered strictly from document context with zero hallucinations. 

The backend is built with FastAPI, LangChain, LangGraph, SentenceTransformers, and FAISS, powered locally by Ollama (`llama3`). The frontend is a modern, 100/10 glassmorphism web dashboard featuring interactive agent workflow visualization, live logs, citation snippet modals, preset prompts, dark/light theme toggle, and live server health metrics.

## Project Structure

```text
DocuTrust/
├── frontend/
│   ├── index.html        # 3-column glassmorphism dashboard (Hub, Workflow, Studio)
│   ├── style.css         # Modern design tokens, glassmorphism, workflow stepper, animations
│   └── script.js         # REST client, Markdown parser, stats polling, interactive modals
├── backend/
│   ├── app.py            # FastAPI endpoints (/upload, /ask, /stats, /clear, /health)
│   ├── rag.py            # PDF loader, chunking, SentenceTransformer embeddings, FAISS engine
│   ├── graph.py          # LangGraph state machine (Retrieve -> Grade -> Rewrite -> Generate)
│   ├── upload/           # Local PDF storage directory
│   ├── vectorstore/      # FAISS vector store index files
│   ├── tests/            # Pytest automated test suite
│   └── requirements.txt  # Python dependencies
└── README.md
```

## Features

- **100/10 Modern Glassmorphism UI**: High-contrast typography (`Plus Jakarta Sans`, `Inter`, `JetBrains Mono`), smooth dark/light mode toggle, and micro-animations.
- **Interactive Agent Stepper**: Real-time visual progress bar tracking LangGraph workflow steps (`Retrieve ➔ Grade ➔ Rewrite ➔ Generate`).
- **Source Citation Snippets**: Clickable source badges that launch modal dialogs displaying the exact text snippet extracted from the PDF page.
- **Rich Markdown Formatting**: Renders formatted lists, bold text, headers, and code blocks in generated answers.
- **Quick Preset Prompts**: One-click prompt chips (`Summarize Document`, `Key Deadlines`, `Policies & Figures`).
- **Live System Health & Stats Monitoring**: Periodic health polling showing live server status, total indexed PDFs, FAISS index state, and Ollama connectivity.
- **File Management & Store Reset**: Delete individual uploaded PDFs or clear the entire index on demand via `POST /clear`.
- **Keyboard Shortcuts**: `Ctrl + Enter` shortcut to send questions quickly.
- **Copy to Clipboard**: One-click copying for generated answers and system execution logs.

## Backend Flow

1. Upload PDFs to `POST /upload`.
2. PDFs are stored in `backend/upload/`.
3. PDFs are parsed page-by-page with `PyPDFLoader` preserving metadata (`file_name`, 1-indexed `page`).
4. Text is split into chunks of 800 characters with 150 characters of overlap using `RecursiveCharacterTextSplitter`.
5. Chunks are embedded using `all-MiniLM-L6-v2` via `SentenceTransformer`.
6. Embeddings are stored in FAISS under `backend/vectorstore/`.
7. Questions submitted to `POST /ask` pass through the **LangGraph** self-correction workflow:
   - `retrieve()`: Fetch top document chunks from FAISS.
   - `grade()`: Evaluate chunk similarity against a relevance threshold (`0.42`).
   - `rewrite()`: Rephrase search query using Ollama if context relevance is low.
   - `generate()`: Generate answer strictly grounded in retrieved context using Ollama `llama3`.
8. The response returns answer markdown, source page citations with snippets, confidence score, and real-time logs.

## Prerequisites

- Python 3.10 or newer
- Ollama installed locally with the `llama3` model pulled (`ollama pull llama3`)

## Quick Start (Windows)

1. Open Command Prompt and navigate to `backend`:
   ```cmd
   cd /d C:\Users\heman\OneDrive\Desktop\RAG-LLM\DocuTrust\backend
   ```

2. Activate virtual environment and install dependencies:
   ```cmd
   call .venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

3. Start the FastAPI server:
   ```cmd
   python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
   ```

4. Open the Frontend:
   Open `frontend/index.html` in your browser.

## Running Tests

Run the backend test suite with `pytest`:

```cmd
python -m pytest tests -v
```

## API Endpoints

- `GET /health`: Returns API status `{"status": "ok"}`.
- `GET /stats`: Returns system statistics (file count, file list, FAISS index state, Ollama online status).
- `POST /upload`: Uploads PDF files and rebuilds the FAISS vector index.
- `DELETE /upload/{filename}`: Deletes a specific uploaded PDF and updates the vector index.
- `POST /clear`: Clears all uploaded PDFs and resets the vector store.
- `POST /ask`: Accepts a question JSON payload, executes the LangGraph workflow, and returns the grounded answer, source citations with text snippets, confidence score, and agent logs.

