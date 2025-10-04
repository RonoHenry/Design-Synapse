"""Authentication and authorization dependencies."""

from typing import Annotated, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings

oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)]
) -> Dict:
    """Validate JWT token and return current user data."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    """Validate JWT token and return current user data."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Add role information from token
        roles = payload.get("roles", [])
        
        return {
            "id": user_id,
            "roles": roles
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_comment_permission(user: Dict, comment_author_id: int, project_owner_id: int) -> bool:
    """Check if user has permission to modify/delete a comment."""
    # Convert user id to integer for comparison
    user_id = int(user["id"])

    # User can modify their own comments
    if user_id == comment_author_id:
        return True
    
    # Project owner can modify any comment in their project
    if user_id == project_owner_id:
        return True
    
    # Admin users can modify any comment
    if "admin" in user["roles"]:
        return True
    
    return False