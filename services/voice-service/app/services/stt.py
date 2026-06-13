"""
Speech-to-Text (STT) — transcribes audio to text using Whisper.

Backend Priority:
  1. faster-whisper (CTranslate2-optimized, best speed) — local
  2. openai-whisper (original, requires VRAM) — local
  3. OpenAI Whisper API — cloud
  4. Mock transcription — testing

Latency Target: <500ms for standard customer support audio (5-15 second clips)
"""

from __future__ import annotations

import io
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")   # tiny/base/small/medium/large-v3
WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", "auto")          # auto/faster/openai-lib/api/mock
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")            # cpu/cuda/mps

try:
    import faster_whisper
    _FASTER_WHISPER_AVAILABLE = True
except ImportError:
    _FASTER_WHISPER_AVAILABLE = False

try:
    import whisper as openai_whisper
    _OPENAI_WHISPER_AVAILABLE = True
except ImportError:
    _OPENAI_WHISPER_AVAILABLE = False


class TranscriptionResult(BaseModel):
    """Output of the STT service."""
    text: str = Field(description="Transcribed text")
    language: str = Field(default="en", description="Detected language code")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int = Field(default=0, description="Transcription latency in milliseconds")
    backend_used: str = Field(default="mock")
    segments: list = Field(default_factory=list, description="Word-level segments with timestamps")


class WhisperSTT:
    """
    Unified STT service wrapping multiple Whisper backends.

    Usage:
        stt = WhisperSTT()
        result = await stt.transcribe(audio_bytes)
        print(result.text)
    """

    def __init__(self):
        self._faster_model = None
        self._openai_model = None

    def _load_faster_whisper(self):
        """Lazy-load faster-whisper model."""
        if self._faster_model is None and _FASTER_WHISPER_AVAILABLE:
            logger.info(f"Loading faster-whisper model: {WHISPER_MODEL_SIZE}")
            compute_type = "int8" if WHISPER_DEVICE == "cpu" else "float16"
            self._faster_model = faster_whisper.WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=compute_type,
            )

    def _load_openai_whisper(self):
        """Lazy-load openai-whisper model."""
        if self._openai_model is None and _OPENAI_WHISPER_AVAILABLE:
            logger.info(f"Loading openai-whisper model: {WHISPER_MODEL_SIZE}")
            self._openai_model = openai_whisper.load_model(WHISPER_MODEL_SIZE)

    async def _transcribe_faster_whisper(self, audio_bytes: bytes) -> Optional[TranscriptionResult]:
        """Transcribe using faster-whisper (fastest local option)."""
        self._load_faster_whisper()
        if self._faster_model is None:
            return None

        try:
            import asyncio
            import tempfile
            import os

            # Write to temp file (faster-whisper reads from file)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            start = time.time()
            segments, info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._faster_model.transcribe(
                    tmp_path,
                    beam_size=5,
                    language="en",
                    vad_filter=True,
                )
            )
            os.unlink(tmp_path)

            elapsed_ms = int((time.time() - start) * 1000)
            segment_list = list(segments)
            text = " ".join(s.text.strip() for s in segment_list)

            return TranscriptionResult(
                text=text.strip(),
                language=info.language,
                confidence=min(1.0, info.language_probability),
                latency_ms=elapsed_ms,
                backend_used="faster-whisper",
                segments=[
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in segment_list
                ],
            )
        except Exception as e:
            logger.warning(f"faster-whisper failed: {e}")
            return None

    async def _transcribe_openai_lib(self, audio_bytes: bytes) -> Optional[TranscriptionResult]:
        """Transcribe using original openai-whisper library."""
        self._load_openai_whisper()
        if self._openai_model is None:
            return None

        try:
            import asyncio
            import tempfile
            import os
            import numpy as np

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            start = time.time()
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._openai_model.transcribe(tmp_path, language="en")
            )
            os.unlink(tmp_path)

            elapsed_ms = int((time.time() - start) * 1000)
            return TranscriptionResult(
                text=result.get("text", "").strip(),
                language=result.get("language", "en"),
                confidence=0.90,
                latency_ms=elapsed_ms,
                backend_used="openai-whisper",
            )
        except Exception as e:
            logger.warning(f"openai-whisper lib failed: {e}")
            return None

    async def _transcribe_openai_api(self, audio_bytes: bytes) -> Optional[TranscriptionResult]:
        """Transcribe using OpenAI Whisper API (cloud, requires API key)."""
        if not OPENAI_API_KEY:
            return None
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

            start = time.time()
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"

            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                language="en",
            )
            elapsed_ms = int((time.time() - start) * 1000)

            return TranscriptionResult(
                text=transcription.text.strip(),
                language=getattr(transcription, "language", "en"),
                confidence=0.95,
                latency_ms=elapsed_ms,
                backend_used="openai-api",
            )
        except Exception as e:
            logger.warning(f"OpenAI Whisper API failed: {e}")
            return None

    def _mock_transcription(self, audio_bytes: bytes) -> TranscriptionResult:
        """Mock transcription for testing."""
        size_kb = len(audio_bytes) // 1024
        # Simulate realistic customer support queries
        mock_texts = [
            "I need to track my order number 12345. It was supposed to arrive yesterday.",
            "I want to return a product that I received last week. It's defective.",
            "Can you help me cancel my subscription? I've been charged twice this month.",
            "I have a complaint about the customer service I received yesterday.",
            "What is the status of my refund request submitted three days ago?",
        ]
        import hashlib
        idx = int(hashlib.md5(audio_bytes[:16]).hexdigest(), 16) % len(mock_texts)
        return TranscriptionResult(
            text=mock_texts[idx],
            language="en",
            confidence=0.92,
            latency_ms=50 + (size_kb * 2),
            backend_used="mock",
        )

    async def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """
        Transcribe audio to text using the best available backend.

        Args:
            audio_bytes: Raw audio bytes (WAV, MP3, OGG, FLAC, WEBM).

        Returns:
            TranscriptionResult with text, language, confidence, and latency.
        """
        if not audio_bytes:
            return TranscriptionResult(text="", language="en", confidence=0.0,
                                        latency_ms=0, backend_used="empty")

        backend = WHISPER_BACKEND
        result = None

        if backend in ("auto", "faster"):
            result = await self._transcribe_faster_whisper(audio_bytes)

        if result is None and backend in ("auto", "openai-lib"):
            result = await self._transcribe_openai_lib(audio_bytes)

        if result is None and backend in ("auto", "api") and OPENAI_API_KEY:
            result = await self._transcribe_openai_api(audio_bytes)

        if result is None:
            logger.info("[STT] Using mock transcription (no backend available)")
            result = self._mock_transcription(audio_bytes)

        logger.info(
            f"[STT] Transcribed {len(audio_bytes)//1024}KB audio in {result.latency_ms}ms "
            f"via {result.backend_used}. Text: '{result.text[:60]}'"
        )
        return result
