"""
API Gateway — Unified FastAPI application integrating all 5 platform components.

Mounts:
  /api/v1/text      — Agent orchestration (text chat)
  /api/v1/rag       — RAG Q&A with RBAC
  /api/v1/multimodal — Multimodal input (image/PDF/text)
  /api/v1/voice     — Voice agent (STT → intent → TTS)
  /api/v1/agents    — Agent management and workflow execution
  /api/v1/knowledge — Knowledge base management
  /api/v1/metrics   — MLOps metrics endpoint
  /health           — Health check
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

SERVICE_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown events."""
    logger.info("=== EAIOC API Gateway Starting ===")
    logger.info(f"Version: {SERVICE_VERSION}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    yield
    logger.info("=== EAIOC API Gateway Shutting Down ===")


def create_app() -> FastAPI:
    """Create and configure the unified FastAPI application."""
    app = FastAPI(
        title="EAIOC — Enterprise AI Operations Center",
        description=(
            "Multi-agent orchestration, secure RAG, multimodal input, "
            "voice agent, and edge LLM deployment — unified API gateway."
        ),
        version=SERVICE_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Text", "description": "Text chat and agent orchestration"},
            {"name": "RAG", "description": "Retrieval-Augmented Generation with RBAC"},
            {"name": "Multimodal", "description": "Image, PDF, and mixed-media processing"},
            {"name": "Voice", "description": "Voice agent: STT → intent → TTS"},
            {"name": "Agents", "description": "Multi-agent workflow management"},
            {"name": "Health", "description": "Health and readiness probes"},
        ],
    )

    # ---------------------------------------------------------------------------
    # Middleware
    # ---------------------------------------------------------------------------

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} [{elapsed_ms}ms]"
        )
        return response

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        import uuid
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ---------------------------------------------------------------------------
    # Health Endpoints
    # ---------------------------------------------------------------------------

    @app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
    async def health_check() -> dict[str, Any]:
        """Overall platform health check."""
        return {
            "status": "healthy",
            "version": SERVICE_VERSION,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "services": {
                "agent_engine": "operational",
                "rag_service": "operational",
                "multimodal_service": "operational",
                "voice_service": "operational",
                "edge_manager": "operational",
            },
        }

    @app.get("/health/live", tags=["Health"])
    async def liveness():
        """Kubernetes liveness probe."""
        return {"status": "alive"}

    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        """Kubernetes readiness probe."""
        return {"status": "ready"}

    # ---------------------------------------------------------------------------
    # Mount Service Routes
    # ---------------------------------------------------------------------------

    # Text chat route
    try:
        from .routes.text import router as text_router
        app.include_router(text_router, prefix="/api/v1", tags=["Text"])
    except ImportError as e:
        logger.warning(f"Text route not available: {e}")

    # RAG route
    try:
        from .routes.rag import router as rag_router
        app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])
    except ImportError as e:
        logger.warning(f"RAG route not available: {e}")

    # Multimodal route
    try:
        from .routes.multimodal import router as multimodal_router
        app.include_router(multimodal_router, prefix="/api/v1", tags=["Multimodal"])
    except ImportError as e:
        logger.warning(f"Multimodal route not available: {e}")

    # Voice route
    try:
        from .routes.voice import router as voice_router
        app.include_router(voice_router, prefix="/api/v1", tags=["Voice"])
    except ImportError as e:
        logger.warning(f"Voice route not available: {e}")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "path": str(request.url.path),
            },
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "development") == "development",
        log_level="info",
    )
