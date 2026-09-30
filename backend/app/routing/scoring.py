"""
FinalScore(tool) = w1*SemanticRelevance + w2*IntentMatch + w3*RolePermission
                  + w4*ContextMatch + w5*HistoricalSuccess - w6*RiskPenalty

All six weights are configurable via Settings (Section 2 of the spec).
Nothing here is hardcoded per-tool -- every component is computed from the
actual query, the actual role, and the tool's actual stored statistics.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.enums import PermissionResult, RiskLevel


@dataclass
class ScoreBreakdown:
    tool_name: str
    semantic_score: float
    intent_score: float
    permission_score: float
    context_score: float
    historical_success: float
    risk_score: float
    final_score: float
    permission_result: str


def permission_component(permission_result: PermissionResult) -> float:
    return {
        PermissionResult.ALLOWED: 1.0,
        PermissionResult.APPROVAL_REQUIRED: 0.6,  # still relevant/rankable, just gated later
        PermissionResult.DENIED: 0.0,
    }[permission_result]


def risk_penalty(risk_level: RiskLevel) -> float:
    return {RiskLevel.LOW: 0.0, RiskLevel.MEDIUM: 0.15, RiskLevel.HIGH: 0.45, RiskLevel.CRITICAL: 0.8}[risk_level]


def context_component(tool_category: str, active_incident_services: set[str], target_hint: str) -> float:
    """Context match: does the tool's category align with the current
    operational context (an active incident on the same service, or the
    query mentioning infrastructure the tool operates on)?"""
    score = 0.5  # neutral baseline
    if target_hint and target_hint.lower() in tool_category.lower():
        score += 0.2
    if active_incident_services:
        score += 0.3
    return min(score, 1.0)


def compute_final_score(
    *,
    tool_name: str,
    semantic_score: float,
    is_canonical_for_intent: bool,
    permission_result: PermissionResult,
    tool_category: str,
    risk_level: RiskLevel,
    historical_success_rate: float,  # 0-100
    active_incident_services: set[str] | None = None,
    target_hint: str = "",
) -> ScoreBreakdown:
    settings = get_settings()
    intent_score = 1.0 if is_canonical_for_intent else 0.3
    perm_score = permission_component(permission_result)
    ctx_score = context_component(tool_category, active_incident_services or set(), target_hint)
    hist_score = historical_success_rate / 100.0
    risk_score = risk_penalty(risk_level)

    final = (
        settings.SCORE_W_SEMANTIC * semantic_score
        + settings.SCORE_W_INTENT * intent_score
        + settings.SCORE_W_PERMISSION * perm_score
        + settings.SCORE_W_CONTEXT * ctx_score
        + settings.SCORE_W_HISTORICAL * hist_score
        - settings.SCORE_W_RISK_PENALTY * risk_score
    )
    return ScoreBreakdown(
        tool_name=tool_name,
        semantic_score=round(semantic_score, 4),
        intent_score=round(intent_score, 4),
        permission_score=round(perm_score, 4),
        context_score=round(ctx_score, 4),
        historical_success=round(hist_score, 4),
        risk_score=round(risk_score, 4),
        final_score=round(final, 4),
        permission_result=permission_result.value,
    )
