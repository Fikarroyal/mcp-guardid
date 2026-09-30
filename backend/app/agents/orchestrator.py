"""
Agent Orchestrator: the full pipeline described in Section 1 of the spec.

User Request -> Intent Understanding -> Semantic Tool Retrieval -> Context &
Role Analysis -> Risk Assessment -> Permission Check -> Tool Ranking ->
MCP Tool Selection -> Approval Gate (if needed) -> MCP Tool Execution ->
Evidence Collection -> Verifier -> LLM Reasoning -> Final Answer -> Audit Trail
"""
from __future__ import annotations

import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.entity_extraction import build_tool_input, extract_target
from app.agents.intent import classify_intent
from app.agents.planner import build_plan
from app.agents.verifier import verify
from app.core.enums import ApprovalStatus, PermissionResult
from app.mcp import gateway
from app.models.entities import McpTool, User
from app.routing.tool_retrieval import retrieve_tools
from app.security.injection_defense import is_blocked, scan_user_input
from app.services import approval_service, audit_service


async def handle_query(db: AsyncSession, *, user: User, query: str, session_id: str | None) -> dict:
    started = time.time()
    request_id = str(uuid.uuid4())

    # ---- 0. Input-level prompt-injection / policy-override screening -----
    input_findings = scan_user_input(query)
    if is_blocked(input_findings):
        for f in input_findings:
            await audit_service.write_security_event(
                db, request_id=request_id, event_type=f.finding_type, severity=f.severity.value,
                description=f.description, user_id=user.id, blocked=True,
            )
        await audit_service.write_audit_log(
            db, request_id=request_id, user_id=user.id, user_role=user.role_name, user_query=query,
            detected_intent="blocked_security_policy", candidate_tools=[], selected_tools=[],
            risk_level="CRITICAL", permission_result=PermissionResult.DENIED.value,
            approval_status=ApprovalStatus.NOT_REQUIRED.value, execution_result={},
            execution_latency_ms=0.0, verification_result={"verified": False, "issues": [f.finding_type for f in input_findings]},
            final_response="BLOCKED: security policy violation detected in user request.", status="BLOCKED",
        )
        await db.commit()
        return {
            "request_id": request_id, "intent": "blocked_security_policy", "risk_level": "CRITICAL",
            "permission_result": PermissionResult.DENIED.value, "routing_candidates": [], "selected_tools": [],
            "executions": [], "evidence": [],
            "plan": {"intent": "blocked_security_policy", "objective": "", "required_information": [],
                     "candidate_tools": [], "reasoning_summary": "Request blocked before planning.",
                     "risk_level": "CRITICAL", "requires_approval": False},
            "answer": "Permintaan diblokir: terdeteksi upaya melewati kebijakan keamanan (prompt injection / policy override).",
            "verification": {"verified": False, "confidence": 0.0,
                              "issues": [f.finding_type for f in input_findings], "required_action": "block"},
            "audit_id": request_id, "pending_approval_id": None,
            "security_findings": [f.finding_type for f in input_findings],
            "total_latency_ms": round((time.time() - started) * 1000, 2),
        }

    # ---- 1. Intent Understanding -----------------------------------------
    intent_result = classify_intent(query)

    # ---- 1b. Explicit high-risk/critical action request ------------------
    # These MUST surface a clear DENIED / APPROVAL_REQUIRED decision for the
    # exact requested tool -- never silently substitute unrelated diagnostic
    # tools instead (Section 3 of the spec).
    if intent_result.forced_tool:
        return await _handle_forced_action(
            db, user=user, query=query, request_id=request_id, intent_result=intent_result, started=started,
        )

    # ---- 2. Semantic Tool Retrieval (+ Risk/Permission scoring) ----------
    candidates = await retrieve_tools(db, query=query, role_name=user.role_name, intent_result=intent_result)

    # ---- 3. Planner (LLM reasoning, restricted to retrieved candidates) --
    plan = await build_plan(query=query, candidates=candidates, role=user.role_name, intent_hint=intent_result.intent)

    overall_permission = _aggregate_permission(candidates, plan["candidate_tools"])

    # ---- 4. Context & Role Analysis (target extraction) ------------------
    target_ctx = extract_target(query)

    all_candidate_names = list({c.tool_name for c in candidates} | set(plan["candidate_tools"]))
    tools_result = await db.execute(select(McpTool).where(McpTool.name.in_(all_candidate_names)))
    tools_by_name = {t.name: t for t in tools_result.scalars().all()}
    candidates_by_name = {c.tool_name: c for c in candidates}

    executions: list[dict] = []
    pending_approval_id: str | None = None
    approval_status = ApprovalStatus.NOT_REQUIRED.value

    for tool_name in plan["candidate_tools"]:
        tool = tools_by_name.get(tool_name)
        candidate = candidates_by_name.get(tool_name)
        if tool is None or candidate is None:
            continue

        if candidate.permission_result == PermissionResult.DENIED.value:
            continue

        if candidate.permission_result == PermissionResult.APPROVAL_REQUIRED.value:
            already_approved = await approval_service.is_approved(db, request_id=request_id, tool_name=tool_name)
            if not already_approved:
                pending_input_data = build_tool_input(tool_name, tool.input_schema, target_ctx, query)
                approval = await approval_service.create_approval(
                    db, request_id=request_id, tool_name=tool_name, user=user,
                    target=target_ctx.get("hostname", ""), reason=f"Requested via query: '{query}'",
                    risk_level=tool.risk_level, required_role=(tool.required_roles or ["Enterprise Administrator"])[0],
                    input_data=pending_input_data,
                )
                pending_approval_id = approval.id
                approval_status = ApprovalStatus.PENDING.value
                continue  # HIGH/CRITICAL tools never execute without a real Approval record

        input_data = build_tool_input(tool_name, tool.input_schema, target_ctx, query)
        try:
            evidence = await gateway.execute_tool(
                db, tool=tool, role_name=user.role_name, input_data=input_data,
                target=target_ctx.get("hostname", ""), request_id=request_id,
                approval_confirmed=(candidate.permission_result == PermissionResult.ALLOWED.value),
            )
            executions.append(evidence)
        except (gateway.PermissionDeniedError, gateway.ApprovalRequiredError, gateway.InputValidationError):
            continue

    # ---- 5. Independent Verifier ------------------------------------------
    verification = await verify(plan=plan, evidence=executions, permission_result=overall_permission)

    # ---- 6. Final Answer (evidence-grounded) ------------------------------
    from app.agents.llm_provider import get_llm_provider

    provider = get_llm_provider()
    answer = await provider.generate_answer(query=query, evidence=executions, verification=verification)

    total_latency_ms = round((time.time() - started) * 1000, 2)

    # ---- 7. Audit Trail ----------------------------------------------------
    audit_log = await audit_service.write_audit_log(
        db, request_id=request_id, user_id=user.id, user_role=user.role_name, user_query=query,
        detected_intent=intent_result.intent, candidate_tools=[c.tool_name for c in candidates],
        selected_tools=plan["candidate_tools"], risk_level=plan["risk_level"], permission_result=overall_permission,
        approval_status=approval_status, execution_result={"executions": executions},
        execution_latency_ms=total_latency_ms, verification_result=verification, final_response=answer,
        status="PENDING_APPROVAL" if pending_approval_id else ("BLOCKED" if verification["required_action"] == "block" else "COMPLETED"),
    )
    await db.commit()

    routing_candidates = [
        {"name": c.tool_name, "similarity": c.semantic_score, "risk": _tool_risk(tools_by_name, candidates_by_name, c.tool_name),
         "permission": c.permission_result, "final_score": c.final_score}
        for c in candidates
    ]

    return {
        "request_id": request_id, "intent": intent_result.intent, "risk_level": plan["risk_level"],
        "permission_result": overall_permission, "routing_candidates": routing_candidates,
        "selected_tools": plan["candidate_tools"], "executions": executions, "evidence": executions,
        "plan": plan, "answer": answer, "verification": verification, "audit_id": audit_log.id,
        "pending_approval_id": pending_approval_id, "security_findings": [], "total_latency_ms": total_latency_ms,
    }


