"""Authentication and authorization services for JWT token management."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from jose import JWTError, jwt

from .config import settings
from ..models import User


def create_access_token(
    data: dict,
    roles: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    role_list = roles if roles is not None else []
    to_encode.update({"exp": expire, "roles": role_list})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a new refresh token."""
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token(data=data, expires_delta=expires)


def verify_token(token: str, credentials_exception) -> dict:
    """Verify the token and return the payload."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return {
            "sub": payload.get("sub"),
            "roles": payload.get("roles", []),
            "exp": payload.get("exp"),
        }
    except JWTError:
        raise credentials_exception


def verify_refresh_token(token: str) -> dict:
    """Verify and decode a refresh token."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise
