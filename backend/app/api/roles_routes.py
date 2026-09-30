"""
Roles & Permissions management. Edits are persisted AND hot-reloaded into
`policy_overrides`, which PolicyEngine reads on every evaluation, so a change
here takes effect immediately for every subsequent request. Only the
Enterprise Administrator may edit; everyone authenticated may read.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.enums import RiskLevel, ToolCategory
from app.database.session import get_db
from app.models.entities import Permission, Role, User
from app.schemas.admin import PermissionOut, RoleOut, RoleUpdate
from app.security.policy_overrides import reload_overrides

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])

_EDITORS = ("Enterprise Administrator",)


@router.get("", response_model=list[RoleOut])
async def list_roles(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[Role]:
    result = await db.execute(select(Role))
    return sorted(result.scalars().all(), key=lambda r: RiskLevel(r.max_risk_level).rank)


@router.put("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: str, payload: RoleUpdate, current_user: User = Depends(require_roles(*_EDITORS)),
    db: AsyncSession = Depends(get_db),
) -> Role:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    if payload.max_risk_level is not None:
        try:
            RiskLevel(payload.max_risk_level)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid risk level.")
        if role.name == current_user.role_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="You cannot change the risk ceiling of your own role.")
        role.max_risk_level = payload.max_risk_level
    if payload.description is not None:
        role.description = payload.description
    await db.commit()
    await reload_overrides(db)
    await db.refresh(role)
    return role


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[PermissionOut]:
    """Full role x category matrix. Missing rows mean "no extra restriction" (allowed)."""
    roles = (await db.execute(select(Role))).scalars().all()
    rows = (await db.execute(select(Permission))).scalars().all()
    existing = {(p.role_name, p.category): p for p in rows}
    out: list[PermissionOut] = []
    for role in roles:
        for category in ToolCategory:
            row = existing.get((role.name, category.value))
            out.append(PermissionOut(id=row.id if row else f"{role.name}::{category.value}", role_name=role.name,
                                      category=category.value, allowed=row.allowed if row else True))
    return out


@router.put("/permissions/set", response_model=PermissionOut)
async def set_permission(
    role_name: str, category: str, allowed: bool, current_user: User = Depends(require_roles(*_EDITORS)),
    db: AsyncSession = Depends(get_db),
) -> PermissionOut:
    if role_name == current_user.role_name and not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot block categories for your own role.")
    try:
        ToolCategory(category)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown category.")
    role = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    row = (await db.execute(select(Permission).where(Permission.role_name == role_name,
                                                      Permission.category == category))).scalar_one_or_none()
    if row is None:
        row = Permission(role_name=role_name, category=category, allowed=allowed)
        db.add(row)
    else:
        row.allowed = allowed
    await db.commit()
    await reload_overrides(db)
    return PermissionOut(id=row.id, role_name=role_name, category=category, allowed=allowed)
