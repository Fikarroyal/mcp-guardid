"""Execution Log: browse raw MCP Gateway tool executions (independent of the
higher-level Audit Trail), with filters, plus retention purge."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database.session import get_db
from app.models.entities import ToolExecution, User
from app.schemas.admin import ToolExecutionOut

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.get("", response_model=list[ToolExecutionOut])
async def list_executions(
    tool: str | None = None, status_filter: str | None = None, limit: int = 200,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[ToolExecution]:
    stmt = select(ToolExecution).order_by(ToolExecution.timestamp.desc()).limit(min(limit, 1000))
    if tool:
        stmt = stmt.where(ToolExecution.tool_name == tool)
    if status_filter:
        stmt = stmt.where(ToolExecution.status == status_filter)
    return list((await db.execute(stmt)).scalars().all())


@router.delete("/{execution_pk}")
async def delete_execution(
    execution_pk: str, current_user: User = Depends(require_roles("Infrastructure Administrator", "Enterprise Administrator")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.get(ToolExecution, execution_pk)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found.")
    await db.delete(row)
    await db.commit()
    return {"status": "deleted"}


@router.post("/purge")
async def purge_old_executions(
    older_than_days: int = 30,
    current_user: User = Depends(require_roles("Infrastructure Administrator", "Enterprise Administrator")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if older_than_days < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="older_than_days must be >= 1.")
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    result = await db.execute(delete(ToolExecution).where(ToolExecution.timestamp < cutoff))
    await db.commit()
    return {"status": "purged", "deleted": result.rowcount or 0, "older_than_days": older_than_days}
