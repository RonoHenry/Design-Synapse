"""Authentication and authorization dependencies for the API.

This module provides FastAPI dependency functions for authenticating users,
validating JWTs, and checking role-based access control. It includes:
- Current user dependency injection
- Role-based access control functions
- OAuth2 bearer token handling
"""

from typing import Annotated, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from ..core.security import verify_token
from ..infrastructure.database import get_db
from ..models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token, credentials_exception)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def has_role(required_roles: List[str]):
    """Dependency factory to check if the current user has required roles.

    Creates a dependency that verifies the current user has at least one of the
    specified roles. If the user lacks all required roles, raises a 403 error.

    Usage:
        @router.get("/admin", dependencies=[Depends(has_role(["admin"]))])

    Args:
        required_roles: List of role names to check against
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> bool:
        for role in required_roles:
            if current_user.has_role(role):
                return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have the required role to access this resource",
        )

    return role_checker
