from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.schemas.misc import AuditLogOut
from app.services import audit_service

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def get_audit_logs(
    user_id: str | None = None, role: str | None = None, tool: str | None = None, risk: str | None = None,
    status_filter: str | None = None, request_id: str | None = None, limit: int = 100,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list:
    return await audit_service.list_audit_logs(
        db, user_id=user_id, role=role, tool=tool, risk=risk, status=status_filter, request_id=request_id, limit=limit,
    )
