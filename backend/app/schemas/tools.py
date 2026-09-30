from datetime import datetime

from pydantic import BaseModel


class ToolOut(BaseModel):
    id: str
    name: str
    description: str
    category: str
    risk_level: str
    requires_approval: bool
    required_roles: list[str]
    input_schema: dict
    output_schema: dict
    enabled: bool
    version: str
    success_rate: float
    avg_latency_ms: float
    execution_count: int
    last_used: datetime | None = None

    class Config:
        from_attributes = True


class ToolSearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class ToolCandidate(BaseModel):
    name: str
    category: str
    risk_level: str
    semantic_score: float
    intent_score: float
    permission_score: float
    context_score: float
    historical_success: float
    risk_score: float
    final_score: float
    permission_result: str


class ToolSearchResponse(BaseModel):
    query: str
    detected_intent: str
    candidates: list[ToolCandidate]


class ToolExecuteRequest(BaseModel):
    input_data: dict = {}
    target: str = ""
    reason: str = ""
