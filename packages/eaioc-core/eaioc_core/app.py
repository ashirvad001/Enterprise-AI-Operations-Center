from typing import Any, Callable, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

def create_app(
    title: str,
    description: str,
    version: str,
    openapi_tags: Optional[list[Dict[str, Any]]] = None,
) -> FastAPI:
    """
    Factory function to create a standardized FastAPI application.
    Includes built-in health checks and standard configuration.
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        openapi_tags=openapi_tags,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Standard Health Check Endpoints
    @app.get("/health/live", tags=["Health"], status_code=status.HTTP_200_OK)
    async def liveness_probe() -> dict[str, str]:
        """Kubernetes liveness probe."""
        return {"status": "alive"}

    @app.get("/health/ready", tags=["Health"], status_code=status.HTTP_200_OK)
    async def readiness_probe() -> dict[str, str]:
        """Kubernetes readiness probe."""
        # Services should override this or add dependencies to check DB/Redis connections
        return {"status": "ready"}

    @app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
    async def health_check() -> dict[str, Any]:
        """Overall system health."""
        return {
            "status": "healthy",
            "version": version,
        }

    return app
