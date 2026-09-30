"""
API Keys (service accounts). The raw key is returned exactly once, at
creation; only its SHA-256 digest is stored. Admin-only.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.role_policy import ROLE_POLICIES
from app.database.session import get_db
from app.models.entities import ApiKey, User
from app.schemas.admin import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.security import api_keys as keys

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])

_ADMIN_ROLES = ("Infrastructure Administrator", "Enterprise Administrator")


def _to_out(api_key: ApiKey, role_name: str) -> ApiKeyOut:
    return ApiKeyOut(id=api_key.id, name=api_key.name, key_prefix=api_key.key_prefix, role_name=role_name,
                     is_active=api_key.is_active, last_used=api_key.last_used, expires_at=api_key.expires_at,
                     created_at=api_key.created_at)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    current_user: User = Depends(require_roles(*_ADMIN_ROLES)), db: AsyncSession = Depends(get_db),
) -> list[ApiKeyOut]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    out = []
    for k in result.scalars().all():
        svc_user = await db.get(User, k.user_id)
        out.append(_to_out(k, svc_user.role_name if svc_user else "unknown"))
    return out


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate, current_user: User = Depends(require_roles(*_ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    if payload.role_name not in {r.value for r in ROLE_POLICIES}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown role '{payload.role_name}'.")
    # Privilege ceiling: an admin cannot mint a key more powerful than themselves.
    from app.core.enums import RoleName

    caller_ceiling = ROLE_POLICIES[RoleName(current_user.role_name)].max_risk_level.rank
    key_ceiling = ROLE_POLICIES[RoleName(payload.role_name)].max_risk_level.rank
    if key_ceiling > caller_ceiling:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="You cannot issue a key with a higher privilege level than your own role.")

    service_user = await keys.create_service_user(db, name=payload.name, role_name=payload.role_name,
                                                   department=payload.department)
    raw = keys.generate_raw_key()
    api_key = ApiKey(
        name=payload.name, key_prefix=keys.display_prefix(raw), hashed_key=keys._hash(raw),
        user_id=service_user.id, created_by=current_user.id,
        expires_at=(datetime.utcnow() + timedelta(days=payload.expires_in_days)) if payload.expires_in_days else None,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreated(id=api_key.id, name=api_key.name, role_name=payload.role_name, raw_key=raw,
                          key_prefix=api_key.key_prefix, created_at=api_key.created_at)


@router.post("/{key_id}/revoke", response_model=ApiKeyOut)
async def revoke_api_key(
    key_id: str, current_user: User = Depends(require_roles(*_ADMIN_ROLES)), db: AsyncSession = Depends(get_db),
) -> ApiKeyOut:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    api_key.is_active = False
    await db.commit()
    svc_user = await db.get(User, api_key.user_id)
    return _to_out(api_key, svc_user.role_name if svc_user else "unknown")


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str, current_user: User = Depends(require_roles(*_ADMIN_ROLES)), db: AsyncSession = Depends(get_db),
) -> dict:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    svc_user = await db.get(User, api_key.user_id)
    await db.delete(api_key)
    if svc_user is not None:
        await db.flush()
        await db.delete(svc_user)
    await db.commit()
    return {"status": "deleted", "key_id": key_id}
