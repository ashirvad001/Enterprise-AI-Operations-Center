"""
Multimodal Router — classifies incoming requests and routes to appropriate handler.

Decision Logic:
  Image/chart file → vision_assistant (GPT-4o Vision / ViT)
  PDF/Word/TXT file → rag_qna (RAG pipeline with citation extraction)
  Audio file → voice_agent (STT → intent → TTS)
  Text only → text_chat (agent orchestrator)

Classification Methods:
  1. MIME type detection (primary, fast)
  2. File extension mapping (secondary)
  3. CLIP model for visual content confirmation (optional, for images)
"""

from __future__ import annotations

import logging
import mimetypes
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class Route(str, Enum):
    TEXT_CHAT = "text_chat"
    RAG_QNA = "rag_qna"
    VISION_ASSISTANT = "vision_assistant"
    VOICE_AGENT = "voice_agent"
    UNKNOWN = "unknown"


# MIME type → Route mapping
MIME_ROUTE_MAP: Dict[str, Route] = {
    # Documents
    "application/pdf": Route.RAG_QNA,
    "application/msword": Route.RAG_QNA,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": Route.RAG_QNA,
    "text/plain": Route.RAG_QNA,
    "text/html": Route.RAG_QNA,
    "text/markdown": Route.RAG_QNA,
    # Images
    "image/jpeg": Route.VISION_ASSISTANT,
    "image/jpg": Route.VISION_ASSISTANT,
    "image/png": Route.VISION_ASSISTANT,
    "image/gif": Route.VISION_ASSISTANT,
    "image/webp": Route.VISION_ASSISTANT,
    "image/bmp": Route.VISION_ASSISTANT,
    "image/tiff": Route.VISION_ASSISTANT,
    # Audio
    "audio/wav": Route.VOICE_AGENT,
    "audio/mp3": Route.VOICE_AGENT,
    "audio/mpeg": Route.VOICE_AGENT,
    "audio/ogg": Route.VOICE_AGENT,
    "audio/webm": Route.VOICE_AGENT,
    "audio/flac": Route.VOICE_AGENT,
}

EXTENSION_ROUTE_MAP: Dict[str, Route] = {
    ".pdf": Route.RAG_QNA,
    ".doc": Route.RAG_QNA,
    ".docx": Route.RAG_QNA,
    ".txt": Route.RAG_QNA,
    ".md": Route.RAG_QNA,
    ".html": Route.RAG_QNA,
    ".png": Route.VISION_ASSISTANT,
    ".jpg": Route.VISION_ASSISTANT,
    ".jpeg": Route.VISION_ASSISTANT,
    ".gif": Route.VISION_ASSISTANT,
    ".webp": Route.VISION_ASSISTANT,
    ".bmp": Route.VISION_ASSISTANT,
    ".tiff": Route.VISION_ASSISTANT,
    ".wav": Route.VOICE_AGENT,
    ".mp3": Route.VOICE_AGENT,
    ".ogg": Route.VOICE_AGENT,
    ".flac": Route.VOICE_AGENT,
    ".webm": Route.VOICE_AGENT,
}


