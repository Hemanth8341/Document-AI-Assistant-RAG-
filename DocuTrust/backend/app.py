from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from graph import run_rag_workflow
from rag import (
    clear_all_uploads,
    delete_uploaded_pdf,
    get_system_stats,
    rebuild_vectorstore_from_uploads,
    save_uploaded_pdf,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "upload"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

app = FastAPI(
    title="DocuTrust API",
    description="Enterprise Advanced RAG Platform with Automated Self-Correction",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question about uploaded documents")

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty.")
        return cleaned


class SourceItem(BaseModel):
    page: int
    file_name: str | None = None
    snippet: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    confidence: float
    logs: List[str]


class UploadResponse(BaseModel):
    message: str
    files: List[str]
    page_count: int
    chunk_count: int
    logs: List[str]


@app.on_event("startup")
def ensure_directories() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def system_stats() -> dict[str, object]:
    return get_system_stats(UPLOAD_DIR, VECTORSTORE_DIR)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "DocuTrust API is running",
        "health": "/health",
        "stats": "/stats",
        "docs": "/docs",
        "upload": "/upload",
        "ask": "/ask",
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_pdfs(files: List[UploadFile] = File(...)) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")

    logs = ["Receiving PDF file(s)..."]
    saved_files: list[str] = []

    for uploaded_file in files:
        saved_path = await save_uploaded_pdf(uploaded_file, UPLOAD_DIR)
        saved_files.append(saved_path.name)
        logs.append(f"Saved {saved_path.name}.")

    page_count, chunk_count, rebuild_logs = rebuild_vectorstore_from_uploads(UPLOAD_DIR, VECTORSTORE_DIR)
    logs.extend(rebuild_logs)

    return UploadResponse(
        message="PDFs uploaded successfully and vector store rebuilt.",
        files=saved_files,
        page_count=page_count,
        chunk_count=chunk_count,
        logs=logs,
    )


@app.delete("/upload/{filename}")
def delete_file(filename: str) -> dict[str, object]:
    page_count, chunk_count, logs = delete_uploaded_pdf(filename, UPLOAD_DIR, VECTORSTORE_DIR)
    return {
        "message": f"File {filename} deleted successfully.",
        "page_count": page_count,
        "chunk_count": chunk_count,
        "logs": logs,
    }


@app.post("/clear")
def clear_index() -> dict[str, object]:
    logs = clear_all_uploads(UPLOAD_DIR, VECTORSTORE_DIR)
    return {
        "message": "All documents and vector store index cleared.",
        "logs": logs,
    }


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = run_rag_workflow(request.question, UPLOAD_DIR, VECTORSTORE_DIR)

    sources = [
        SourceItem(
            page=item["page"],
            file_name=item.get("file_name"),
            snippet=item.get("snippet"),
        )
        for item in result["sources"]
    ]

    return AskResponse(
        answer=result["answer"],
        sources=sources,
        confidence=result["confidence"],
        logs=result["logs"],
    )

