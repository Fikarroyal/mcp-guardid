from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.schemas.misc import SecurityEventOut
from app.services import audit_service

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.get("/events", response_model=list[SecurityEventOut])
async def list_security_events(
    limit: int = 100, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list:
    return await audit_service.list_security_events(db, limit=limit)
