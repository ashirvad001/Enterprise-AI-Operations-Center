"""
Semantic Chunker — splits documents by semantic topic change rather than fixed token windows.

Algorithm:
  1. Split into sentences using simple regex
  2. Embed each sentence with sentence-transformers
  3. Compute cosine similarity between adjacent sentences
  4. When similarity drops below threshold → topic break → new chunk
  5. Merge chunks smaller than min_chunk_size with neighbors

Benefits over sliding window:
  - Chunks align with conceptual boundaries (better retrieval)
  - Avoids splitting mid-concept
  - Reduces false retrievals from topic bleed-over
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try sentence-transformers; fall back to mock if not installed
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Using mock embeddings for chunking.")

DEFAULT_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.5   # Below this → new topic chunk
MIN_CHUNK_CHARS = 200
MAX_CHUNK_CHARS = 2000


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a_arr = np.array(a, dtype=float)
    b_arr = np.array(b, dtype=float)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex (avoids NLTK dependency)."""
    # Split on sentence-ending punctuation followed by space + capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
    # Filter out empty strings and very short fragments
    return [s.strip() for s in sentences if len(s.strip()) > 10]


class SemanticChunker:
    """
    Splits documents into semantically coherent chunks.

    Usage:
        chunker = SemanticChunker()
        chunks = chunker.chunk(text, document_id="doc_001")
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        min_chunk_chars: int = MIN_CHUNK_CHARS,
        max_chunk_chars: int = MAX_CHUNK_CHARS,
    ):
        self.similarity_threshold = similarity_threshold
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self._model: Optional[SentenceTransformer] = None
        self._model_name = model_name

    def _load_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None and _ST_AVAILABLE:
            logger.info(f"Loading SentenceTransformer: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)

    def _embed_sentences(self, sentences: List[str]) -> List[List[float]]:
        """Embed a list of sentences. Uses real model or mock."""
        self._load_model()
        if self._model is not None:
            embeddings = self._model.encode(sentences, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Mock: return deterministic hash-based vectors (for testing)
            return [
                [float(ord(c) % 100) / 100.0 for c in (s[:384] + "0" * 384)[:384]]
                for s in sentences
            ]

    def _find_breakpoints(self, similarities: List[float]) -> List[int]:
        """
        Identify sentence indices where a topic change occurs.
        A breakpoint occurs where similarity drops below the threshold.
        """
        breakpoints = []
        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                breakpoints.append(i + 1)  # Break after sentence i
        return breakpoints

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """Merge chunks that are too small into their neighbor."""
        merged = []
        i = 0
        while i < len(chunks):
            if len(chunks[i]) < self.min_chunk_chars and i + 1 < len(chunks):
                merged.append(chunks[i] + " " + chunks[i + 1])
                i += 2
            else:
                merged.append(chunks[i])
                i += 1
        return merged

    def _split_large_chunks(self, chunks: List[str]) -> List[str]:
        """Split chunks that exceed max_chunk_chars at sentence boundaries."""
        result = []
        for chunk in chunks:
            if len(chunk) <= self.max_chunk_chars:
                result.append(chunk)
            else:
                # Force split at sentence boundaries
                sentences = _split_into_sentences(chunk)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) > self.max_chunk_chars:
                        if current:
                            result.append(current.strip())
                        current = sent
                    else:
                        current = (current + " " + sent).strip()
                if current:
                    result.append(current.strip())
        return result

    def chunk(self, text: str, document_id: str = "doc") -> List[dict]:
        """
        Semantically chunk a document.

        Args:
            text: Full document text.
            document_id: Identifier for the source document.

        Returns:
            List of chunk dicts: {chunk_id, document_id, text, char_count, chunk_index}
        """
        if not text or not text.strip():
            return []

        sentences = _split_into_sentences(text)
        if len(sentences) <= 1:
            return [{
                "chunk_id": f"{document_id}_0",
                "document_id": document_id,
                "text": text.strip(),
                "char_count": len(text),
                "chunk_index": 0,
            }]

        logger.debug(f"[SemanticChunker] Embedding {len(sentences)} sentences for {document_id}")

        # Embed all sentences
        embeddings = self._embed_sentences(sentences)

        # Compute adjacent similarities
        similarities = [
            _cosine_similarity(embeddings[i], embeddings[i + 1])
            for i in range(len(embeddings) - 1)
        ]

        # Find topic breakpoints
        breakpoints = self._find_breakpoints(similarities)

        # Build initial chunks from breakpoints
        chunks_raw: List[str] = []
        prev_idx = 0
        for bp in breakpoints:
            chunk_sentences = sentences[prev_idx:bp]
            if chunk_sentences:
                chunks_raw.append(" ".join(chunk_sentences))
            prev_idx = bp
        # Last chunk
        remaining = sentences[prev_idx:]
        if remaining:
            chunks_raw.append(" ".join(remaining))

        # Post-process
        chunks_raw = self._merge_small_chunks(chunks_raw)
        chunks_raw = self._split_large_chunks(chunks_raw)

        logger.info(
            f"[SemanticChunker] {document_id}: {len(sentences)} sentences → "
            f"{len(chunks_raw)} semantic chunks"
        )

        return [
            {
                "chunk_id": f"{document_id}_{i}",
                "document_id": document_id,
                "text": chunk_text.strip(),
                "char_count": len(chunk_text),
                "chunk_index": i,
            }
            for i, chunk_text in enumerate(chunks_raw)
            if chunk_text.strip()
        ]
