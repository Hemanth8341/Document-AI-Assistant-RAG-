from __future__ import annotations

import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 6
NOT_FOUND_ANSWER = "Information not found in uploaded document."


class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def get_embeddings() -> SentenceTransformerEmbeddings:
    return SentenceTransformerEmbeddings(EMBEDDING_MODEL_NAME)


def ensure_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


async def save_uploaded_pdf(uploaded_file: UploadFile, upload_dir: Path) -> Path:
    if not uploaded_file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    file_name = Path(uploaded_file.filename).name
    if Path(file_name).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for {file_name}. Only PDF files are allowed.",
        )

    ensure_directory(upload_dir)
    unique_name = f"{Path(file_name).stem}_{uuid.uuid4().hex[:8]}.pdf"
    destination = upload_dir / unique_name

    contents = await uploaded_file.read()
    if not contents:
        raise HTTPException(status_code=400, detail=f"File {file_name} is empty.")

    destination.write_bytes(contents)
    return destination


def load_documents_from_uploads(upload_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for pdf_path in sorted(upload_dir.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf_path))
        loaded_documents = loader.load()
        for document in loaded_documents:
            document.metadata["file_name"] = pdf_path.name
            page_number = document.metadata.get("page")
            if isinstance(page_number, int):
                document.metadata["page"] = page_number + 1
        documents.extend(loaded_documents)
    return documents


