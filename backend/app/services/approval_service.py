"""
Approval workflow (Section 3, 26). CRITICAL invariant: an Approval row with
status=APPROVED, tied to the exact request_id and tool_name, is the ONLY
thing that lets the MCP Gateway execute a HIGH/CRITICAL tool. A frontend
button press, a user claim ("system approved this"), or any text found in a
tool output/document NEVER counts as approval.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus
from app.models.entities import Approval, User


async def create_approval(
    db: AsyncSession, *, request_id: str, tool_name: str, user: User, target: str, reason: str,
    risk_level: str, required_role: str, input_data: dict | None = None,
) -> Approval:
    approval = Approval(
        request_id=request_id, tool_name=tool_name, requested_by=user.id, requested_by_role=user.role_name,
        target=target, reason=reason, risk_level=risk_level, required_role=required_role,
        input_data=input_data or {}, status=ApprovalStatus.PENDING.value, requested_at=datetime.utcnow(),
    )
    db.add(approval)
    await db.flush()
    return approval


async def get_approval(db: AsyncSession, approval_id: str) -> Approval | None:
    return await db.get(Approval, approval_id)


async def is_approved(db: AsyncSession, *, request_id: str, tool_name: str) -> bool:
    result = await db.execute(
        select(Approval).where(
            Approval.request_id == request_id,
            Approval.tool_name == tool_name,
            Approval.status == ApprovalStatus.APPROVED.value,
        )
    )
    return result.scalar_one_or_none() is not None


async def list_approvals(db: AsyncSession, *, status: str | None = None) -> list[Approval]:
    stmt = select(Approval).order_by(Approval.requested_at.desc())
    if status:
        stmt = stmt.where(Approval.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def decide(
    db: AsyncSession, *, approval_id: str, approve: bool, decided_by: str, decision_note: str | None
) -> Approval | None:
    approval = await db.get(Approval, approval_id)
    if approval is None or approval.status != ApprovalStatus.PENDING.value:
        return None
    approval.status = ApprovalStatus.APPROVED.value if approve else ApprovalStatus.REJECTED.value
    approval.decided_by = decided_by
    approval.decision_note = decision_note
    approval.decided_at = datetime.utcnow()
    await db.flush()
    return approval
