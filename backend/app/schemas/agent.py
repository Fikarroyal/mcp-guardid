from pydantic import BaseModel


class AgentQueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class EvidenceItem(BaseModel):
    tool_name: str
    execution_id: str
    timestamp: str
    target: str
    status: str
    latency_ms: float
    result: dict
    source: str = "mcp"


class ToolRoutingCandidate(BaseModel):
    name: str
    similarity: float
    risk: str
    permission: str
    final_score: float


class PlanOut(BaseModel):
    intent: str
    objective: str
    required_information: list[str]
    candidate_tools: list[str]
    reasoning_summary: str
    risk_level: str
    requires_approval: bool


class VerificationOut(BaseModel):
    verified: bool
    confidence: float
    issues: list[str]
    required_action: str


class AgentQueryResponse(BaseModel):
    request_id: str
    intent: str
    risk_level: str
    permission_result: str
    routing_candidates: list[ToolRoutingCandidate]
    selected_tools: list[str]
    executions: list[EvidenceItem]
    evidence: list[EvidenceItem]
    plan: PlanOut
    answer: str
    verification: VerificationOut
    audit_id: str
    pending_approval_id: str | None = None
    security_findings: list[str] = []
    total_latency_ms: float = 0.0
