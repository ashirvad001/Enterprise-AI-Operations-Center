"""
Enterprise AI Operations Center - Events Library
"""

from typing import Any, Dict
from pydantic import BaseModel
import datetime

__version__ = "0.1.0"

class BaseEvent(BaseModel):
    """Base class for all internal events."""
    event_id: str
    event_type: str
    timestamp: datetime.datetime
    tenant_id: str
    payload: Dict[str, Any]

class ExecutionStatusEvent(BaseEvent):
    """Event emitted when a workflow execution changes status."""
    execution_id: str
    status: str
    
class AgentStepEvent(BaseEvent):
    """Event emitted when an agent completes a step or streams a chunk."""
    execution_id: str
    step_id: str
    agent_id: str
    content: str
