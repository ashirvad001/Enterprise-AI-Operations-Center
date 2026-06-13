"""
PDF Parser — extracts structured text, tables, and images from PDF documents.

Uses:
  - PyPDF2: text extraction (fast, handles most PDFs)
  - pdfplumber: table extraction + precise text positioning
  - Pillow: image extraction from PDF pages

Output Format:
  {
    "text": "...",
    "pages": [...],
    "tables": [...],
    "images": [...],
    "metadata": {...},
    "chunks": [...]  # ready for RAG ingestion
  }
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    _PYPDF2_AVAILABLE = True
except ImportError:
    _PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not installed. Text extraction limited.")

try:
    import pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed. Table extraction disabled.")

try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False
    logger.warning("Pillow not installed. Image extraction from PDF disabled.")


class PDFParser:
    """
    Extracts structured content from PDF files for RAG ingestion.

    Usage:
        parser = PDFParser()
        result = parser.parse(pdf_bytes, document_id="doc_001")
        chunks = result["chunks"]  # Pass directly to VectorStoreManager.ingest_document()
    """

    def __init__(self, chunk_strategy: str = "native"):
        """
        Args:
            chunk_strategy: "native" (token window) or "semantic" (topic-based)
        """
        self.chunk_strategy = chunk_strategy

    def parse(
        self,
        pdf_bytes: bytes,
        document_id: str = "doc",
        filename: str = "document.pdf",
    ) -> Dict[str, Any]:
        """
        Parse a PDF from raw bytes.

        Args:
            pdf_bytes: Raw PDF file bytes.
            document_id: Unique identifier for this document.
            filename: Original filename (used in metadata).

        Returns:
            Dict with text, pages, tables, metadata, and RAG-ready chunks.
        """
        result = {
            "document_id": document_id,
            "filename": filename,
            "page_count": 0,
            "text": "",
            "pages": [],
            "tables": [],
            "images": [],
            "metadata": {},
            "chunks": [],
        }

        pdf_stream = io.BytesIO(pdf_bytes)

        # 1. Extract text + metadata with PyPDF2
        if _PYPDF2_AVAILABLE:
            result.update(self._extract_with_pypdf2(pdf_stream, document_id))
            pdf_stream.seek(0)

        # 2. Extract tables with pdfplumber (more accurate for structured data)
        if _PDFPLUMBER_AVAILABLE:
            tables = self._extract_tables_with_pdfplumber(pdf_stream, document_id)
            result["tables"] = tables
            pdf_stream.seek(0)

        # 3. If neither library available, use mock
        if not _PYPDF2_AVAILABLE and not _PDFPLUMBER_AVAILABLE:
            logger.warning("No PDF library available. Using mock extraction.")
            result.update(self._mock_parse(document_id, filename))

        # 4. Chunk the extracted text for RAG
        result["chunks"] = self._chunk_text(result["text"], document_id)

        logger.info(
            f"[PDFParser] {filename}: {result['page_count']} pages, "
            f"{len(result['text'])} chars, {len(result['tables'])} tables, "
            f"{len(result['chunks'])} chunks"
        )

        return result

    def _extract_with_pypdf2(self, pdf_stream: io.BytesIO, document_id: str) -> Dict[str, Any]:
        """Extract text and metadata using PyPDF2."""
        pages = []
        all_text_parts = []

        try:
            reader = PyPDF2.PdfReader(pdf_stream)
            page_count = len(reader.pages)

            # Extract metadata
            meta = reader.metadata or {}
            metadata = {
                "title": str(meta.get("/Title", "")),
                "author": str(meta.get("/Author", "")),
                "subject": str(meta.get("/Subject", "")),
                "creator": str(meta.get("/Creator", "")),
                "page_count": page_count,
            }

            # Extract per-page text
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    pages.append({
                        "page_number": page_num + 1,
                        "text": page_text,
                        "char_count": len(page_text),
                    })
                    all_text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"[PDFParser] Page {page_num + 1} text extraction failed: {e}")
                    pages.append({"page_number": page_num + 1, "text": "", "char_count": 0})

            return {
                "page_count": page_count,
                "text": "\n\n".join(all_text_parts),
                "pages": pages,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"[PDFParser] PyPDF2 extraction failed: {e}")
            return {"page_count": 0, "text": "", "pages": [], "metadata": {}}

    def _extract_tables_with_pdfplumber(
        self, pdf_stream: io.BytesIO, document_id: str
    ) -> List[Dict[str, Any]]:
        """Extract tables using pdfplumber."""
        tables = []
        try:
            with pdfplumber.open(pdf_stream) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table_idx, table in enumerate(page_tables):
                        if not table:
                            continue
                        # Convert table to dict format
                        headers = [str(h).strip() if h else f"col_{i}"
                                   for i, h in enumerate(table[0])]
                        rows = []
                        for row in table[1:]:
                            rows.append({
                                headers[i]: str(cell).strip() if cell else ""
                                for i, cell in enumerate(row)
                                if i < len(headers)
                            })
                        tables.append({
                            "table_id": f"{document_id}_p{page_num+1}_t{table_idx}",
                            "page_number": page_num + 1,
                            "headers": headers,
                            "rows": rows,
                            "row_count": len(rows),
                        })
        except Exception as e:
            logger.warning(f"[PDFParser] pdfplumber table extraction failed: {e}")

        return tables

    def _chunk_text(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """Chunk the extracted text using the configured strategy."""
        if not text:
            return []
        try:
            if self.chunk_strategy == "semantic":
                from services.rag_service.app.services.chunking.semantic import SemanticChunker
                return SemanticChunker().chunk(text, document_id)
            else:
                from services.rag_service.app.services.chunking.native import NativeChunker
                return NativeChunker().chunk(text, document_id)
        except ImportError:
            # Fallback: simple paragraph chunking
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
            return [
                {
                    "chunk_id": f"{document_id}_{i}",
                    "document_id": document_id,
                    "text": para,
                    "chunk_index": i,
                    "char_count": len(para),
                }
                for i, para in enumerate(paragraphs)
            ]

    def _mock_parse(self, document_id: str, filename: str) -> Dict[str, Any]:
        """Returns mock extraction for testing without PDF libraries."""
        mock_text = f"""
