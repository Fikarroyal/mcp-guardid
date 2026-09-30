from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.config import get_settings
from app.database.session import get_db
from app.models.entities import McpTool
from app.schemas.misc import SystemHealthOut

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health", response_model=SystemHealthOut)
async def health(db: AsyncSession = Depends(get_db)) -> SystemHealthOut:
    settings = get_settings()
    db_status = "healthy"
    try:
        await db.execute(select(McpTool).limit(1))
    except Exception:  # noqa: BLE001
        db_status = "unhealthy"

    llm_status = "healthy" if settings.LLM_PROVIDER == "mock" or settings.ANTHROPIC_API_KEY else "degraded"

    return SystemHealthOut(
        api="healthy", mcp_gateway="healthy", database=db_status, vector_store="healthy",
        llm_service=llm_status, redis="not_configured" if not settings.REDIS_URL else "healthy",
        environment=settings.ENVIRONMENT,
    )


@router.get("/health/live")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(select(McpTool).limit(1))
    return {"status": "ready"}
