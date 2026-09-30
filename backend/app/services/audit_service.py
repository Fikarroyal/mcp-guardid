from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditLog, SecurityEvent


async def write_audit_log(db: AsyncSession, **fields: Any) -> AuditLog:
    log = AuditLog(created_at=datetime.utcnow(), **fields)
    db.add(log)
    await db.flush()
    return log


async def write_security_event(
    db: AsyncSession, *, request_id: str, event_type: str, severity: str, description: str,
    user_id: str | None = None, blocked: bool = True,
) -> SecurityEvent:
    event = SecurityEvent(
        request_id=request_id, event_type=event_type, severity=severity, description=description,
        user_id=user_id, blocked=blocked, created_at=datetime.utcnow(),
    )
    db.add(event)
    await db.flush()
    return event


async def list_audit_logs(
    db: AsyncSession, *, user_id: str | None = None, role: str | None = None, tool: str | None = None,
    risk: str | None = None, status: str | None = None, request_id: str | None = None, limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if role:
        stmt = stmt.where(AuditLog.user_role == role)
    if risk:
        stmt = stmt.where(AuditLog.risk_level == risk)
    if status:
        stmt = stmt.where(AuditLog.status == status)
    if request_id:
        stmt = stmt.where(AuditLog.request_id == request_id)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())
    if tool:
        logs = [log for log in logs if tool in (log.selected_tools or [])]
    return logs


async def list_security_events(db: AsyncSession, *, limit: int = 100) -> list[SecurityEvent]:
    stmt = select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
