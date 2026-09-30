"""
MCP Gateway (Section 36). Responsibilities: tool validation, permission
re-enforcement (defense-in-depth -- never trust an upstream "already
checked" flag alone), input validation, execution timeout, evidence
collection, and rolling tool statistics.

Architecture position:
    Agent Orchestrator -> Tool Retrieval Engine -> Policy Engine
        -> MCP Gateway (this module) -> MCP Client -> MCP Server -> Tools
"""
from __future__ import annotations

import random
import string
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ExecutionStatus, PermissionResult
from app.mcp.mcp_client import get_mcp_client
from app.models.entities import McpTool, ToolExecution
from app.security.policy_engine import get_policy_engine


class PermissionDeniedError(Exception):
    pass


class ApprovalRequiredError(Exception):
    pass


class InputValidationError(Exception):
    pass


def _gen_execution_id() -> str:
    return "EX-" + "".join(random.choices(string.digits, k=5))


def _validate_input(tool: McpTool, input_data: dict[str, Any]) -> None:
    required = (tool.input_schema or {}).get("required", [])
    missing = [f for f in required if f not in input_data]
    if missing:
        raise InputValidationError(f"Missing required fields for '{tool.name}': {missing}")


async def execute_tool(
    db: AsyncSession,
    *,
    tool: McpTool,
    role_name: str,
    input_data: dict[str, Any],
    target: str,
    request_id: str,
    approval_confirmed: bool = False,
) -> dict[str, Any]:
    policy_engine = get_policy_engine()
    decision = policy_engine.evaluate(
        role_name=role_name,
        tool_name=tool.name,
        tool_category=tool.category,
        tool_risk_level=tool.risk_level,
        tool_required_roles=tool.required_roles or [],
    )

    if decision.result == PermissionResult.DENIED:
        raise PermissionDeniedError(decision.reason)
    if decision.result == PermissionResult.APPROVAL_REQUIRED and not approval_confirmed:
        raise ApprovalRequiredError(decision.reason)

    _validate_input(tool, input_data)

    client = get_mcp_client()
    response = await client.call_tool(tool.name, input_data, timeout=tool.timeout_seconds)

    status = response.get("status", ExecutionStatus.FAILED.value)
    latency_ms = float(response.get("latency_ms", 0.0))
    result = response.get("result")
    execution_id = _gen_execution_id()

    execution = ToolExecution(
        execution_id=execution_id,
        request_id=request_id,
        tool_name=tool.name,
        target=target,
        status=status,
        latency_ms=latency_ms,
        result=result or {},
        source="mcp",
        timestamp=datetime.utcnow(),
    )
    db.add(execution)

    # Update rolling tool statistics.
    tool.execution_count = (tool.execution_count or 0) + 1
    if status == ExecutionStatus.SUCCESS.value:
        pass
    else:
        tool.failure_count = (tool.failure_count or 0) + 1
    total = tool.execution_count
    prior_successes = total - tool.failure_count
    tool.success_rate = round(100.0 * prior_successes / total, 2) if total else 100.0
    tool.avg_latency_ms = round(
        ((tool.avg_latency_ms or 0.0) * (total - 1) + latency_ms) / total, 2
    ) if total else latency_ms
    tool.last_used = datetime.utcnow()

    await db.flush()

    return {
        "tool_name": tool.name,
        "execution_id": execution_id,
        "timestamp": execution.timestamp.isoformat(),
        "target": target,
        "status": status,
        "latency_ms": latency_ms,
        "result": result or {},
        "source": "mcp",
    }
