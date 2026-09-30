from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    token = create_access_token(subject=user.id, extra_claims={"role": user.role_name})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role_name, full_name=user.full_name)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Public self-registration. The role is ALWAYS forced to the lowest
    privilege ("Viewer") server-side -- the request body has no role field,
    so a caller cannot self-assign privileges. An administrator can promote
    the account afterwards from the Accounts page."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")
    user = User(email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password),
                role_name="Viewer", department="General")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(subject=user.id, extra_claims={"role": user.role_name})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role_name, full_name=user.full_name)
