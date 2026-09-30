from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import handle_query
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(
    payload: AgentQueryRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> AgentQueryResponse:
    result = await handle_query(db, user=current_user, query=payload.query, session_id=payload.session_id)
    return AgentQueryResponse(**result)
