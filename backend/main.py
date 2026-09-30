from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agent_routes,
    api_keys_routes,
    executions_routes,
    roles_routes,
    users_routes,
    approvals_routes,
    audit_routes,
    auth_routes,
    evaluation_routes,
    incidents_routes,
    rag_routes,
    security_routes,
    system_routes,
    tools_routes,
)
from app.core.bootstrap import bootstrap_embeddings
from app.security.policy_overrides import reload_overrides
from app.core.config import get_settings
from app.database.session import AsyncSessionLocal, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        try:
            await bootstrap_embeddings(db)
        except ValueError:
            # Empty corpus (fresh DB, not seeded yet) -- fine, seed script will populate it.
            pass
        await reload_overrides(db)
    yield


app = FastAPI(
    title="MCP-GuardID API",
    description="Intelligent & Secure MCP Tool Router for Enterprise Indonesia",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    users_routes.router,
    api_keys_routes.router,
    roles_routes.router,
    executions_routes.router,
    auth_routes.router,
    agent_routes.router,
    tools_routes.router,
    approvals_routes.router,
    audit_routes.router,
    incidents_routes.router,
    rag_routes.router,
    evaluation_routes.router,
    security_routes.router,
    system_routes.router,
):
    app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {"name": "MCP-GuardID", "status": "running", "docs": "/docs"}
