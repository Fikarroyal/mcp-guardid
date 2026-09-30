"""
ORM entities. Uses SQLite-compatible types (String UUID, JSON) by default.

For production PostgreSQL + pgvector, swap:
  - JSON embedding columns -> `from pgvector.sqlalchemy import Vector`
  - String(36) PKs         -> `sqlalchemy.dialects.postgresql.UUID(as_uuid=True)`
This is a drop-in change confined to this file; no service-layer code depends
on the physical column type (see app/rag/vector_store.py abstraction).
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    max_risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    is_elevated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    role_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class McpTool(Base):
    __tablename__ = "mcp_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    required_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    semantic_embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, default=100.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ToolEmbedding(Base):
    """Versioned embeddings, decoupled from the tool row (production: pgvector column)."""

    __tablename__ = "tool_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("mcp_tools.id"), index=True)
    model_version: Mapped[str] = mapped_column(String(64), default="tfidf-svd-v1")
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), index=True, default="MEDIUM")
    service: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    root_cause: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    related_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    execution_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    target: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="success")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(32), default="mcp")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    tool_name: Mapped[str] = mapped_column(String(128))
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    requested_by_role: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(255), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(16))
    required_role: Mapped[str] = mapped_column(String(64))
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), index=True, default="PENDING")
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    user_role: Mapped[str] = mapped_column(String(64), index=True)
    user_query: Mapped[str] = mapped_column(Text)
    detected_intent: Mapped[str] = mapped_column(String(128), index=True)
    candidate_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    selected_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    permission_result: Mapped[str] = mapped_column(String(32))
    approval_status: Mapped[str] = mapped_column(String(32), default="NOT_REQUIRED")
    execution_result: Mapped[dict] = mapped_column(JSON, default=dict)
    execution_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    verification_result: Mapped[dict] = mapped_column(JSON, default=dict)
    final_response: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    dataset_name: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    description: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ApiKey(Base):
    """Service-account access tokens for programmatic/automation use,
    distinct from human JWT logins. Bound to a synthetic `User` row so RBAC,
    risk checks, and audit logging all treat a key exactly like any other
    authenticated identity -- no separate authorization code path to drift
    out of sync."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)  # safe to display, e.g. "gid_AbCd1234..."
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # sha256 hex digest
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
