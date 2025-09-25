"""
Authentication and authorization services.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from src.core.config import settings
from src.models.user import User

def create_access_token(data: dict, roles: Optional[List[str]] = None, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "roles": roles if roles is not None else []
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a new refresh token."""
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token(data=data, expires_delta=expires)

def verify_token(token: str, credentials_exception) -> dict:
    """Verify the token and return the payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return {
            "sub": payload.get("sub"),
            "roles": payload.get("roles", []),
            "exp": payload.get("exp")
        }
    except JWTError:
        raise credentials_exception


def verify_refresh_token(token: str) -> dict:
    """Verify and decode a refresh token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise

# Install the required package
try:
    import jose
except ImportError:
    raise ImportError("The 'python-jose' package is not installed. Please install it by running 'pip install python-jose'.")
