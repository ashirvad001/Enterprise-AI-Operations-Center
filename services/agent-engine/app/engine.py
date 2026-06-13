"""
EAIOC Agent Engine — LangGraph-based execution engine.

Replaces the previous MockLLMExecutor with a real LangGraph pipeline.
The engine manages pipeline compilation, execution, and result formatting.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional

from .agents.orchestrator import build_graph, FallbackOrchestrator

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Production agent execution engine wrapping the LangGraph compiled graph.

    Provides async execute() for API routes and maintains a compiled graph
    instance for reuse across requests (LangGraph graphs are thread-safe).
    """

    def __init__(self):
        self._graph = None
        self._init_error: Optional[str] = None
        self._build_graph()

    def _build_graph(self):
        """Build and compile the LangGraph pipeline on startup."""
        try:
            self._graph = build_graph()
            logger.info("AgentEngine: LangGraph pipeline ready")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"AgentEngine: Failed to build graph ({e}). Using fallback.")
            self._graph = FallbackOrchestrator()

    async def execute(
        self,
        issue: str,
        issue_id: str = "GH-0",
        repository: str = "",
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Executes the full agent pipeline for a given GitHub issue.

        Args:
            issue: The raw GitHub issue description/body text.
            issue_id: Issue identifier, e.g. "GH-142".
            repository: GitHub repo in "org/repo" format.
            max_iterations: Max security-retry iterations (default 3).

        Returns:
            Final AgentState dict with plan, code, security_review, tests, pr, metrics.
        """
        run_id = str(uuid.uuid4())
        start_ms = int(time.time() * 1000)

        logger.info(f"[AgentEngine] Starting run {run_id} for issue {issue_id}")

        initial_state = {
            "run_id": run_id,
            "issue": issue,
            "issue_id": issue_id,
            "repository": repository,
            "plan": None,
            "code": None,
            "security_review": None,
            "tests": None,
            "pr": None,
            "iteration": 0,
            "max_iterations": max_iterations,
            "human_approved": False,
            "error": None,
            "status": "running",
            "messages": [],
            "total_tokens_used": 0,
            "total_cost_usd": 0.0,
            "latency_ms": {},
        }

        config = {"configurable": {"thread_id": run_id}}

        try:
            # LangGraph compiled graph or FallbackOrchestrator — both support ainvoke
            if hasattr(self._graph, "ainvoke"):
                result = await self._graph.ainvoke(initial_state, config)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._graph.invoke, initial_state, config
                )
        except Exception as e:
            logger.error(f"[AgentEngine] Pipeline execution failed: {e}")
            result = {**initial_state, "status": "failed", "error": str(e)}

        total_ms = int(time.time() * 1000) - start_ms
        logger.info(
            f"[AgentEngine] Run {run_id} completed in {total_ms}ms. "
            f"Status: {result.get('status', 'unknown')}"
        )

        # Serialize Pydantic models to dicts for JSON response
        return _serialize_state(result)

    def health(self) -> Dict[str, Any]:
        """Returns engine health status."""
        return {
            "status": "healthy" if self._init_error is None else "degraded",
            "graph_type": type(self._graph).__name__,
            "init_error": self._init_error,
        }


def _serialize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Converts Pydantic models in state to plain dicts for JSON serialization."""
    result = dict(state)
    for key in ("plan", "code", "security_review", "tests", "pr"):
        val = result.get(key)
        if val is not None and hasattr(val, "model_dump"):
            result[key] = val.model_dump()
    return result


# Singleton instance (shared across FastAPI routes)
engine = AgentEngine()
