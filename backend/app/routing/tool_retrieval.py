"""
Tool Retrieval Engine.

Pipeline (Section 7):
    User Query -> Query Embedding -> Vector Search -> Top-K candidates
    -> Metadata filtering -> Permission filtering -> Risk filtering
    -> Tool reranking (FinalScore) -> Final tools

This is the ONLY component allowed to narrow the full tool catalog down to a
small candidate list. The Planner (app/agents/planner.py) never sees the
full registry -- only what this engine returns.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent import IntentResult
from app.core.config import get_settings
from app.core.enums import PermissionResult, RiskLevel
from app.models.entities import Incident, McpTool
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import get_vector_store
from app.routing.scoring import ScoreBreakdown, compute_final_score
from app.security.policy_engine import get_policy_engine


async def retrieve_tools(
    db: AsyncSession,
    *,
    query: str,
    role_name: str,
    intent_result: IntentResult,
    target_hint: str = "",
    top_k: int | None = None,
) -> list[ScoreBreakdown]:
    settings = get_settings()
    top_k = top_k or settings.TOOL_RETRIEVAL_TOP_K

    provider = get_embedding_provider()
    vector_store = get_vector_store()
    query_vector = provider.embed(query)

    # 1) Vector search over a generous candidate pool (metadata-filtered to enabled tools only).
    raw_results = vector_store.search(
        namespace="mcp_tools", query_vector=query_vector, top_k=max(top_k * 4, 15),
        metadata_filter={"enabled": True},
    )

    # If a high-signal rule forced a specific tool (e.g. "restart database"),
    # make sure it is present in the candidate set even if its embedding
    # similarity alone wouldn't have surfaced it in the top results.
    candidate_names = {r.id for r in raw_results}
    if intent_result.forced_tool and intent_result.forced_tool not in candidate_names:
        raw_results.append(_synthetic_result(intent_result.forced_tool))

    tools_result = await db.execute(select(McpTool).where(McpTool.enabled.is_(True)))
    tools_by_name = {t.name: t for t in tools_result.scalars().all()}

    active_incidents = await db.execute(select(Incident).where(Incident.status == "OPEN"))
    active_services = {i.service for i in active_incidents.scalars().all()}

    policy_engine = get_policy_engine()
    scored: list[ScoreBreakdown] = []
    seen: set[str] = set()
    for r in raw_results:
        tool = tools_by_name.get(r.id)
        if tool is None or tool.name in seen:
            continue
        seen.add(tool.name)

        decision = policy_engine.evaluate(
            role_name=role_name,
            tool_name=tool.name,
            tool_category=tool.category,
            tool_risk_level=tool.risk_level,
            tool_required_roles=tool.required_roles or [],
        )

        breakdown = compute_final_score(
            tool_name=tool.name,
            semantic_score=r.score,
            is_canonical_for_intent=tool.name in intent_result.canonical_tools,
            permission_result=decision.result,
            tool_category=tool.category,
            risk_level=RiskLevel(tool.risk_level),
            historical_success_rate=tool.success_rate,
            active_incident_services=active_services,
            target_hint=target_hint,
        )
        scored.append(breakdown)

    scored.sort(key=lambda s: s.final_score, reverse=True)
    return scored[:top_k]


def _synthetic_result(tool_name: str):
    from app.rag.vector_store import VectorSearchResult

    return VectorSearchResult(id=tool_name, score=0.9, metadata={"name": tool_name})
