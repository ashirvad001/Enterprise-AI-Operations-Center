"""
Native Token-Window Chunker — sliding window chunking with token-level control.

Uses tiktoken for accurate GPT-style token counting.
Produces overlapping chunks to preserve context across boundaries.

Parameters:
  chunk_size: 512 tokens (fits in most embedding model context windows)
  overlap: 50 tokens (preserves cross-chunk context)
"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try tiktoken for accurate token counting; fall back to word estimation
try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed. Using word-count approximation for chunking.")

DEFAULT_CHUNK_SIZE = 512    # tokens
DEFAULT_OVERLAP = 50        # tokens
DEFAULT_ENCODING = "cl100k_base"  # GPT-4 / text-embedding-3 encoding


class NativeChunker:
    """
    Sliding-window token-based chunker.

    Produces fixed-size overlapping chunks suitable for embedding models
    with 512-token context windows (e.g., all-MiniLM-L6-v2, text-embedding-3-small).

    Usage:
        chunker = NativeChunker(chunk_size=512, overlap=50)
        chunks = chunker.chunk(text, document_id="doc_001")
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        encoding_name: str = DEFAULT_ENCODING,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._encoding = None
        self._encoding_name = encoding_name

    def _get_encoding(self):
        """Lazy-load tiktoken encoding."""
        if self._encoding is None and _TIKTOKEN_AVAILABLE:
            self._encoding = tiktoken.get_encoding(self._encoding_name)
        return self._encoding

    def _tokenize(self, text: str) -> List[int]:
        """Convert text to token IDs. Falls back to word-level if tiktoken unavailable."""
        enc = self._get_encoding()
        if enc is not None:
            return enc.encode(text)
        else:
            # Word-level approximation (1 word ≈ 1.3 tokens for English)
            words = text.split()
            return list(range(len(words)))  # Just return indices as proxy tokens

    def _detokenize(self, token_ids: List[int], original_text: str) -> str:
        """Convert token IDs back to text."""
        enc = self._get_encoding()
        if enc is not None:
            return enc.decode(token_ids)
        else:
            # Word-level fallback: map indices back to words
            words = original_text.split()
            valid_ids = [i for i in token_ids if i < len(words)]
            return " ".join(words[i] for i in valid_ids)

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self._tokenize(text))

    def chunk(self, text: str, document_id: str = "doc") -> List[dict]:
        """
        Splits text into overlapping token-window chunks.

        Args:
            text: Full document text.
            document_id: Identifier for the source document.

        Returns:
            List of chunk dicts:
            {
                chunk_id, document_id, text, token_count,
                char_count, chunk_index, start_token, end_token
            }
        """
        if not text or not text.strip():
            return []

        tokens = self._tokenize(text)
        total_tokens = len(tokens)

        if total_tokens <= self.chunk_size:
            # Document fits in one chunk
            return [{
                "chunk_id": f"{document_id}_0",
                "document_id": document_id,
                "text": text.strip(),
                "token_count": total_tokens,
                "char_count": len(text),
                "chunk_index": 0,
                "start_token": 0,
                "end_token": total_tokens,
            }]

        chunks = []
        chunk_index = 0
        start = 0

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]

            # Reconstruct text from tokens
            if _TIKTOKEN_AVAILABLE and self._get_encoding():
                chunk_text = self._get_encoding().decode(chunk_tokens)
            else:
                # Word-level fallback
                words = text.split()
                chunk_text = " ".join(words[start:end])

            chunks.append({
                "chunk_id": f"{document_id}_{chunk_index}",
                "document_id": document_id,
                "text": chunk_text.strip(),
                "token_count": len(chunk_tokens),
                "char_count": len(chunk_text),
                "chunk_index": chunk_index,
                "start_token": start,
                "end_token": end,
            })

            chunk_index += 1

            # Advance by chunk_size - overlap (sliding window)
            next_start = start + self.chunk_size - self.overlap
            if next_start <= start:  # Safety: prevent infinite loop
                break
            start = next_start

        logger.info(
            f"[NativeChunker] {document_id}: {total_tokens} tokens → "
            f"{len(chunks)} chunks (size={self.chunk_size}, overlap={self.overlap})"
        )

        return chunks


def chunk_document(
    text: str,
    document_id: str = "doc",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[dict]:
    """
    Convenience function to chunk a document with default settings.
    Equivalent to NativeChunker().chunk(text, document_id).
    """
    chunker = NativeChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk(text, document_id)
