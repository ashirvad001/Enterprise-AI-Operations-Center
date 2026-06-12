import uuid
from sqlalchemy import String, Boolean, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import List, Optional, Any

from ..base import Base, TimestampMixin

class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = {"schema": "agent"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'research', 'conversational'
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    
    model_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    system_prompt: Mapped[str] = mapped_column(String, nullable=False)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    guardrails: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    cost_budget: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id"), nullable=False)


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"
    __table_args__ = {"schema": "agent"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dag_definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    executions: Mapped[List["Execution"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")


class Execution(Base, TimestampMixin):
    __tablename__ = "executions"
    __table_args__ = {"schema": "agent"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent.workflows.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False) # running, completed, failed
    
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    steps: Mapped[List["Step"]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class Step(Base, TimestampMixin):
    __tablename__ = "steps"
    __table_args__ = {"schema": "agent"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent.executions.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent.agents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    
    step_input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)
    step_output: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    execution: Mapped["Execution"] = relationship(back_populates="steps")
