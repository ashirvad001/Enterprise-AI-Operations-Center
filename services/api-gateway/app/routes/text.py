"""
Text Chat Route — agent orchestration endpoint for the API Gateway.

POST /api/v1/text
  Request: {"query": str, "session_id": str (optional)}
  Response: {"response": str, "agent_plan": dict, "latency_ms": int}

Latency target: <1s (uses mock/simple LLM path for fast response)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class TextRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000, description="User's text query")
    session_id: Optional[str] = Field(default=None, description="Session ID for multi-turn")
    model: Optional[str] = Field(default=None, description="Override default LLM model")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)


class TextResponse(BaseModel):
    session_id: str
    response: str
    latency_ms: int
    model_used: str
    tokens_used: Optional[int] = None


@router.post("/text", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def text_chat(request: TextRequest):
    """
    Direct text chat via the agent orchestration pipeline.

    Routes to the agent engine for complex queries involving
    code review, planning, or analysis. Simple Q&A routes to
    the local Ollama runtime directly.
    """
    start = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    # Try Ollama direct for fast response
    response_text = None
    model_used = "mock"

    try:
        from services.edge_manager.app.services.runtime import OllamaRuntime
        import os
        runtime = OllamaRuntime()
        if await runtime.is_available():
            result = await runtime.generate(
                prompt=request.query,
                system="You are a helpful AI assistant. Answer concisely and accurately.",
                temperature=request.temperature,
                max_tokens=1024,
            )
            response_text = result.text
            model_used = result.model
    except Exception:
        pass

    if not response_text:
        # Fallback mock response
        response_text = (
            f"I understand your query: '{request.query[:100]}'. "
            "This is a mock response from the EAIOC text chat endpoint. "
            "Configure OLLAMA_BASE_URL to get real LLM responses."
        )
        model_used = "mock"

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "data": {
            "session_id": session_id,
            "response": response_text,
            "latency_ms": elapsed_ms,
            "model_used": model_used,
        }
    }