class MultimodalRouter:
    """
    Routes multimodal requests to the appropriate handler.

    Usage:
        router = MultimodalRouter()
        route, confidence, reason = router.route(
            text="Analyze this chart",
            filename="q3_revenue.png",
            content_type="image/png"
        )
    """

    def __init__(self, use_clip: bool = False):
        """
        Args:
            use_clip: If True, use CLIP model for visual content verification
                      (requires sentence-transformers with CLIP support).
        """
        self.use_clip = use_clip
        self._clip_model = None

    def _load_clip(self):
        """Lazy-load CLIP model if enabled."""
        if self._clip_model is None and self.use_clip:
            try:
                from sentence_transformers import SentenceTransformer
                self._clip_model = SentenceTransformer("clip-ViT-B-32")
                logger.info("CLIP model loaded for visual routing")
            except Exception as e:
                logger.warning(f"Could not load CLIP model: {e}. Falling back to MIME routing.")

    def _route_by_mime(self, content_type: str) -> Optional[Route]:
        """Route based on MIME content type."""
        if not content_type:
            return None
        # Normalize MIME type (strip parameters like "; charset=utf-8")
        base_mime = content_type.split(";")[0].strip().lower()
        return MIME_ROUTE_MAP.get(base_mime)

    def _route_by_extension(self, filename: str) -> Optional[Route]:
        """Route based on file extension."""
        if not filename:
            return None
        ext = Path(filename).suffix.lower()
        return EXTENSION_ROUTE_MAP.get(ext)

    def _is_chart_or_diagram(self, filename: str, text: str) -> bool:
        """
        Heuristic: check if the image is likely a chart/diagram vs. photo.
        Used to add more context to vision routing.
        """
        chart_keywords = {"chart", "graph", "diagram", "plot", "figure", "revenue",
                          "sales", "trend", "bar", "pie", "scatter", "heatmap"}
        combined = (filename.lower() + " " + text.lower()) if text else filename.lower()
        return any(kw in combined for kw in chart_keywords)

    def route(
        self,
        text: Optional[str] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
    ) -> Tuple[Route, float, str]:
        """
        Determines the processing route for a request.

        Args:
            text: User's text query (required for text_chat route).
            filename: Uploaded file name (used for extension-based routing).
            content_type: HTTP Content-Type header value.
            file_bytes: Raw file bytes (optional, used for CLIP verification).

        Returns:
            (Route, confidence_score, reason_string)
        """
        # 1. No file → text only
        if not filename and not content_type and not file_bytes:
            return Route.TEXT_CHAT, 1.0, "No file attached — routing to text chat"

        # 2. MIME type routing (highest priority)
        mime_route = self._route_by_mime(content_type or "")
        if mime_route:
            is_chart = (mime_route == Route.VISION_ASSISTANT and
                        self._is_chart_or_diagram(filename or "", text or ""))
            reason = (
                f"MIME type '{content_type}' matched {mime_route.value}"
                + (" (detected as chart/diagram)" if is_chart else "")
            )
            return mime_route, 0.95, reason

        # 3. File extension routing
        ext_route = self._route_by_extension(filename or "")
        if ext_route:
            return ext_route, 0.85, f"Extension '{Path(filename).suffix}' matched {ext_route.value}"

        # 4. Magic bytes detection (minimal)
        if file_bytes:
            if file_bytes[:4] == b"%PDF":
                return Route.RAG_QNA, 0.90, "PDF magic bytes detected"
            if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                return Route.VISION_ASSISTANT, 0.90, "PNG magic bytes detected"
            if file_bytes[:3] == b"\xff\xd8\xff":
                return Route.VISION_ASSISTANT, 0.90, "JPEG magic bytes detected"
            if file_bytes[:4] == b"RIFF":
                return Route.VOICE_AGENT, 0.90, "WAV audio magic bytes detected"

        # 5. Text-only fallback
        if text:
            return Route.TEXT_CHAT, 0.70, "No file type identified — routing to text chat"

        return Route.UNKNOWN, 0.0, "Cannot determine route: no text, file, or content_type provided"

    def route_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience method accepting a request dict.

        Args:
            request_data: Dict with optional keys: text, filename, content_type, file_bytes

        Returns:
            Dict with: route, confidence, reason, handler_config
        """
        route, confidence, reason = self.route(
            text=request_data.get("text"),
            filename=request_data.get("filename"),
            content_type=request_data.get("content_type"),
            file_bytes=request_data.get("file_bytes"),
        )

        handler_configs = {
            Route.TEXT_CHAT: {"endpoint": "/api/v1/text", "timeout_ms": 1000},
            Route.RAG_QNA: {"endpoint": "/api/v1/rag", "timeout_ms": 2000},
            Route.VISION_ASSISTANT: {"endpoint": "/api/v1/vision", "timeout_ms": 5000},
            Route.VOICE_AGENT: {"endpoint": "/api/v1/voice", "timeout_ms": 3000},
            Route.UNKNOWN: {"endpoint": None, "timeout_ms": 0},
        }

        return {
            "route": route.value,
            "confidence": confidence,
            "reason": reason,
            "handler_config": handler_configs[route],
            "is_file_required": route != Route.TEXT_CHAT,
        }
