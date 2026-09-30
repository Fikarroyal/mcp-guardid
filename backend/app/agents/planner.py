"""
Planner. Never executes tools itself, and is HARD-restricted to the tool
names it was given by the Tool Retrieval Engine -- even if the underlying
LLM hallucinates a different tool name, this layer strips it out before the
plan is used downstream (Section 9: "Planner TIDAK boleh membuat nama tool
baru").
"""
from __future__ import annotations

from app.agents.llm_provider import get_llm_provider
from app.routing.scoring import ScoreBreakdown


async def build_plan(*, query: str, candidates: list[ScoreBreakdown], role: str, intent_hint: str) -> dict:
    provider = get_llm_provider()
    candidate_dicts = [
        {"name": c.tool_name, "risk_level": _risk_of(c), "permission_result": c.permission_result,
         "final_score": c.final_score}
        for c in candidates
    ]
    plan = await provider.generate_plan(query=query, candidates=candidate_dicts, role=role, intent_hint=intent_hint)

    allowed_names = {c.tool_name for c in candidates}
    plan["candidate_tools"] = [t for t in plan.get("candidate_tools", []) if t in allowed_names]
    return plan


def _risk_of(candidate: ScoreBreakdown) -> str:
    # ScoreBreakdown doesn't carry risk_level directly (it's derived from risk_score);
    # callers pass the richer tool objects in build_plan's caller when needed. Here we
    # reconstruct a label purely for LLM context, not for enforcement.
    if candidate.risk_score >= 0.8:
        return "CRITICAL"
    if candidate.risk_score >= 0.45:
        return "HIGH"
    if candidate.risk_score >= 0.15:
        return "MEDIUM"
    return "LOW"
