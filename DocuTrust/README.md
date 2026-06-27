# DocuTrust - Enterprise Advanced RAG Platform with Automated Self-Correction

DocuTrust is a full-stack AI document assistant that lets users upload PDF files, index them locally, and ask grounded questions that are answered only from the uploaded document content. The backend uses FastAPI, LangChain, LangGraph, SentenceTransformers, and FAISS. The LLM layer uses Ollama with `llama3`.

## Project Structure

```text
DocuTrust/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── backend/
│   ├── app.py
│   ├── rag.py
│   ├── graph.py
│   ├── upload/
│   ├── vectorstore/
│   └── requirements.txt
└── README.md
```

## Features

- PDF upload with drag-and-drop support
- Multiple PDF ingestion
- PyPDFLoader-based parsing
- RecursiveCharacterTextSplitter chunking
- SentenceTransformer embeddings using `all-MiniLM-L6-v2`
- Local FAISS vector store persistence
- Ollama `llama3` answer generation
- LangGraph retrieve -> grade -> rewrite -> generate workflow
- Source citations with page metadata
- Responsive split-screen frontend
- Dark mode toggle
- Chat history and live agent logs

## Backend Flow

1. Upload one or more PDFs to `POST /upload`.
2. PDFs are stored in `backend/upload/`.
3. The system loads every uploaded PDF with `PyPDFLoader`.
4. Text is split into chunks of 500 characters with 100 characters of overlap.
5. Chunks are embedded using `all-MiniLM-L6-v2`.
6. Embeddings are stored in FAISS under `backend/vectorstore/`.
7. Questions submitted to `POST /ask` go through the LangGraph workflow:
   - retrieve()
   - grade()
   - rewrite()
   - generate()
8. The answer is restricted to the retrieved document context.

## Prerequisites

- Python 3.10 or newer
- Ollama installed locally
- The `llama3` model pulled locally

You already have the model available. This command confirms it:

```bash
ollama list
```

To test a local chat session with the model:

```bash
ollama run llama3:latest
```

Pull the model if needed:

```bash
ollama pull llama3:latest
```

## Setup

### 1. Open Command Prompt and go to the backend

Use `cd` to move into the backend folder first:

```bat
cd /d C:\Users\heman\OneDrive\Desktop\use\DocuTrust\backend
```

### 2. Create and activate the virtual environment

Run these commands in `cmd`:

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
```

If activation works, your prompt should show `(.venv)`.

### 3. Install dependencies

```bat
pip install -r requirements.txt
```

### 4. Start Ollama

Make sure Ollama is running locally on the default port:

```bat
ollama serve
```

If your Ollama host differs, set:

```bat
set OLLAMA_HOST=http://localhost:11434
set OLLAMA_MODEL=llama3:latest
```

### 5. Run the API

```bat
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

If you want automatic reload during development, use this instead:

```bat
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

### 6. Open the Frontend

Open `frontend/index.html` in your browser. The UI expects the API at `http://127.0.0.1:8000`.

If you want the exact order from scratch in `cmd`, use:

```bat
cd /d C:\Users\heman\OneDrive\Desktop\use\DocuTrust\backend
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
ollama run llama3
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open `frontend\index.html`.

## API Endpoints

### `POST /upload`

Accepts one or more PDF files in a multipart form field named `files`.

Response:

```json
{
  "message": "PDFs uploaded successfully and vector store rebuilt.",
  "files": ["example_1234abcd.pdf"]
}
```

### `POST /ask`

Request:

```json
{
  "question": "What does the policy say about document retention?"
}
```

Response:

```json
{
  "answer": "...",
  "sources": [
    { "page": 5, "file_name": "policy_a.pdf" },
    { "page": 7, "file_name": "policy_b.pdf" }
  ],
  "confidence": 0.86,
  "logs": ["Reading PDF...", "Searching...", "Checking relevance...", "Generating answer..."]
}
```

## Notes

- The vector store is rebuilt from all uploaded PDFs whenever a new upload completes.
- Page numbers are stored in source metadata so citations can be shown in the UI.
- The workflow intentionally falls back to `Information not found in uploaded document.` when the retrieved context is not sufficient.
- The frontend is implemented with plain HTML, CSS, Bootstrap, and JavaScript as requested.

## Production Considerations

- Restrict CORS origins before deployment.
- Move upload and vectorstore directories to durable storage in production.
- Add authentication and authorization for enterprise use.
- Run Ollama on a secured internal host for production environments.
