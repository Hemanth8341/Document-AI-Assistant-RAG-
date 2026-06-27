# DocuTrust Project Explanation

DocuTrust is a full-stack AI document assistant for PDF question answering. It is designed to answer only from uploaded document content, provide source citations, and support a future self-correction workflow through LangGraph.

## What the project does

Users upload one or more PDF files. The backend reads the PDFs, splits them into chunks, creates embeddings, stores those embeddings in a local FAISS index, and then answers questions using only the retrieved document context. If the system cannot find the answer in the uploaded documents, it returns a fixed fallback message instead of inventing an answer.

## Main technologies

- Frontend: HTML, CSS, Bootstrap, JavaScript
- Backend: FastAPI
- PDF loader: PyPDFLoader
- Text splitting: RecursiveCharacterTextSplitter
- Embeddings: SentenceTransformer with all-MiniLM-L6-v2
- Vector store: FAISS
- LLM: Ollama with llama3
- Orchestration: LangChain and LangGraph

## Folder structure

- frontend/
  - index.html: Main user interface
  - style.css: Custom styling and responsive layout
  - script.js: Browser-side logic for upload, chat, logs, and theme toggle
- backend/
  - app.py: FastAPI routes and app bootstrap
  - rag.py: PDF loading, chunking, embeddings, FAISS, Ollama calls
  - graph.py: LangGraph workflow for retrieve, grade, rewrite, generate
  - upload/: Stored PDF files
  - vectorstore/: Saved FAISS index
  - requirements.txt: Python dependencies
- README.md: Quick start and run instructions

## Data flow

1. The user uploads PDF files in the frontend.
2. The frontend sends them to `POST /upload`.
3. The backend stores the PDFs in `backend/upload/`.
4. PyPDFLoader reads the PDF pages.
5. RecursiveCharacterTextSplitter creates overlapping chunks.
6. SentenceTransformer creates embeddings for the chunks.
7. FAISS stores the embeddings locally in `backend/vectorstore/`.
8. The user asks a question in the frontend.
9. The frontend sends the question to `POST /ask`.
10. The backend retrieves relevant chunks from FAISS.
11. LangGraph grades relevance and optionally rewrites the query.
12. Ollama generates the final answer only from the retrieved context.
13. The response includes the answer, citations, confidence, and workflow logs.

## Workflow nodes

The LangGraph flow is:

- retrieve(): fetch relevant chunks from FAISS
- grade(): judge whether the retrieved chunks are relevant enough
- rewrite(): rewrite the query if retrieval quality is weak
- generate(): build the final grounded answer

## API endpoints

### POST /upload

Accepts one or more PDF files.

Returns:
- success message
- list of stored PDF file names

### POST /ask

Accepts a JSON body with a question.

Returns:
- answer
- sources with page numbers and file names
- confidence score
- agent logs

## How to run on Windows cmd

1. Open Command Prompt.
2. Change into the backend folder.
3. Create and activate the virtual environment.
4. Install dependencies.
5. Start Ollama or verify it is already available.
6. Start the FastAPI server.
7. Open the frontend file in your browser.

Example commands:

```bat
cd /d C:\Users\heman\OneDrive\Desktop\use\DocuTrust\backend
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
ollama run llama3
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

## Notes for Ollama

You already confirmed that `llama3:latest` exists locally. That means the model is ready to use.

Useful checks:

```bat
ollama list
ollama run llama3:latest
```

When setting the backend environment variable, use:

```bat
set OLLAMA_MODEL=llama3:latest
```

## Suggested next improvements

- Add a dedicated upload status panel in the frontend.
- Persist chat history between browser refreshes.
- Add authentication for enterprise use.
- Add stricter source ranking and confidence scoring.
- Add automated tests for the upload and question endpoints.
- Add Docker support for a one-command local startup.