def _aggregate_permission(candidates, selected_names: list[str]) -> str:
    selected = [c for c in candidates if c.tool_name in selected_names]
    if any(c.permission_result == PermissionResult.APPROVAL_REQUIRED.value for c in selected):
        return PermissionResult.APPROVAL_REQUIRED.value
    if selected and all(c.permission_result == PermissionResult.ALLOWED.value for c in selected):
        return PermissionResult.ALLOWED.value
    if not selected:
        return PermissionResult.DENIED.value
    return PermissionResult.ALLOWED.value


def _tool_risk(tools_by_name, candidates_by_name, tool_name: str) -> str:
    tool = tools_by_name.get(tool_name)
    return tool.risk_level if tool else "UNKNOWN"


async def _handle_forced_action(
    db: AsyncSession, *, user: User, query: str, request_id: str, intent_result, started: float
) -> dict:
    """Explicit single-action path for HIGH/CRITICAL requests (restart, delete,
    shutdown, modify firewall/config, clear cache). Always surfaces a clear
    ALLOWED / DENIED / APPROVAL_REQUIRED decision for the exact tool the user
    asked for -- never substitutes a different tool silently."""
    from app.security.policy_engine import get_policy_engine

    tool_name = intent_result.forced_tool
    result = await db.execute(select(McpTool).where(McpTool.name == tool_name))
    tool = result.scalar_one_or_none()

    target_ctx = extract_target(query)
    routing_candidates = [{
        "name": tool_name, "similarity": 1.0,
        "risk": tool.risk_level if tool else intent_result.nominal_risk.value,
        "permission": "UNKNOWN", "final_score": 1.0,
    }]

    if tool is None:
        answer = f"Tool '{tool_name}' tidak ditemukan pada Tool Registry."
        verification = {"verified": False, "confidence": 0.0, "issues": ["tool_not_found"], "required_action": "block"}
        audit_log = await audit_service.write_audit_log(
            db, request_id=request_id, user_id=user.id, user_role=user.role_name, user_query=query,
            detected_intent=intent_result.intent, candidate_tools=[tool_name], selected_tools=[],
            risk_level=intent_result.nominal_risk.value, permission_result=PermissionResult.DENIED.value,
            approval_status=ApprovalStatus.NOT_REQUIRED.value, execution_result={}, execution_latency_ms=0.0,
            verification_result=verification, final_response=answer, status="BLOCKED",
        )
        await db.commit()
        return {
            "request_id": request_id, "intent": intent_result.intent, "risk_level": intent_result.nominal_risk.value,
            "permission_result": PermissionResult.DENIED.value, "routing_candidates": routing_candidates,
            "selected_tools": [], "executions": [], "evidence": [],
            "plan": {"intent": intent_result.intent, "objective": "", "required_information": [],
                     "candidate_tools": [], "reasoning_summary": "Tool not found.",
                     "risk_level": intent_result.nominal_risk.value, "requires_approval": False},
            "answer": answer, "verification": verification, "audit_id": audit_log.id, "pending_approval_id": None,
            "security_findings": [], "total_latency_ms": round((time.time() - started) * 1000, 2),
        }

    policy_engine = get_policy_engine()
    decision = policy_engine.evaluate(
        role_name=user.role_name, tool_name=tool.name, tool_category=tool.category,
        tool_risk_level=tool.risk_level, tool_required_roles=tool.required_roles or [],
    )
    routing_candidates[0]["permission"] = decision.result.value

    plan = {
        "intent": intent_result.intent,
        "objective": f"Execute explicitly requested high-risk action: {tool.name}",
        "required_information": [],
        "candidate_tools": [tool.name],
        "reasoning_summary": (
            "Explicit high-risk action detected from user request; routed directly to the "
            "named tool and evaluated strictly against RBAC and the risk/approval policy."
        ),
        "risk_level": tool.risk_level,
        "requires_approval": tool.requires_approval,
    }

    executions: list[dict] = []
    pending_approval_id: str | None = None

    if decision.result == PermissionResult.DENIED:
        required_role = (tool.required_roles or ["Enterprise Administrator"])[0]
        answer = (
            f"HIGH RISK ACTION DITOLAK.\nTool: {tool.name}\nTarget: {target_ctx.get('hostname','')}\n"
            f"Risk: {tool.risk_level}\nRole Anda: {user.role_name}\nRole yang dibutuhkan: {required_role}\n"
            f"Alasan: {decision.reason}\nAksi tidak dijalankan."
        )
        verification = {"verified": False, "confidence": 0.0, "issues": [decision.reason], "required_action": "block"}
        approval_status = ApprovalStatus.NOT_REQUIRED.value
        status = "BLOCKED"
    elif decision.result == PermissionResult.APPROVAL_REQUIRED:
        forced_input_data = build_tool_input(tool.name, tool.input_schema, target_ctx, query)
        approval = await approval_service.create_approval(
            db, request_id=request_id, tool_name=tool.name, user=user, target=target_ctx.get("hostname", ""),
            reason=f"Requested via query: '{query}'", risk_level=tool.risk_level,
            required_role=(tool.required_roles or ["Enterprise Administrator"])[0], input_data=forced_input_data,
        )
        pending_approval_id = approval.id
        answer = (
            f"{tool.risk_level} RISK ACTION, APPROVAL REQUIRED.\nTool: {tool.name}\n"
            f"Target: {target_ctx.get('hostname','')}\nRisk: {tool.risk_level}\nRequested by: {user.role_name}\n"
            f"Required role: {(tool.required_roles or ['Enterprise Administrator'])[0]}\n"
            f"Approval request ID: {approval.id}\nAksi TIDAK dijalankan sampai approval diberikan."
        )
        verification = {"verified": False, "confidence": 0.5, "issues": ["Approval required before execution."],
                         "required_action": "escalate"}
        approval_status = ApprovalStatus.PENDING.value
        status = "PENDING_APPROVAL"
    else:
        input_data = build_tool_input(tool.name, tool.input_schema, target_ctx, query)
        evidence = await gateway.execute_tool(
            db, tool=tool, role_name=user.role_name, input_data=input_data, target=target_ctx.get("hostname", ""),
            request_id=request_id, approval_confirmed=True,
        )
        executions.append(evidence)
        verification = await verify(plan=plan, evidence=executions, permission_result=PermissionResult.ALLOWED.value)
        from app.agents.llm_provider import get_llm_provider

        provider = get_llm_provider()
        answer = await provider.generate_answer(query=query, evidence=executions, verification=verification)
        approval_status = ApprovalStatus.NOT_REQUIRED.value
        status = "COMPLETED"

    total_latency_ms = round((time.time() - started) * 1000, 2)
    audit_log = await audit_service.write_audit_log(
        db, request_id=request_id, user_id=user.id, user_role=user.role_name, user_query=query,
        detected_intent=intent_result.intent, candidate_tools=[tool.name], selected_tools=[tool.name],
        risk_level=tool.risk_level, permission_result=decision.result.value, approval_status=approval_status,
        execution_result={"executions": executions}, execution_latency_ms=total_latency_ms,
        verification_result=verification, final_response=answer, status=status,
    )
    await db.commit()

    return {
        "request_id": request_id, "intent": intent_result.intent, "risk_level": tool.risk_level,
        "permission_result": decision.result.value, "routing_candidates": routing_candidates,
        "selected_tools": [tool.name], "executions": executions, "evidence": executions, "plan": plan,
        "answer": answer, "verification": verification, "audit_id": audit_log.id,
        "pending_approval_id": pending_approval_id, "security_findings": [], "total_latency_ms": total_latency_ms,
    }
