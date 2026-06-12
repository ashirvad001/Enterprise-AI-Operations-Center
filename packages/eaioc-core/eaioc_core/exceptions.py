from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
import uuid
import datetime

class APIException(Exception):
    """
    Base exception for all API errors.
    Formats errors according to RFC 7807 Problem Details.
    """
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        error_type: str,
        instance: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.error_type = f"https://eaioc.dev/errors/{error_type}"
        self.instance = instance
        self.extra = extra or {}
        super().__init__(detail)

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    FastAPI exception handler for APIException.
    Returns an RFC 7807 compliant JSON response.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    content = {
        "type": exc.error_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": exc.instance or request.url.path,
        "request_id": request_id,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
    }
    
    if exc.extra:
        content.update(exc.extra)
        
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers={
            "Content-Type": "application/problem+json"
        }
    )
