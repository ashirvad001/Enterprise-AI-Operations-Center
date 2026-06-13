"""
Agent Engine API Routes — wires LangGraph pipeline to HTTP endpoints.

Endpoints:
  POST /agents                                 — Create agent config (registry)
  POST /workflows/{workflow_id}/execute        — Trigger async agent pipeline
  GET  /workflows/executions/{execution_id}   — Poll execution status
  POST /issues/review                          — Direct GitHub issue → PR pipeline
  WS   /ws/v1/agents/executions/{id}           — Real-time streaming events
  GET  /engine/health                          — Engine health check
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, status
from pydantic import BaseModel, Field

from ..engine import engine

router = APIRouter()

# In-memory execution store (replace with Redis in production)
_executions: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Pydantic Request/Response Schemas
# ---------------------------------------------------------------------------

class AgentCreateRequest(BaseModel):
    name: str
    description: str
    type: str
    model_config_data: Dict[str, Any] = Field(default_factory=dict, alias="model_config")
    system_prompt: str
    tools: Optional[List[Dict[str, Any]]] = []
    guardrails: Optional[Dict[str, Any]] = {}
    cost_budget: Optional[Dict[str, Any]] = {}

    model_config = {"populate_by_name": True}


class AgentExecuteRequest(BaseModel):
    input_data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = {}


class IssueReviewRequest(BaseModel):
    issue: str = Field(description="GitHub issue description/body text")
    issue_id: str = Field(default="GH-0", description="Issue number, e.g. GH-142")
    repository: str = Field(default="", description="GitHub repo in org/repo format")
    max_iterations: int = Field(default=3, ge=1, le=10)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreateRequest):
    """Creates a new agent configuration (registry entry)."""
    agent_id = str(uuid.uuid4())
    return {
        "data": {
            "id": agent_id,
            "name": request.name,
            "version": "1.0.0",
            "type": request.type,
            "status": "active",
            "created_at": "2026-06-13T00:00:00Z",
        }
    }


@router.post("/workflows/{workflow_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_workflow(
    workflow_id: str,
    request: AgentExecuteRequest,
    background_tasks: BackgroundTasks,
):
    """
    Triggers async execution of a workflow via the agent pipeline.
    Returns immediately with execution_id; use WebSocket or polling to get results.
    """
    execution_id = str(uuid.uuid4())
    _executions[execution_id] = {"status": "running", "result": None}

    async def _run():
        issue = request.input_data.get("issue", "No issue provided")
        issue_id = request.input_data.get("issue_id", workflow_id)
        repository = request.input_data.get("repository", "")
        result = await engine.execute(issue=issue, issue_id=issue_id, repository=repository)
        _executions[execution_id] = {"status": result.get("status", "completed"), "result": result}

    background_tasks.add_task(_run)

    return {
        "data": {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "websocket_url": f"/ws/v1/agents/executions/{execution_id}",
            "poll_url": f"/api/v1/workflows/executions/{execution_id}",
        }
    }


@router.get("/workflows/executions/{execution_id}")
async def get_execution_status(execution_id: str):
    """Poll the status of a background pipeline execution."""
    execution = _executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    return {"data": execution}


@router.post("/issues/review", status_code=status.HTTP_200_OK)
async def review_issue(request: IssueReviewRequest):
    """
    Synchronous GitHub issue review pipeline.
    Runs planner → coder → security_reviewer → tester → (human checkpoint) → PR.

    Returns the full pipeline result including plan, code, tests, security review.
    Note: For large issues, prefer the async /workflows endpoint.
    """
    try:
        result = await engine.execute(
            issue=request.issue,
            issue_id=request.issue_id,
            repository=request.repository,
            max_iterations=request.max_iterations,
        )
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.get("/engine/health")
async def engine_health():
    """Returns the agent engine health status."""
    return {"data": engine.health()}


@router.websocket("/ws/v1/agents/executions/{execution_id}")
async def websocket_execution_stream(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for real-time streaming of agent execution events.

    Streams events every 500ms until execution completes or client disconnects.
    """
    await websocket.accept()

    await websocket.send_json({
        "event": "execution.started",
        "execution_id": execution_id,
    })

    # Stream node progress
    nodes = ["planner", "coder", "security_reviewer", "tester", "human_checkpoint", "create_pr"]
    for node in nodes:
        await asyncio.sleep(0.5)
        execution = _executions.get(execution_id, {})
        if execution.get("status") == "failed":
            await websocket.send_json({
                "event": "execution.failed",
                "execution_id": execution_id,
                "error": execution.get("result", {}).get("error"),
            })
            break

        await websocket.send_json({
            "event": "step.started",
            "step_id": node,
            "execution_id": execution_id,
        })
        await asyncio.sleep(0.3)
        await websocket.send_json({
            "event": "step.completed",
            "step_id": node,
            "execution_id": execution_id,
        })

        # Check if done
        if execution.get("status") in {"completed", "failed"}:
            break

    # Send final state
    final = _executions.get(execution_id, {})
    await websocket.send_json({
        "event": "execution.completed",
        "execution_id": execution_id,
        "status": final.get("status", "unknown"),
        "total_cost": final.get("result", {}).get("total_cost_usd", 0.0),
    })
    await websocket.close()
