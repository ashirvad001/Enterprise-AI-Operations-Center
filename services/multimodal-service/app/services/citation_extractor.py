"""
Citation Extractor — maps RAG answer sentences back to source documents.

Given:
  - query: "What is the RBAC policy?"
  - answer: "RBAC requires doctors to have role=doctor to access medical documents."
  - retrieved_chunks: [{"text": "...", "document_id": "...", "page_number": 3, ...}]

Produces:
  [
    {
      "claim": "RBAC requires doctors to have role=doctor",
      "source": "doc_001",
      "page": 3,
      "supporting_text": "Doctors must be assigned role=doctor to access medical records.",
      "confidence": 0.87,
    }
  ]

Algorithm:
  1. Sentence-split the answer
  2. For each answer sentence, find the chunk with highest BM25/embedding overlap
  3. Extract the supporting span from that chunk
  4. Return citation with page number and document title
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _split_into_claims(text: str) -> List[str]:
    """Split answer text into individual claim sentences."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _word_overlap_score(claim: str, chunk_text: str) -> float:
    """Compute normalized word overlap between a claim and a chunk."""
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "and", "or", "in",
                 "of", "to", "for", "with", "that", "this", "it", "be", "by"}
    claim_words = set(claim.lower().split()) - stopwords
    chunk_words = set(chunk_text.lower().split()) - stopwords
    if not claim_words:
        return 0.0
    overlap = len(claim_words & chunk_words)
    return overlap / len(claim_words)


def _find_supporting_span(claim: str, chunk_text: str, window: int = 200) -> str:
    """
    Finds the most relevant span within a chunk that supports a claim.

    Uses a sliding window to find the portion of the chunk with highest
    word overlap with the claim.
    """
    words = chunk_text.split()
    if len(words) <= 30:
        return chunk_text

    claim_words = set(claim.lower().split())
    best_score = 0.0
    best_start = 0

    # Slide a 30-word window across the chunk
    window_size = 30
    for i in range(0, max(1, len(words) - window_size + 1)):
        window_words = set(words[i:i + window_size])
        overlap = len(claim_words & {w.lower() for w in window_words})
        score = overlap / max(len(claim_words), 1)
        if score > best_score:
            best_score = score
            best_start = i

    span_words = words[best_start:best_start + window_size]
    span = " ".join(span_words)

    # Trim to window characters
    if len(span) > window:
        span = span[:window] + "..."

    return span


def find_supporting_text(
    query: str,
    answer: str,
    chunks: List[Dict[str, Any]],
    min_confidence: float = 0.2,
) -> List[Dict[str, Any]]:
    """
    Maps each claim in the answer to its supporting source chunk.

    Args:
        query: The original user query.
        answer: The LLM-generated answer text.
        chunks: Retrieved chunks, each must have 'text', 'document_id', 'chunk_id'.
                Optional: 'page_number', 'filename', 'chunk_index'.
        min_confidence: Minimum overlap score to include a citation.

    Returns:
        List of citation dicts, one per answer claim (only those above min_confidence).
    """
    claims = _split_into_claims(answer)
    citations = []

    for claim in claims:
        best_chunk = None
        best_score = 0.0

        for chunk in chunks:
            chunk_text = chunk.get("text", chunk.get("content", ""))
            score = _word_overlap_score(claim, chunk_text)
            if score > best_score:
                best_score = score
                best_chunk = chunk

        if best_chunk is None or best_score < min_confidence:
            continue

        chunk_text = best_chunk.get("text", best_chunk.get("content", ""))
        supporting_span = _find_supporting_span(claim, chunk_text)

        citation = {
            "claim": claim,
            "document_id": best_chunk.get("document_id", "unknown"),
            "chunk_id": best_chunk.get("chunk_id", "unknown"),
            "page_number": best_chunk.get("page_number", best_chunk.get("chunk_index", 1)),
            "filename": best_chunk.get("filename", best_chunk.get("document_id", "document")),
            "supporting_text": supporting_span,
            "confidence": round(best_score, 3),
        }
        citations.append(citation)

    logger.info(
        f"[CitationExtractor] {len(claims)} claims → {len(citations)} citations "
        f"(min_confidence={min_confidence})"
    )
    return citations


class CitationExtractor:
    """
    High-level citation extraction service.

    Usage:
        extractor = CitationExtractor()
        citations = extractor.extract(query, answer, retrieved_chunks)
        formatted = extractor.format_citations(citations)
    """

    def __init__(self, min_confidence: float = 0.2):
        self.min_confidence = min_confidence

    def extract(
        self,
        query: str,
        answer: str,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract citations from an answer given the retrieved chunks."""
        return find_supporting_text(query, answer, chunks, self.min_confidence)

    def format_citations(self, citations: List[Dict[str, Any]]) -> str:
        """
        Format citations as a markdown references section.

        Example output:
            ## Sources
            [1] document.pdf, page 3 — "RBAC requires doctors to have role=doctor..."
            [2] policy_doc.pdf, page 7 — "Admin has unrestricted access to all documents..."
        """
        if not citations:
            return ""

        lines = ["## Sources\n"]
        for i, cite in enumerate(citations, 1):
            filename = cite.get("filename", cite.get("document_id", "unknown"))
            page = cite.get("page_number", "N/A")
            span = cite.get("supporting_text", "")[:100]
            confidence = cite.get("confidence", 0)
            lines.append(
                f"[{i}] **{filename}**, page {page} *(confidence: {confidence:.0%})* — "
                f'"{span}"'
            )

        return "\n".join(lines)

    def compute_correctness_rate(
        self,
        citations: List[Dict[str, Any]],
        threshold: float = 0.5,
    ) -> float:
        """
        Computes the citation correctness rate (proportion above confidence threshold).

        Target: >90%
        """
        if not citations:
            return 0.0
        correct = sum(1 for c in citations if c.get("confidence", 0) >= threshold)
        return correct / len(citations)
