from fastapi import APIRouter, status, BackgroundTasks, WebSocket
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid

from ..engine import MockLLMExecutor

router = APIRouter()
executor = MockLLMExecutor()

# --- Pydantic Schemas ---
class AgentCreateRequest(BaseModel):
    name: str
    description: str
    type: str
    model_config: Dict[str, Any]
    system_prompt: str
    tools: Optional[List[Dict[str, Any]]] = []
    guardrails: Optional[Dict[str, Any]] = {}
    cost_budget: Optional[Dict[str, Any]] = {}

class AgentExecuteRequest(BaseModel):
    input_data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = {}

# --- Endpoints ---
@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreateRequest):
    """
    Creates a new agent configuration.
    """
    agent_id = str(uuid.uuid4())
    return {
        "data": {
            "id": agent_id,
            "name": request.name,
            "version": "1.0.0",
            "type": request.type,
            "status": "active",
            "created_at": "2026-06-13T00:00:00Z"
        }
    }

@router.post("/workflows/{workflow_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_workflow(workflow_id: str, request: AgentExecuteRequest, background_tasks: BackgroundTasks):
    """
    Triggers an async execution of a workflow.
    """
    execution_id = str(uuid.uuid4())
    
    # In reality, we'd add the execution to a Redis queue or fire a background task
    # background_tasks.add_task(executor.execute_agent, {}, request.input_data)
    
    return {
        "data": {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "websocket_url": f"/ws/v1/agents/executions/{execution_id}",
            "created_at": "2026-06-13T00:00:00Z"
        }
    }

@router.websocket("/ws/v1/agents/executions/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for streaming execution events in real-time.
    """
    await websocket.accept()
    # Mocking stream
    await websocket.send_json({"event": "execution.started", "execution_id": execution_id})
    await websocket.send_json({"event": "step.started", "step_id": "research"})
    await websocket.send_json({"event": "step.llm_chunk", "content": "Mocking "})
    await websocket.send_json({"event": "step.llm_chunk", "content": "stream..."})
    await websocket.send_json({"event": "step.completed", "step_id": "research", "duration_ms": 2000})
    await websocket.send_json({"event": "execution.completed", "total_cost": 0.002})
    await websocket.close()
