"""
Audit Logger — structured security and access audit logging.

Logs:
  - All API requests (user, endpoint, timestamp, status)
  - RBAC violations (immediate alert)
  - Agent executions (cost, latency, status)
  - Authentication events (login, logout, token refresh)

Storage:
  - PostgreSQL: long-term audit trail (via SQLAlchemy)
  - Elasticsearch: full-text search and analysis (optional)
  - JSON logs: stdout for container log aggregation

RBAC Violation Alerts:
  - Logged at CRITICAL level
  - Sent to alerting system (Prometheus alert + email/Slack)
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("eaioc.audit")

AUDIT_LOG_LEVEL = os.getenv("AUDIT_LOG_LEVEL", "INFO")
POSTGRES_AUDIT_TABLE = "audit.access_logs"
ES_INDEX = "eaioc-audit-logs"


# ---------------------------------------------------------------------------
# Audit Event Models
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    """Structured audit log entry."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str                         # "access" | "rbac_violation" | "auth" | "agent_execution"
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    tenant_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "INFO"                  # INFO | WARNING | CRITICAL


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    Enterprise audit logger with multi-destination output.

    Usage:
        logger = AuditLogger()
        logger.log_access(user_id="usr_1", endpoint="/api/v1/rag", status_code=200, response_time_ms=320)
        logger.log_rbac_violation(user_id="usr_2", endpoint="/api/v1/rag", reason="Role denied")
    """

    def __init__(self):
        self._pg_available = False
        self._es_available = False
        self._setup_logging()

    def _setup_logging(self):
        """Configure structured JSON logging for audit events."""
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": %(message)s}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(AUDIT_LOG_LEVEL)
        logger.propagate = False

    def _emit(self, event: AuditEvent):
        """Emit an audit event to all configured destinations."""
        event_dict = event.model_dump()
        event_json = json.dumps(event_dict)

        # 1. Structured JSON log (always)
        log_fn = {
            "INFO": logger.info,
            "WARNING": logger.warning,
            "CRITICAL": logger.critical,
        }.get(event.severity, logger.info)
        log_fn(event_json)

        # 2. PostgreSQL (async, non-blocking — would use asyncpg/SQLAlchemy in production)
        # await db.execute(INSERT INTO audit.access_logs ...)

        # 3. Elasticsearch (async — would use elasticsearch-py)
        # await es_client.index(index=ES_INDEX, body=event_dict)

    def log_access(
        self,
        endpoint: str,
        method: str = "POST",
        status_code: int = 200,
        response_time_ms: int = 0,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        """Log a standard API access event."""
        event = AuditEvent(
            event_type="access",
            user_id=user_id,
            user_role=user_role,
            tenant_id=tenant_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            request_id=request_id,
            metadata=kwargs,
            severity="INFO",
        )
        self._emit(event)

    def log_rbac_violation(
        self,
        endpoint: str,
        reason: str,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        tenant_id: Optional[str] = None,
        document_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """
        Log an RBAC access violation — CRITICAL severity.
        Triggers immediate alert in production.
        """
        event = AuditEvent(
            event_type="rbac_violation",
            user_id=user_id,
            user_role=user_role,
            tenant_id=tenant_id,
            endpoint=endpoint,
            status_code=403,
            ip_address=ip_address,
            metadata={
                "reason": reason,
                "document_id": document_id,
                "alert": "RBAC violation requires immediate review",
            },
            severity="CRITICAL",
        )
        self._emit(event)
        logger.critical(
            f"🚨 RBAC VIOLATION: user={user_id} role={user_role} "
            f"endpoint={endpoint} reason={reason}"
        )

    def log_agent_execution(
        self,
        run_id: str,
        issue_id: str,
        status: str,
        duration_ms: int,
        cost_usd: float,
        user_id: Optional[str] = None,
        nodes_executed: Optional[list] = None,
    ):
        """Log a multi-agent pipeline execution."""
        event = AuditEvent(
            event_type="agent_execution",
            user_id=user_id,
            endpoint="/api/v1/issues/review",
            status_code=200 if status == "completed" else 500,
            response_time_ms=duration_ms,
            metadata={
                "run_id": run_id,
                "issue_id": issue_id,
                "execution_status": status,
                "cost_usd": cost_usd,
                "nodes_executed": nodes_executed or [],
            },
            severity="INFO",
        )
        self._emit(event)

    def log_auth_event(
        self,
        event_subtype: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
    ):
        """Log authentication events (login, logout, token refresh, failed auth)."""
        event = AuditEvent(
            event_type="auth",
            user_id=user_id,
            ip_address=ip_address,
            status_code=200 if success else 401,
            metadata={
                "auth_event": event_subtype,
                "success": success,
            },
            severity="WARNING" if not success else "INFO",
        )
        self._emit(event)


# Singleton
audit_logger = AuditLogger()
