"""
Conversation Logger — asynchronously logs multi-turn chat and voice interactions
to the datastore for analytics and CSAT tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConversationTurn(BaseModel):
    turn_id: int
    user_message: str
    agent_response: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = {}
    latency_ms: int
    timestamp: float


class ConversationSession(BaseModel):
    session_id: str
    user_id: str
    tenant_id: str
    channel: str  # "voice", "chat", "agent_engine"
    turns: List[ConversationTurn] = []
    csat_score: Optional[float] = None
    escalated: bool = False
    started_at: float
    updated_at: float


class ConversationLogger:
    """
    Asynchronous logger for tracking conversation history.
    In production, this flushes to PostgreSQL or a specialized analytics DB.
    """

    def __init__(self, flush_interval: int = 5):
        self._flush_interval = flush_interval
        self._buffer: Dict[str, ConversationSession] = {}
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("ConversationLogger started")

    async def stop(self):
        """Stop the background flush task and flush remaining buffer."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            await self._flush_buffer()
            logger.info("ConversationLogger stopped")

    async def log_turn(
        self,
        session_id: str,
        user_message: str,
        agent_response: str,
        user_id: str = "anonymous",
        tenant_id: str = "default",
        channel: str = "chat",
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        latency_ms: int = 0,
        escalated: bool = False,
    ):
        """Log a single turn of a conversation."""
        now = time.time()
        
        async with self._lock:
            if session_id not in self._buffer:
                self._buffer[session_id] = ConversationSession(
                    session_id=session_id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    channel=channel,
                    started_at=now,
                    updated_at=now,
                )
            
            session = self._buffer[session_id]
            session.updated_at = now
            if escalated:
                session.escalated = True
                
            turn = ConversationTurn(
                turn_id=len(session.turns) + 1,
                user_message=user_message,
                agent_response=agent_response,
                intent=intent,
                entities=entities or {},
                latency_ms=latency_ms,
                timestamp=now,
            )
            session.turns.append(turn)

    async def _flush_loop(self):
        """Background task to periodically flush the buffer."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush the current buffer to storage."""
        async with self._lock:
            if not self._buffer:
                return
            
            # In a real system, this would bulk insert into Postgres/Elasticsearch
            sessions_to_flush = list(self._buffer.values())
            self._buffer.clear()
            
        logger.info(f"Flushed {len(sessions_to_flush)} conversation sessions to storage")
        
        # Simulate DB insert
        await asyncio.sleep(0.05)


# Global instance for the service
conversation_logger = ConversationLogger()
