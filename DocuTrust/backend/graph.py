from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, StateGraph

from rag import (
    NOT_FOUND_ANSWER,
    adjust_confidence_for_answer,
    build_retrieval_confidence,
    extract_sources,
    format_context_documents,
    generate_answer,
    is_context_relevant,
    rewrite_query,
    search_documents_with_scores,
)

RELEVANCE_THRESHOLD = 0.42
MAX_REWRITE_ATTEMPTS = 1


class RAGState(TypedDict, total=False):
    question: str
    rewritten_question: str
    retrieved_documents: list[Document]
    scored_documents: list[tuple[Document, float]]
    is_relevant: bool
    confidence: float
    answer: str
    sources: list[dict[str, object]]
    logs: list[str]
    rewrite_attempts: int


def append_log(state: RAGState, message: str) -> list[str]:
    return [*(state.get("logs", [])), message]


def retrieve_node(state: RAGState, vectorstore_dir: Path) -> RAGState:
    query = state.get("rewritten_question") or state["question"]
    scored_documents = search_documents_with_scores(query, vectorstore_dir)
    retrieved_documents = [document for document, _ in scored_documents]

    log_message = f"Retrieved {len(retrieved_documents)} chunk(s) for query."
    if state.get("rewritten_question"):
        log_message = f"Retrieved {len(retrieved_documents)} chunk(s) using rewritten query."

    return {
        "scored_documents": scored_documents,
        "retrieved_documents": retrieved_documents,
        "logs": append_log(state, log_message),
    }


def grade_node(state: RAGState) -> RAGState:
    scored_documents = state.get("scored_documents", [])
    is_relevant = is_context_relevant(scored_documents, RELEVANCE_THRESHOLD)
    confidence = build_retrieval_confidence(scored_documents)

    if is_relevant:
        grade_message = "Context is relevant — proceeding to answer generation."
    elif state.get("rewrite_attempts", 0) >= MAX_REWRITE_ATTEMPTS:
        grade_message = "Context still weak after rewrite — generating best-effort answer."
    else:
        grade_message = "Context weak — rewriting query for another retrieval pass."

    return {
        "is_relevant": is_relevant,
        "confidence": confidence,
        "logs": append_log(state, grade_message),
    }


def rewrite_node(state: RAGState) -> RAGState:
    rewritten_question = rewrite_query(state["question"])
    return {
        "rewritten_question": rewritten_question,
        "rewrite_attempts": state.get("rewrite_attempts", 0) + 1,
        "logs": append_log(state, f"Rewrote query to: {rewritten_question}"),
    }


def generate_node(state: RAGState) -> RAGState:
    documents = state.get("retrieved_documents", [])
    confidence = state.get("confidence", 0.0)

    if not documents:
        return {
            "answer": NOT_FOUND_ANSWER,
            "sources": [],
            "confidence": 0.0,
            "logs": append_log(state, "No chunks retrieved — returning fallback answer."),
        }

    context = format_context_documents(documents)
    answer = generate_answer(state["question"], context)
    sources = extract_sources(documents)
    confidence = adjust_confidence_for_answer(confidence, answer, bool(sources))

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "logs": append_log(state, "Generated grounded answer from retrieved context."),
    }


def decide_after_grade(state: RAGState) -> str:
    if state.get("is_relevant"):
        return "generate"
    if state.get("rewrite_attempts", 0) >= MAX_REWRITE_ATTEMPTS:
        return "generate"
    return "rewrite"


def build_graph(vectorstore_dir: Path):
    workflow = StateGraph(RAGState)

    workflow.add_node("retrieve", lambda state: retrieve_node(state, vectorstore_dir))
    workflow.add_node("grade", grade_node)
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("generate", generate_node)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        decide_after_grade,
        {"generate": "generate", "rewrite": "rewrite"},
    )
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", END)

    return workflow.compile()


def run_rag_workflow(question: str, upload_dir: Path, vectorstore_dir: Path) -> dict:
    del upload_dir  # Kept for API compatibility; indexing happens at upload time.

    graph = build_graph(vectorstore_dir)
    final_state = graph.invoke(
        {
            "question": question,
            "logs": [
                "Loading FAISS vector index...",
                f"Searching for: \"{question.strip()}\"",
            ],
            "rewrite_attempts": 0,
        }
    )

    return {
        "answer": final_state.get("answer", NOT_FOUND_ANSWER),
        "sources": final_state.get("sources", []),
        "confidence": final_state.get("confidence", 0.0),
        "logs": final_state.get("logs", []),
    }
