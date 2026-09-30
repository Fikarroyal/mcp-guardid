from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.entities import Incident, User
from app.schemas.misc import IncidentOut

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
async def list_incidents(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[Incident]:
    result = await db.execute(select(Incident).order_by(Incident.detected_at.desc()))
    return list(result.scalars().all())
