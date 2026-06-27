from __future__ import annotations

import pytest
from langchain_core.documents import Document

from rag import (
    NOT_FOUND_ANSWER,
    adjust_confidence_for_answer,
    build_retrieval_confidence,
    extract_sources,
    is_context_relevant,
    l2_distance_to_cosine_similarity,
)


def test_l2_distance_to_cosine_similarity_identical_vectors() -> None:
    assert l2_distance_to_cosine_similarity(0.0) == 1.0


def test_l2_distance_to_cosine_similarity_orthogonal_vectors() -> None:
    assert l2_distance_to_cosine_similarity(1.4142135) == pytest.approx(0.0, abs=0.01)


def test_build_retrieval_confidence_returns_high_score_for_close_matches() -> None:
    scored = [
        (Document(page_content="a"), 0.2),
        (Document(page_content="b"), 0.35),
        (Document(page_content="c"), 0.5),
    ]
    confidence = build_retrieval_confidence(scored)
    assert confidence >= 0.75


def test_build_retrieval_confidence_returns_zero_for_empty_results() -> None:
    assert build_retrieval_confidence([]) == 0.0


def test_is_context_relevant_respects_threshold() -> None:
    relevant = [(Document(page_content="policy"), 0.3)]
    irrelevant = [(Document(page_content="policy"), 1.4)]

    assert is_context_relevant(relevant, threshold=0.42) is True
    assert is_context_relevant(irrelevant, threshold=0.42) is False


def test_extract_sources_deduplicates_pages() -> None:
    documents = [
        Document(page_content="one", metadata={"page": 1, "file_name": "a.pdf"}),
        Document(page_content="two", metadata={"page": 1, "file_name": "a.pdf"}),
        Document(page_content="three", metadata={"page": 2, "file_name": "a.pdf"}),
    ]

    sources = extract_sources(documents)
    assert sources == [
        {"page": 1, "file_name": "a.pdf"},
        {"page": 2, "file_name": "a.pdf"},
    ]


def test_adjust_confidence_for_answer_caps_not_found_responses() -> None:
    adjusted = adjust_confidence_for_answer(0.82, NOT_FOUND_ANSWER, has_sources=True)
    assert adjusted <= 0.25


def test_adjust_confidence_for_answer_boosts_substantive_answers() -> None:
    adjusted = adjust_confidence_for_answer(
        0.72,
        "The retention policy requires keeping records for seven years after closure.",
        has_sources=True,
    )
    assert adjusted >= 0.75
