from __future__ import annotations

from unittest.mock import patch

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import graph as graph_module
import rag
from graph import run_rag_workflow


def test_run_rag_workflow_generates_answer_with_mocked_llm(
    sample_documents: list[Document],
    upload_dir,
    vectorstore_dir,
    patched_embeddings,
) -> None:
    vectorstore = FAISS.from_documents(sample_documents, rag.get_embeddings())
    vectorstore.save_local(str(vectorstore_dir))

    def fake_generate(question: str, context: str) -> str:
        return "The document retention policy requires keeping records for seven years."

    with patch.object(graph_module, "generate_answer", side_effect=fake_generate):
        with patch.object(graph_module, "rewrite_query", side_effect=lambda question: question):
            result = run_rag_workflow(
                "What is the document retention policy?",
                upload_dir,
                vectorstore_dir,
            )

    assert "seven years" in result["answer"].lower()
    assert result["sources"]
    assert result["confidence"] > 0
    assert any("Searching" in log or "Retrieved" in log for log in result["logs"])
    assert result["logs"][0] == "Loading FAISS vector index..."


def test_run_rag_workflow_returns_fallback_without_documents(
    upload_dir,
    vectorstore_dir,
    patched_embeddings,
) -> None:
    empty_vectorstore = FAISS.from_documents(
        [Document(page_content="Unrelated content about cooking recipes.", metadata={"page": 1, "file_name": "x.pdf"})],
        rag.get_embeddings(),
    )
    empty_vectorstore.save_local(str(vectorstore_dir))

    with patch.object(graph_module, "generate_answer", return_value=rag.NOT_FOUND_ANSWER):
        with patch.object(graph_module, "rewrite_query", side_effect=lambda question: question):
            result = run_rag_workflow("What is the CEO salary?", upload_dir, vectorstore_dir)

    assert rag.NOT_FOUND_ANSWER in result["answer"]
    assert result["confidence"] <= 0.25


def test_decide_after_grade_routes_to_rewrite_when_weak() -> None:
    state = {"is_relevant": False, "rewrite_attempts": 0}
    assert graph_module.decide_after_grade(state) == "rewrite"


def test_decide_after_grade_routes_to_generate_after_rewrite_limit() -> None:
    state = {"is_relevant": False, "rewrite_attempts": graph_module.MAX_REWRITE_ATTEMPTS}
    assert graph_module.decide_after_grade(state) == "generate"
