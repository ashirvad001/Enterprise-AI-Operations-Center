import uuid
from sqlalchemy import String, ForeignKey, Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import List, Optional, Any
import datetime

from ..base import Base, TimestampMixin

# --- EDGE SCHEMA ---
class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    __table_args__ = {"schema": "edge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mac_address: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    hardware_specs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_heartbeat_at: Mapped[Optional[datetime.datetime]] = mapped_column()

    deployments: Mapped[List["Deployment"]] = relationship(back_populates="device", cascade="all, delete-orphan")

class Deployment(Base, TimestampMixin):
    __tablename__ = "deployments"
    __table_args__ = {"schema": "edge"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("edge.devices.id", ondelete="CASCADE"), nullable=False)
    # Could reference agent.id or a ModelRegistry ID. We'll use a generic string for now.
    workload_id: Mapped[str] = mapped_column(String(255), nullable=False) 
    workload_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "model", "agent"
    
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    
    device: Mapped["Device"] = relationship(back_populates="deployments")


# --- MLOPS SCHEMA ---
class ModelRegistry(Base, TimestampMixin):
    __tablename__ = "model_registry"
    __table_args__ = {"schema": "mlops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    framework: Mapped[str] = mapped_column(String(50)) # e.g., pytorch, onnx, gguf
    s3_path: Mapped[str] = mapped_column(String(1000))
    
    metrics: Mapped[List["ModelMetric"]] = relationship(back_populates="model", cascade="all, delete-orphan")

class ModelMetric(Base, TimestampMixin):
    __tablename__ = "model_metrics"
    __table_args__ = {"schema": "mlops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mlops.model_registry.id", ondelete="CASCADE"), nullable=False)
    
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False) # latency_ms, tokens_per_sec, drift_score
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    
    model: Mapped["ModelRegistry"] = relationship(back_populates="metrics")
