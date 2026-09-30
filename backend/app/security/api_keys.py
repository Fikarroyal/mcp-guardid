"""
Service-account API keys (Section: additional platform feature).

Keys are high-entropy random tokens (`gid_<32-byte-urlsafe>`), hashed with
plain SHA-256 (not bcrypt) for storage -- deliberately, since bcrypt's
per-value salt makes an exact-match DB lookup by hash impossible, whereas a
deterministic digest lets `resolve_api_key` find the matching row in a
single indexed query. This is the standard, accepted pattern for
high-entropy API keys (unlike human passwords, which use bcrypt precisely
*because* they are low-entropy and need salting against precomputation).

Each key is bound to a synthetic, non-login `User` row so every downstream
component (Policy Engine, Tool Retrieval, MCP Gateway, audit logging) keeps
treating "who is making this request" as a plain `User` -- no parallel
authorization path to fall out of sync with the rest of the system.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ApiKey, User
from app.security.auth import hash_password

KEY_PREFIX = "gid_"


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_raw_key() -> str:
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def display_prefix(raw_key: str) -> str:
    return raw_key[:12] + "..."


async def create_service_user(db: AsyncSession, *, name: str, role_name: str, department: str) -> User:
    """Every API key needs a User row to bind to; keys never share a human's
    login row so revoking/expiring a key can never accidentally touch a
    real person's account."""
    service_user = User(
        email=f"svc-{secrets.token_hex(4)}@service.mcpguardid.internal",
        full_name=f"Service Account: {name}",
        hashed_password=hash_password(secrets.token_urlsafe(24)),  # random, never used to log in
        role_name=role_name,
        department=department,
        is_active=True,
    )
    db.add(service_user)
    await db.flush()
    return service_user


async def resolve_api_key(db: AsyncSession, raw_key: str) -> User | None:
    result = await db.execute(select(ApiKey).where(ApiKey.hashed_key == _hash(raw_key)))
    api_key = result.scalar_one_or_none()
    if api_key is None or not api_key.is_active:
        return None
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None

    user = await db.get(User, api_key.user_id)
    if user is None or not user.is_active:
        return None

    api_key.last_used = datetime.utcnow()
    await db.flush()
    return user
