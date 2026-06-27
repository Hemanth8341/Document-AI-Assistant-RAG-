from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class DeterministicEmbeddings(Embeddings):
    """Lightweight embeddings for fast, offline tests."""

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [((byte / 255.0) * 2.0) - 1.0 for byte in digest[:16]]
        magnitude = sum(value * value for value in values) ** 0.5 or 1.0
        return [value / magnitude for value in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(
            page_content="The document retention policy requires keeping records for seven years.",
            metadata={"page": 1, "file_name": "policy_a.pdf"},
        ),
        Document(
            page_content="Employees must submit expense reports within thirty days.",
            metadata={"page": 2, "file_name": "policy_a.pdf"},
        ),
        Document(
            page_content="Remote work is allowed up to three days per week.",
            metadata={"page": 3, "file_name": "policy_b.pdf"},
        ),
    ]


@pytest.fixture
def upload_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "upload"
    directory.mkdir()
    return directory


@pytest.fixture
def vectorstore_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "vectorstore"
    directory.mkdir()
    return directory


@pytest.fixture
def patched_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    import rag

    monkeypatch.setattr(rag, "get_embeddings", lambda: DeterministicEmbeddings())
