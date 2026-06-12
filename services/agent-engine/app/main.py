from fastapi import FastAPI
from eaioc_core.app import create_app
from eaioc_core.exceptions import api_exception_handler, APIException
from .routes import agents

app = create_app(
    title="Agent Orchestration Engine",
    description="EAIOC execution engine for LLM-driven multi-agent workflows",
    version="0.1.0",
)

app.add_exception_handler(APIException, api_exception_handler)

app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
