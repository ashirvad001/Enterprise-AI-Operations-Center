"""
Text-to-Speech (TTS) — converts response text to audio bytes.

Backend Priority:
  1. Azure TTS (Neural voices, highest quality) — cloud
  2. Google TTS (gTTS) — cloud, free tier
  3. pyttsx3 — local, offline
  4. Mock (silent WAV) — testing

Latency Target: <500ms for typical support response sentences (<200 chars)
"""

from __future__ import annotations

import io
import logging
import os
import struct
import time
from typing import Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
AZURE_VOICE_NAME = os.getenv("AZURE_VOICE_NAME", "en-US-AriaNeural")
TTS_BACKEND = os.getenv("TTS_BACKEND", "auto")  # auto/azure/gtts/pyttsx3/mock

try:
    import azure.cognitiveservices.speech as speechsdk
    _AZURE_AVAILABLE = True
except ImportError:
    _AZURE_AVAILABLE = False

try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False

try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False


class TTSResult(BaseModel):
    """Output of the TTS service."""
    audio_bytes: bytes = Field(description="Raw audio bytes (WAV format)")
    audio_format: str = Field(default="wav")
    sample_rate: int = Field(default=16000)
    duration_ms: int = Field(default=0)
    latency_ms: int = Field(default=0)
    backend_used: str = Field(default="mock")
    text_length: int = Field(default=0)

    model_config = {"arbitrary_types_allowed": True}


def _create_silent_wav(duration_ms: int = 1000, sample_rate: int = 16000) -> bytes:
    """
    Creates a silent WAV file for mock/testing purposes.
    Returns raw WAV bytes.
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    data_bytes = b"\x00\x00" * num_samples  # 16-bit silence

    # WAV header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",                          # ChunkID
        36 + len(data_bytes),             # ChunkSize
        b"WAVE",                          # Format
        b"fmt ",                          # Subchunk1ID
        16,                               # Subchunk1Size (PCM)
        1,                                # AudioFormat (PCM=1)
        1,                                # NumChannels (mono)
        sample_rate,                      # SampleRate
        sample_rate * 2,                  # ByteRate
        2,                                # BlockAlign
        16,                               # BitsPerSample
        b"data",                          # Subchunk2ID
        len(data_bytes),                  # Subchunk2Size
    )
    return header + data_bytes


async def _synthesize_azure(text: str) -> Optional[bytes]:
    """Synthesize speech using Azure Cognitive Services TTS."""
    if not AZURE_SPEECH_KEY or not _AZURE_AVAILABLE:
        return None

    try:
        import asyncio
        config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION,
        )
        config.speech_synthesis_voice_name = AZURE_VOICE_NAME
        config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)

        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: synthesizer.speak_text_async(text).get()
        )

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        else:
            logger.warning(f"Azure TTS failed: {result.reason}")
            return None
    except Exception as e:
        logger.warning(f"Azure TTS error: {e}")
        return None


async def _synthesize_gtts(text: str) -> Optional[bytes]:
    """Synthesize speech using Google TTS (gTTS)."""
    if not _GTTS_AVAILABLE:
        return None

    try:
        import asyncio

        def _synth():
            tts = gTTS(text=text, lang="en", slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()

        mp3_bytes = await asyncio.get_event_loop().run_in_executor(None, _synth)
        return mp3_bytes  # Returns MP3 bytes
    except Exception as e:
        logger.warning(f"gTTS failed: {e}")
        return None


async def _synthesize_pyttsx3(text: str) -> Optional[bytes]:
    """Synthesize speech using pyttsx3 (offline, local)."""
    if not _PYTTSX3_AVAILABLE:
        return None

    try:
        import asyncio
        import tempfile

        def _synth():
            engine = pyttsx3.init()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            with open(tmp_path, "rb") as f:
                data = f.read()
            os.unlink(tmp_path)
            return data

        wav_bytes = await asyncio.get_event_loop().run_in_executor(None, _synth)
        return wav_bytes
    except Exception as e:
        logger.warning(f"pyttsx3 failed: {e}")
        return None


class TextToSpeech:
    """
    Unified TTS service with multi-backend support.

    Usage:
        tts = TextToSpeech()
        result = await tts.synthesize("Your order will arrive by Friday.")
        # result.audio_bytes contains WAV audio
    """

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
    ) -> TTSResult:
        """
        Convert text to speech audio.

        Args:
            text: Response text to synthesize (max ~500 chars for <500ms latency).
            voice: Optional voice name override.

        Returns:
            TTSResult with audio_bytes in WAV format.
        """
        if not text or not text.strip():
            return TTSResult(
                audio_bytes=_create_silent_wav(500),
                latency_ms=0,
                backend_used="empty",
                text_length=0,
            )

        start = time.time()
        audio_bytes = None
        backend_used = "mock"

        backend = TTS_BACKEND

        if backend in ("auto", "azure") and AZURE_SPEECH_KEY:
            audio_bytes = await _synthesize_azure(text)
            if audio_bytes:
                backend_used = "azure"

        if audio_bytes is None and backend in ("auto", "gtts"):
            audio_bytes = await _synthesize_gtts(text)
            if audio_bytes:
                backend_used = "gtts"

        if audio_bytes is None and backend in ("auto", "pyttsx3"):
            audio_bytes = await _synthesize_pyttsx3(text)
            if audio_bytes:
                backend_used = "pyttsx3"

        if audio_bytes is None:
            # Mock: estimate duration from text length (avg 150 words/min speech rate)
            word_count = len(text.split())
            estimated_ms = int((word_count / 150) * 60 * 1000) + 200
            audio_bytes = _create_silent_wav(estimated_ms)
            backend_used = "mock"

        elapsed_ms = int((time.time() - start) * 1000)

        logger.info(
            f"[TTS] Synthesized {len(text)} chars in {elapsed_ms}ms via {backend_used}. "
            f"Audio: {len(audio_bytes)} bytes"
        )

        return TTSResult(
            audio_bytes=audio_bytes,
            audio_format="wav" if backend_used in ("azure", "pyttsx3", "mock") else "mp3",
            sample_rate=16000 if backend_used == "azure" else 22050,
            latency_ms=elapsed_ms,
            backend_used=backend_used,
            text_length=len(text),
        )