def split_documents(documents: Iterable[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(list(documents))


def l2_distance_to_cosine_similarity(distance: float) -> float:
    """Convert L2 distance between unit vectors to cosine similarity."""
    clamped = max(0.0, float(distance))
    cosine = 1.0 - (clamped ** 2) / 2.0
    return max(0.0, min(1.0, cosine))


def rebuild_vectorstore_from_uploads(
    upload_dir: Path,
    vectorstore_dir: Path,
) -> tuple[int, int, list[str]]:
    """Rebuild the FAISS index and return (page_count, chunk_count, workflow_logs)."""
    ensure_directory(upload_dir)
    ensure_directory(vectorstore_dir)

    pdf_count = len(list(upload_dir.glob("*.pdf")))
    logs = [
        f"Found {pdf_count} PDF file(s) in storage.",
        "Loading PDF pages with PyPDFLoader...",
    ]

    documents = load_documents_from_uploads(upload_dir)
    if not documents:
        raise HTTPException(status_code=400, detail="No valid PDFs found. Upload at least one PDF first.")

    logs.append(f"Loaded {len(documents)} page(s) from uploaded PDFs.")
    logs.append(f"Splitting text into {CHUNK_SIZE}-character chunks ({CHUNK_OVERLAP} overlap)...")

    chunks = split_documents(documents)
    logs.append(f"Created {len(chunks)} searchable chunks.")
    logs.append(f"Embedding chunks with {EMBEDDING_MODEL_NAME}...")

    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    vectorstore.save_local(str(vectorstore_dir))

    logs.append("Saved FAISS vector store to disk.")
    logs.append("Index ready — you can now ask questions.")

    return len(documents), len(chunks), logs


def load_vectorstore(vectorstore_dir: Path) -> FAISS | None:
    index_file = vectorstore_dir / "index.faiss"
    if not index_file.exists():
        return None
    return FAISS.load_local(
        str(vectorstore_dir),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def format_context_documents(documents: list[Document]) -> str:
    formatted_chunks: list[str] = []
    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("file_name", "unknown.pdf")
        page = document.metadata.get("page", "unknown")
        formatted_chunks.append(
            f"[Source {index}] File: {source} | Page: {page}\n{document.page_content.strip()}"
        )
    return "\n\n---\n\n".join(formatted_chunks)


def search_documents_with_scores(
    question: str,
    vectorstore_dir: Path,
    top_k: int = TOP_K,
) -> list[tuple[Document, float]]:
    vectorstore = load_vectorstore(vectorstore_dir)
    if vectorstore is None:
        raise HTTPException(status_code=400, detail="Vector store not found. Upload PDFs first.")

    return vectorstore.similarity_search_with_score(question, k=top_k)


def score_documents(scored_documents: list[tuple[Document, float]]) -> list[tuple[Document, float]]:
    """Attach cosine similarity scores derived from FAISS L2 distances."""
    return [
        (document, l2_distance_to_cosine_similarity(distance))
        for document, distance in scored_documents
    ]


def extract_sources(documents: list[Document]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    seen_pairs: set[tuple[object, object]] = set()
    for document in documents:
        page = document.metadata.get("page")
        file_name = document.metadata.get("file_name")
        snippet = document.page_content.strip()[:180] + ("..." if len(document.page_content.strip()) > 180 else "")
        key = (page, file_name)
        if page is None or key in seen_pairs:
            continue
        seen_pairs.add(key)
        sources.append({
            "page": int(page),
            "file_name": file_name,
            "snippet": snippet,
        })
    return sources


def delete_uploaded_pdf(
    file_name: str,
    upload_dir: Path,
    vectorstore_dir: Path,
) -> tuple[int, int, list[str]]:
    target_path = upload_dir / file_name
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail=f"File {file_name} not found in uploads.")

    target_path.unlink()
    logs = [f"Deleted file {file_name}."]

    remaining_pdfs = list(upload_dir.glob("*.pdf"))
    if not remaining_pdfs:
        # Clear vectorstore if no PDFs remain
        import shutil
        if vectorstore_dir.exists():
            shutil.rmtree(vectorstore_dir)
            vectorstore_dir.mkdir(parents=True, exist_ok=True)
        logs.append("No PDFs remaining. Cleared vector store index.")
        return 0, 0, logs

    page_count, chunk_count, rebuild_logs = rebuild_vectorstore_from_uploads(upload_dir, vectorstore_dir)
    logs.extend(rebuild_logs)
    return page_count, chunk_count, logs


def clear_all_uploads(upload_dir: Path, vectorstore_dir: Path) -> list[str]:
    import shutil
    logs = ["Clearing all uploaded files and vector store..."]

    if upload_dir.exists():
        for item in upload_dir.glob("*.pdf"):
            item.unlink()

    if vectorstore_dir.exists():
        shutil.rmtree(vectorstore_dir)
        vectorstore_dir.mkdir(parents=True, exist_ok=True)

    logs.append("All files and vector store index cleared successfully.")
    return logs


def get_system_stats(upload_dir: Path, vectorstore_dir: Path) -> dict[str, object]:
    ensure_directory(upload_dir)
    ensure_directory(vectorstore_dir)

    pdf_files = [f.name for f in upload_dir.glob("*.pdf")]
    has_index = (vectorstore_dir / "index.faiss").exists()

    ollama_online = False
    try:
        import requests
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=2)
        ollama_online = resp.status_code == 200
    except Exception:
        ollama_online = False

    return {
        "file_count": len(pdf_files),
        "files": pdf_files,
        "has_index": has_index,
        "ollama_online": ollama_online,
    }


def build_retrieval_confidence(scored_documents: list[tuple[Document, float]]) -> float:
    """Compute confidence from cosine similarities of retrieved chunks."""
    if not scored_documents:
        return 0.0

    cosine_scores = [
        l2_distance_to_cosine_similarity(distance) for _, distance in scored_documents
    ]
    weights = [1.0 / (index + 1) for index in range(len(cosine_scores))]
    weight_total = sum(weights)
    weighted_average = sum(score * weight for score, weight in zip(cosine_scores, weights)) / weight_total

    top_score = cosine_scores[0]
    blended = (0.65 * top_score) + (0.35 * weighted_average)
    return round(min(0.99, max(0.05, blended)), 2)


def is_context_relevant(scored_documents: list[tuple[Document, float]], threshold: float = 0.42) -> bool:
    if not scored_documents:
        return False
    best_cosine = l2_distance_to_cosine_similarity(scored_documents[0][1])
    return best_cosine >= threshold


def adjust_confidence_for_answer(confidence: float, answer: str, has_sources: bool) -> float:
    normalized_answer = answer.strip().lower()
    if NOT_FOUND_ANSWER.lower() in normalized_answer or not has_sources:
        return round(min(confidence, 0.25), 2)
    if len(answer.strip()) > 40:
        confidence = min(0.99, confidence + 0.08)
    return round(confidence, 2)


def ask_ollama(prompt: str, temperature: float = 0.1) -> str:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3:latest")
    api_url = f"{host.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    import requests

    response = requests.post(api_url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def rewrite_query(question: str) -> str:
    prompt = f"""You improve search queries for a PDF document retrieval system.
Rewrite the user question into a concise search query that preserves key entities, dates, and terms.
Return ONLY the rewritten query with no explanation.

User question:
{question}""".strip()
    rewritten = ask_ollama(prompt, temperature=0.0)
    cleaned = rewritten.strip().strip('"').strip("'")
    return cleaned or question


def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are DocuTrust, a document assistant. Answer ONLY using the context below.

Rules:
1. Use facts directly supported by the context.
2. Be specific — include names, numbers, dates, and policy details when present.
3. If the context does not contain enough information, reply exactly:
"{NOT_FOUND_ANSWER}"
4. Do not invent information or mention that you are an AI.
5. Write in clear, complete sentences. Use bullet points only when listing multiple items.

Context:
{context}

Question:
{question}

Answer:""".strip()
    answer = ask_ollama(prompt, temperature=0.15)
    return answer or NOT_FOUND_ANSWER

