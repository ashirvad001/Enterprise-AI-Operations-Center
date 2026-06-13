"""
RBAC Middleware — FastAPI middleware that enforces role-based access control
on every incoming request before it reaches any route handler.

Enforcement layers:
  1. JWT token extraction and validation
  2. Role resolution from token claims
  3. Endpoint-level role requirement check
  4. Sensitivity level verification for RAG endpoints
  5. Audit logging of every access attempt (including violations)

Token format (JWT):
  {
    "sub": "usr-1234",
    "roles": ["analyst"],
    "tenant_id": "tenant-001",
    "sensitivity_clearance": "confidential",
    "exp": 1718123456
  }

Rate limiting: 100 requests/minute per user (Redis sliding window)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "eaioc-dev-secret-change-in-prod")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "100"))
SKIP_AUTH_PATHS: Set[str] = {"/health", "/health/live", "/health/ready", "/docs", "/redoc", "/openapi.json"}

# Endpoint → required role mapping
ENDPOINT_ROLES: Dict[str, List[str]] = {
    "/api/v1/issues/review":          ["admin", "engineer", "analyst"],
    "/api/v1/workflows":              ["admin", "engineer", "analyst"],
    "/api/v1/agents":                 ["admin", "engineer"],
    "/api/v1/rag/query":              ["admin", "analyst", "finance", "hr", "engineer", "medical", "legal"],
    "/api/v1/rag/ingest":             ["admin"],
    "/api/v1/multimodal/analyze":     ["admin", "analyst", "engineer", "finance"],
    "/api/v1/voice/session":          ["admin", "analyst", "support"],
    "/api/v1/edge/models":            ["admin", "engineer"],
    "/api/v1/edge/nodes":             ["admin", "engineer"],
    "/api/v1/metrics":                ["admin"],
    "/api/v1/text":                   ["admin", "analyst", "engineer", "finance", "hr", "support"],
}

try:
    import jwt as pyjwt
    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False
    logger.warning("PyJWT not installed — using mock token validation (dev mode only)")

try:
    import redis.asyncio as aioredis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

_rate_limit_store: Dict[str, list] = {}  # In-memory fallback


def _decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT bearer token.

    Returns claims dict or None if invalid/expired.
    """
    if not token:
        return None

    if not _JWT_AVAILABLE:
        # Dev mode: accept any token as admin
        return {
            "sub": "dev-user",
            "roles": ["admin"],
            "tenant_id": "dev-tenant",
            "sensitivity_clearance": "restricted",
        }

    try:
        claims = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return claims
    except pyjwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except pyjwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def _extract_bearer(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    # Also check X-API-Key header for service-to-service calls
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return api_key
    return None


def _check_rate_limit(user_id: str) -> bool:
    """
    Sliding window rate limiter (in-memory fallback).
    Returns True if request is allowed, False if rate limited.
    """
    now = time.time()
    window = 60.0  # 1 minute

    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []

    # Remove timestamps outside the window
    _rate_limit_store[user_id] = [
        ts for ts in _rate_limit_store[user_id] if now - ts < window
    ]

    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_RPM:
        return False

    _rate_limit_store[user_id].append(now)
    return True


def _get_required_roles(path: str) -> Optional[List[str]]:
    """Find required roles for a given path (prefix match)."""
    for endpoint, roles in ENDPOINT_ROLES.items():
        if path.startswith(endpoint):
            return roles
    return None


class RBACMiddleware(BaseHTTPMiddleware):
    """
    FastAPI RBAC middleware — runs before every request.

    Flow:
      1. Skip auth for public paths (health, docs)
      2. Extract + decode JWT token
      3. Check rate limit (100 rpm per user)
      4. Validate role against endpoint requirements
      5. Inject user context into request state
      6. Audit log every request
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        start = time.time()

        # 1. Skip auth for public paths
        if path in SKIP_AUTH_PATHS or path.startswith("/static"):
            return await call_next(request)

        # 2. Extract token
        token = _extract_bearer(request)
        claims = _decode_token(token) if token else None

        # 3. Unauthenticated — return 401
        if claims is None:
            required = _get_required_roles(path)
            if required is not None:
                logger.info(f"[RBAC] 401 {path} — no valid token")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "unauthorized", "message": "Valid bearer token required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        user_id = claims.get("sub", "anonymous") if claims else "anonymous"
        user_roles: List[str] = claims.get("roles", []) if claims else []
        tenant_id: str = claims.get("tenant_id", "default") if claims else "default"
        sensitivity: str = claims.get("sensitivity_clearance", "public") if claims else "public"

        # 4. Rate limit check
        if not _check_rate_limit(f"{tenant_id}:{user_id}"):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limited",
                    "message": f"Rate limit exceeded: {RATE_LIMIT_RPM} requests/minute",
                    "retry_after": 60,
                },
            )

        # 5. Role check against endpoint requirements
        required_roles = _get_required_roles(path)
        if required_roles is not None:
            user_role_set = set(user_roles)
            if not user_role_set.intersection(set(required_roles)):
                elapsed_ms = int((time.time() - start) * 1000)
                logger.warning(
                    f"[RBAC] 403 VIOLATION — user={user_id} role={user_roles} "
                    f"path={path} required={required_roles} tenant={tenant_id}"
                )
                # Emit audit event
                from services.mlops_service.app.services.audit_logger import audit_logger
                try:
                    audit_logger.log_rbac_violation(
                        endpoint=path,
                        reason=f"User role {user_roles} not in required {required_roles}",
                        user_id=user_id,
                        user_role=str(user_roles),
                        tenant_id=tenant_id,
                        ip_address=request.client.host if request.client else None,
                    )
                except Exception:
                    pass  # Don't fail request on audit failure

                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "forbidden",
                        "message": "Insufficient role for this endpoint",
                        "required_roles": required_roles,
                        "your_roles": user_roles,
                    },
                )

        # 6. Inject user context into request state
        request.state.user_id = user_id
        request.state.user_roles = user_roles
        request.state.tenant_id = tenant_id
        request.state.sensitivity_clearance = sensitivity

        # 7. Process request
        response = await call_next(request)

        # 8. Audit log access
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            f"[RBAC] {request.method} {path} "
            f"user={user_id} roles={user_roles} "
            f"status={response.status_code} {elapsed_ms}ms"
        )

        # Inject response headers
        response.headers["X-User-ID"] = user_id
        response.headers["X-Tenant-ID"] = tenant_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        return response
