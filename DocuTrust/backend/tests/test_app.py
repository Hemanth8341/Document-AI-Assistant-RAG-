from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import app as app_module
import graph as graph_module
import rag
from app import app
from tests.conftest import DeterministicEmbeddings


@pytest.fixture(autouse=True)
def reset_storage(tmp_path, monkeypatch):
    upload_dir = tmp_path / "upload"
    vectorstore_dir = tmp_path / "vectorstore"
    upload_dir.mkdir()
    vectorstore_dir.mkdir()

    monkeypatch.setattr(app_module, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(app_module, "VECTORSTORE_DIR", vectorstore_dir)
    monkeypatch.setattr(rag, "get_embeddings", lambda: DeterministicEmbeddings())
    yield {"upload_dir": upload_dir, "vectorstore_dir": vectorstore_dir}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _seed_vectorstore(vectorstore_dir, documents: list[Document]) -> None:
    vectorstore = FAISS.from_documents(documents, DeterministicEmbeddings())
    vectorstore.save_local(str(vectorstore_dir))


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_rejects_empty_request(client: TestClient) -> None:
    response = client.post("/upload", files=[])
    assert response.status_code == 422


def test_upload_accepts_pdf_and_returns_logs(client: TestClient, reset_storage, monkeypatch) -> None:
    def fake_rebuild(upload_dir, vectorstore_dir):
        return 2, 5, [
            "Loaded 2 page(s) from uploaded PDFs.",
            "Created 5 searchable chunks.",
            "Index ready — you can now ask questions.",
        ]

    monkeypatch.setattr(app_module, "rebuild_vectorstore_from_uploads", fake_rebuild)

    response = client.post(
        "/upload",
        files={"files": ("policy.pdf", b"%PDF-1.4 sample", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["files"] == ["policy.pdf"] or payload["files"][0].endswith(".pdf")
    assert payload["chunk_count"] == 5
    assert payload["page_count"] == 2
    assert any("Receiving PDF" in log for log in payload["logs"])
    assert any("Index ready" in log for log in payload["logs"])


def test_ask_requires_existing_vectorstore(client: TestClient) -> None:
    response = client.post("/ask", json={"question": "What is the retention policy?"})
    assert response.status_code == 400


def test_ask_returns_answer_logs_and_confidence(client: TestClient, reset_storage) -> None:
    documents = [
        Document(
            page_content="The document retention policy requires keeping records for seven years.",
            metadata={"page": 1, "file_name": "policy.pdf"},
        )
    ]
    _seed_vectorstore(reset_storage["vectorstore_dir"], documents)

    fake_answer = "The retention policy is seven years."

    with patch.object(graph_module, "generate_answer", return_value=fake_answer):
        with patch.object(graph_module, "rewrite_query", side_effect=lambda question: question):
            response = client.post("/ask", json={"question": "What is the retention policy?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == fake_answer
    assert isinstance(payload["confidence"], float)
    assert payload["confidence"] >= 0.05
    assert payload["logs"]
    assert payload["logs"][0] == "Loading FAISS vector index..."


def test_ask_rejects_empty_question(client: TestClient) -> None:
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 422
