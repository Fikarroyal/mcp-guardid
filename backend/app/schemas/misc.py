from datetime import datetime

from pydantic import BaseModel


class ApprovalOut(BaseModel):
    id: str
    request_id: str
    tool_name: str
    requested_by_role: str
    target: str
    reason: str
    risk_level: str
    required_role: str
    status: str
    requested_at: datetime
    decided_at: datetime | None = None

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    decision_note: str | None = None


class AuditLogOut(BaseModel):
    id: str
    request_id: str
    user_id: str
    user_role: str
    user_query: str
    detected_intent: str
    candidate_tools: list[str]
    selected_tools: list[str]
    risk_level: str
    permission_result: str
    approval_status: str
    execution_latency_ms: float
    final_response: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentOut(BaseModel):
    id: str
    code: str
    title: str
    severity: str
    service: str
    status: str
    root_cause: str
    detected_at: datetime
    assigned_to: str | None = None

    class Config:
        from_attributes = True


class RagSearchRequest(BaseModel):
    query: str
    category: str | None = None
    top_k: int = 5


class RagSearchResult(BaseModel):
    document_id: str
    title: str
    category: str
    similarity: float
    snippet: str


class EvaluationRunRequest(BaseModel):
    dataset_name: str = "enterprise_tool_routing_v1"
    sample_size: int = 300


class EvaluationRunOut(BaseModel):
    id: str
    dataset_name: str
    model_version: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    metrics: dict[str, float] = {}


class SecurityEventOut(BaseModel):
    id: str
    request_id: str
    event_type: str
    severity: str
    description: str
    blocked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SystemHealthOut(BaseModel):
    api: str
    mcp_gateway: str
    database: str
    vector_store: str
    llm_service: str
    redis: str
    environment: str
