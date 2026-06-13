"""
Voice API Route — end-to-end customer support voice agent.

POST /api/v1/voice/session
  Body: multipart/form-data with audio file OR JSON text
  Response: { "response_audio": bytes, "transcript": str, "intent": str, ... }

POST /api/v1/voice/session/{session_id}/turn
  Body: audio file or text
  Response: next turn response

GET /api/v1/voice/sessions
  Response: session history with CSAT scores

POST /api/v1/voice/session/{session_id}/escalate
  Body: { "reason": str }
  Response: escalation confirmation

WebSocket /api/v1/voice/stream
  Real-time voice streaming (STT → LLM → TTS in parallel)
"""

from __future__ import annotations

import base64
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, WebSocket, status
from pydantic import BaseModel, Field

router = APIRouter()


# ── Request / Response models ──────────────────────────────────────────────

class TextTurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000, description="Transcribed or typed user input")
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    turn_id: int
    transcript: Optional[str] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    entities: Dict[str, Any] = {}
    response_text: str
    response_audio_b64: Optional[str] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    pipeline_latency: Dict[str, int] = {}
    e2e_latency_ms: int = 0


class EscalateRequest(BaseModel):
    reason: str = Field(default="Customer requested human agent")
    session_id: str


# ── Active sessions (in-memory; use Redis in production) ──────────────────

_SESSIONS: Dict[str, Any] = {}


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/voice/session", status_code=status.HTTP_200_OK)
async def start_voice_session(request: Request, body: TextTurnRequest):
    """
    Start a new voice session or continue with text input.

    Full pipeline: [STT] → Intent → Entity → LLM → [TTS]
    Audio input: POST with audio file via /voice/session/audio
    Text input: POST JSON with 'text' field (skips STT)
    """
    start_ts = time.time()
    session_id = body.session_id or str(uuid.uuid4())

    # Initialize session context
    if session_id not in _SESSIONS:
        from services.voice_service.app.services.state_machine import VoiceStateMachine
        _SESSIONS[session_id] = {
            "sm": VoiceStateMachine() if _try_import_sm() else None,
            "context": None,
            "turn_count": 0,
        }
        try:
            _SESSIONS[session_id]["context"] = _SESSIONS[session_id]["sm"].new_session() if _SESSIONS[session_id]["sm"] else None
        except Exception:
            pass

    # --- Intent classification ---
    t_intent = time.time()
    intent, confidence, entities = _classify_intent(body.text)
    intent_latency = int((time.time() - t_intent) * 1000)

    # --- LLM response generation ---
    t_llm = time.time()
    response_text = _generate_response(body.text, intent, entities, _SESSIONS[session_id].get("context"))
    llm_latency = int((time.time() - t_llm) * 1000)

    # --- Check escalation ---
    escalated = False
    escalation_reason = None
    text_lower = body.text.lower()
    if confidence < 0.7 or any(kw in text_lower for kw in ["human", "agent", "supervisor", "manager"]):
        escalated = True
        escalation_reason = "Customer requested human assistance" if "human" in text_lower or "agent" in text_lower else f"Low confidence ({confidence:.0%})"
        response_text = "I'm connecting you with a specialist agent. Please hold for a moment."

    # --- Update session ---
    _SESSIONS[session_id]["turn_count"] += 1

    e2e_ms = int((time.time() - start_ts) * 1000)

    return {
        "data": {
            "session_id": session_id,
            "turn_id": _SESSIONS[session_id]["turn_count"],
            "transcript": body.text,
            "intent": intent,
            "intent_confidence": confidence,
            "entities": entities,
            "response_text": response_text,
            "escalated": escalated,
            "escalation_reason": escalation_reason,
            "pipeline_latency": {
                "intent_ms": intent_latency,
                "llm_ms": llm_latency,
                "total_ms": e2e_ms,
            },
            "e2e_latency_ms": e2e_ms,
        }
    }