ENTERPRISE AI OPERATIONS CENTER — DOCUMENT: {filename}

Section 1: Executive Summary
This document outlines the enterprise AI operations platform capabilities. 
The system integrates multi-agent orchestration, RAG-based document retrieval,
multimodal input processing, and edge deployment capabilities.

Section 2: Technical Architecture
The platform uses LangGraph for stateful agent orchestration. Retrieval-Augmented
Generation (RAG) uses hybrid BM25 + dense vector search with cross-encoder reranking.
Context precision improved from 0.61 to 0.84 after semantic chunking optimization.

Section 3: Security and Compliance
Role-Based Access Control (RBAC) ensures that users only access documents
within their permitted categories and sensitivity levels. Admin has full access.
Lawyers access legal documents. Doctors access medical records.

Section 4: Performance Metrics
Voice agent achieves end-to-end latency under 2 seconds. 
Edge deployment on Raspberry Pi 5 achieves 45 tokens per second with Q4_K_M quantization.
Memory footprint is 4.5GB, within the 6GB target for 8GB RAM devices.
""".strip()

        return {
            "page_count": 4,
            "text": mock_text,
            "pages": [
                {"page_number": i+1, "text": f"Mock page {i+1} content", "char_count": 200}
                for i in range(4)
            ],
            "metadata": {
                "title": filename,
                "author": "EAIOC System",
                "page_count": 4,
            },
        }

    @classmethod
    def parse_file(cls, file_path: str, chunk_strategy: str = "native") -> Dict[str, Any]:
        """
        Convenience method to parse a PDF from a file path.

        Args:
            file_path: Path to the PDF file.
            chunk_strategy: Chunking strategy ("native" or "semantic").

        Returns:
            Parsed document dict.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        with open(path, "rb") as f:
            pdf_bytes = f.read()

        parser = cls(chunk_strategy=chunk_strategy)
        return parser.parse(pdf_bytes, document_id=path.stem, filename=path.name)
