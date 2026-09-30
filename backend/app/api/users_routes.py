"""
Accounts (Users) management -- CRUD over the `users` table. Reading the
directory is open to any authenticated user; create/update/delete are
restricted to Infrastructure Administrator / Enterprise Administrator since
this is a platform-administration surface.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.role_policy import ROLE_POLICIES
from app.database.session import get_db
from app.models.entities import User
from app.schemas.admin import AdminUserOut, UserCreate, UserUpdate
from app.security.auth import hash_password

router = APIRouter(prefix="/api/v1/users", tags=["accounts"])

_ADMIN_ROLES = ("Infrastructure Administrator", "Enterprise Administrator")
_VALID_ROLES = {r.value for r in ROLE_POLICIES}


@router.get("", response_model=list[AdminUserOut])
async def list_users(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    # Service-account identities (bound to API keys) are managed on the API Keys page.
    return [u for u in result.scalars().all() if not u.email.endswith("@service.mcpguardid.internal")]


@router.post("", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, current_user: User = Depends(require_roles(*_ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> User:
    if payload.role_name not in _VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown role '{payload.role_name}'.")
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists.")

    user = User(
        email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password),
        role_name=payload.role_name, department=payload.department,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str, payload: UserUpdate, current_user: User = Depends(require_roles(*_ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.role_name is not None:
        if payload.role_name not in _VALID_ROLES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown role '{payload.role_name}'.")
        user.role_name = payload.role_name
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.department is not None:
        user.department = payload.department
    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account.")
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str, current_user: User = Depends(require_roles(*_ADMIN_ROLES)), db: AsyncSession = Depends(get_db),
) -> dict:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await db.delete(user)
    await db.commit()
    return {"status": "deleted", "user_id": user_id}