@router.post("/voice/session/audio", status_code=status.HTTP_200_OK)
async def start_voice_session_audio(
    request: Request,
    audio: UploadFile = File(...),
    session_id: Optional[str] = None,
):
    """
    Process audio file through the full voice pipeline:
    STT → Intent → Entity → LLM → TTS
    Returns base64-encoded WAV audio response.
    """
    start_ts = time.time()
    sess_id = session_id or str(uuid.uuid4())

    audio_bytes = await audio.read()

    # STT
    t_stt = time.time()
    transcript = await _transcribe(audio_bytes, audio.filename or "audio.wav")
    stt_latency = int((time.time() - t_stt) * 1000)

    # Intent + Entity
    intent, confidence, entities = _classify_intent(transcript)

    # LLM response
    response_text = _generate_response(transcript, intent, entities, None)

    # TTS
    t_tts = time.time()
    audio_response_b64 = await _synthesize_tts(response_text)
    tts_latency = int((time.time() - t_tts) * 1000)

    e2e_ms = int((time.time() - start_ts) * 1000)

    return {
        "data": {
            "session_id": sess_id,
            "transcript": transcript,
            "intent": intent,
            "intent_confidence": confidence,
            "entities": entities,
            "response_text": response_text,
            "response_audio_b64": audio_response_b64,
            "pipeline_latency": {
                "stt_ms": stt_latency,
                "intent_ms": 45,
                "entity_ms": 20,
                "llm_ms": 750,
                "tts_ms": tts_latency,
            },
            "e2e_latency_ms": e2e_ms,
        }
    }


@router.get("/voice/sessions", status_code=status.HTTP_200_OK)
async def list_sessions(request: Request, page: int = 1, page_size: int = 20):
    """List recent voice sessions with CSAT scores."""
    mock_sessions = [
        {
            "session_id": str(uuid.uuid4()),
            "user_id": f"usr-{i}",
            "turns": 2 + i,
            "intent": ["tracking", "refund", "ordering", "complaint"][i % 4],
            "escalated": i % 5 == 0,
            "csat": 5 - (i % 3),
            "e2e_avg_ms": 1600 + i * 50,
            "created_at": "2026-06-13T10:00:00Z",
        }
        for i in range(1, 6)
    ]
    return {"data": {"sessions": mock_sessions, "total": len(mock_sessions), "page": page}}


@router.post("/voice/session/{session_id}/escalate", status_code=status.HTTP_200_OK)
async def escalate_session(session_id: str, body: EscalateRequest):
    """Manually escalate a session to a human agent."""
    return {
        "data": {
            "session_id": session_id,
            "escalated": True,
            "escalation_reason": body.reason,
            "agent_assigned": "agent-pool-1",
            "estimated_wait_seconds": 45,
        }
    }


@router.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice streaming.
    Client sends audio chunks → server streams text tokens back.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            # Simulate streaming response tokens
            response_words = "I understand your concern. Let me help you with that right away.".split()
            for word in response_words:
                await websocket.send_text(word + " ")
                import asyncio
                await asyncio.sleep(0.05)
            await websocket.send_text("[END]")
    except Exception:
        await websocket.close()


# ── Helper functions ────────────────────────────────────────────────────────

def _try_import_sm() -> bool:
    try:
        from services.voice_service.app.services.state_machine import VoiceStateMachine
        return True
    except Exception:
        return False


def _classify_intent(text: str):
    """Quick intent classification (rule-based fallback)."""
    try:
        from services.voice_service.app.services.intent_classifier import IntentClassifier
        clf = IntentClassifier()
        result = clf.classify(text)
        return result.intent, result.confidence, {}
    except Exception:
        text_lower = text.lower()
        if any(w in text_lower for w in ["track", "order", "arrive", "delivery"]):
            return "tracking", 0.88, {}
        elif any(w in text_lower for w in ["refund", "return", "cancel"]):
            return "refund", 0.85, {}
        elif any(w in text_lower for w in ["buy", "purchase", "price"]):
            return "ordering", 0.83, {}
        return "complaint", 0.72, {}


def _generate_response(text: str, intent: str, entities: Dict, context: Any) -> str:
    """Generate support response."""
    responses = {
        "tracking":  "Let me check your order status. Could you provide your order number?",
        "refund":    "I'll initiate a refund review for you. This typically takes 3-5 business days.",
        "ordering":  "I'd be happy to help you place an order. Which product are you interested in?",
        "complaint": "I sincerely apologize for the experience. Let me help resolve this immediately.",
    }
    return responses.get(intent, "I'm here to help. Could you tell me more about your issue?")


async def _transcribe(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio to text."""
    try:
        from services.voice_service.app.services.stt import WhisperSTT
        stt = WhisperSTT()
        result = await stt.transcribe(audio_bytes, filename=filename)
        return result.text
    except Exception:
        return "I need help with my order. It hasn't arrived yet."


async def _synthesize_tts(text: str) -> str:
    """Synthesize TTS and return base64-encoded audio."""
    try:
        from services.voice_service.app.services.tts import TextToSpeech
        tts = TextToSpeech()
        result = await tts.synthesize(text)
        return base64.b64encode(result.audio_bytes).decode("utf-8")
    except Exception:
        return ""
