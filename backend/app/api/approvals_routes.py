"""
Approval Center routes.

CRITICAL invariant enforced here (not just in the UI): approving an
Approval record is what actually triggers execution via the MCP Gateway.
A frontend button press alone never executes anything -- and only a user
whose OWN role satisfies the tool's `required_roles` (i.e. is itself
authorized to run that tool) may approve it. This stops a lower-privileged
user from rubber-stamping their own escalation request.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.enums import PermissionResult
from app.database.session import get_db
from app.mcp import gateway
from app.models.entities import McpTool, User
from app.schemas.misc import ApprovalDecisionRequest, ApprovalOut
from app.security.policy_engine import get_policy_engine
from app.services import approval_service, audit_service

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(
    status_filter: str | None = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list:
    return await approval_service.list_approvals(db, status=status_filter)


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str, payload: ApprovalDecisionRequest, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    approval = await approval_service.get_approval(db, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found.")
    if approval.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Approval already {approval.status}.")

    tool_result = await db.execute(select(McpTool).where(McpTool.name == approval.tool_name))
    tool_obj = tool_result.scalar_one_or_none()
    if tool_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Underlying tool not found.")

    # The approver must themselves be authorized for this tool (elevated-role check).
    policy_engine = get_policy_engine()
    approver_decision = policy_engine.evaluate(
        role_name=current_user.role_name, tool_name=tool_obj.name, tool_category=tool_obj.category,
        tool_risk_level=tool_obj.risk_level, tool_required_roles=tool_obj.required_roles or [],
    )
    if approver_decision.result == PermissionResult.DENIED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail=f"Your role ('{current_user.role_name}') is not authorized to approve this action.")

    decided = await approval_service.decide(
        db, approval_id=approval_id, approve=True, decided_by=current_user.id, decision_note=payload.decision_note,
    )

    try:
        evidence = await gateway.execute_tool(
            db, tool=tool_obj, role_name=approval.requested_by_role, input_data=approval.input_data or {},
            target=approval.target, request_id=approval.request_id, approval_confirmed=True,
        )
        await db.commit()
        return {"status": "approved_and_executed", "approval_id": approval_id, "evidence": evidence}
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail=f"Approved, but execution failed: {exc}") from exc


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str, payload: ApprovalDecisionRequest, current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    decided = await approval_service.decide(
        db, approval_id=approval_id, approve=False, decided_by=current_user.id, decision_note=payload.decision_note,
    )
    if decided is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found or not pending.")
    await audit_service.write_security_event(
        db, request_id=decided.request_id, event_type="approval_rejected", severity="MEDIUM",
        description=f"Approval for '{decided.tool_name}' rejected by {current_user.email}.",
        user_id=current_user.id, blocked=True,
    )
    await db.commit()
    return {"status": "rejected", "approval_id": approval_id}
