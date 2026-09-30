from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import User
from app.security.api_keys import resolve_api_key
from app.security.auth import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = credentials.credentials

    # Service-account access: tokens issued via the API Keys page start with
    # a fixed prefix and are looked up/hashed instead of JWT-decoded.
    if token.startswith("gid_"):
        user = await resolve_api_key(db, token)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key.")
        return user

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory: restricts an endpoint to a fixed set of roles,
    on top of (never instead of) the normal RBAC/risk checks that already
    guard tool execution. Used for platform-administration surfaces --
    Accounts, API Keys, Roles & Permissions -- that must not be reachable by
    every authenticated user just because they're logged in."""

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}.",
            )
        return current_user

    return _dependency
