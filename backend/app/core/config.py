"""
Application configuration.

All configuration is environment-driven so the same codebase can run against
local/dev adapters (SQLite, in-process vector store, mock LLM) or production
infrastructure (PostgreSQL + pgvector/Qdrant + real LLM API) without code
changes -- only environment variables change.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchored to the `backend/` directory (this file lives at
# backend/app/core/config.py), NOT to the process's current working
# directory. This matters: seeding the database from the project root and
# then running `cd backend && uvicorn main:app` must resolve to the exact
# same SQLite file, or you get a backend that "starts fine" but has no
# seeded users -- every login then fails with 401 for a reason that has
# nothing to do with the password. A relative "./mcp_guardid.db" default
# would silently create a *different* file depending on which directory a
# command happens to be run from; an absolute, code-anchored path cannot.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_SQLITE_PATH = _BACKEND_DIR / "mcp_guardid.db"


class Settings(BaseSettings):
    # `.env` is resolved at the project root (not the process's CWD) for the
    # same reason the SQLite path above is absolute -- so `.env` is picked
    # up consistently no matter which directory you run commands from.
    model_config = SettingsConfigDict(env_file=str(_BACKEND_DIR.parent / ".env"), extra="ignore")

    # --- General ---
    APP_NAME: str = "MCP-GuardID"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # --- Database ---
    # Default: local SQLite file at a fixed, absolute path (see note above),
    # zero external infra required.
    # Production: postgresql+asyncpg://user:pass@host:5432/mcp_guardid
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DEFAULT_SQLITE_PATH}"

    # --- Vector store ---
    # "local"    -> in-process numpy cosine-similarity store (default, dev)
    # "pgvector" -> PostgreSQL + pgvector extension (production)
    # "qdrant"   -> external Qdrant service (production, high scale)
    VECTOR_STORE_BACKEND: Literal["local", "pgvector", "qdrant"] = "local"
    QDRANT_URL: str | None = None
    EMBEDDING_DIMENSION: int = 256

    # --- Redis (optional cache layer) ---
    REDIS_URL: str | None = None

    # --- Auth ---
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION_ENV"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    # --- LLM provider ---
    # "mock"      -> deterministic rule-based planner/verifier (no external call, default)
    # "anthropic" -> real Claude model via Anthropic API
    LLM_PROVIDER: Literal["mock", "anthropic"] = "mock"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # --- Routing ---
    TOOL_RETRIEVAL_TOP_K: int = 5

    # --- Scoring weights: FinalScore = w1*semantic + w2*intent + w3*permission
    #     + w4*context + w5*historical - w6*risk_penalty
    SCORE_W_SEMANTIC: float = 0.30
    SCORE_W_INTENT: float = 0.20
    SCORE_W_PERMISSION: float = 0.20
    SCORE_W_CONTEXT: float = 0.10
    SCORE_W_HISTORICAL: float = 0.10
    SCORE_W_RISK_PENALTY: float = 0.10

    # --- MCP Gateway ---
    MCP_TOOL_TIMEOUT_SECONDS: int = 30
    # "inprocess" (default, demo-friendly) or "stdio" (spawns a real MCP server subprocess)
    MCP_CLIENT_MODE: Literal["inprocess", "stdio"] = "inprocess"


@lru_cache
def get_settings() -> Settings:
    return Settings()
