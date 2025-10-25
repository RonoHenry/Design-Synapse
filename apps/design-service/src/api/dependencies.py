"""
Authentication and authorization dependencies for the Design Service API.

This module provides FastAPI dependency functions for:
- Authenticating users via JWT tokens
- Extracting user information from tokens
- Verifying project access
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..services.project_client import ProjectClient, ProjectAccessDeniedError

# OAuth2 scheme for bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

# JWT configuration (should match user-service configuration)
SECRET_KEY = "your-secret-key-here"  # TODO: Move to config
ALGORITHM = "HS256"


def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> int:
    """
    Dependency to extract and validate the current user ID from JWT token.
    
    Args:
        token: JWT bearer token from Authorization header
        
    Returns:
        User ID extracted from token
        
    Raises:
        HTTPException: 401 if token is invalid or missing user ID
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        # Convert to integer
        return int(user_id)
        
    except (JWTError, ValueError):
        raise credentials_exception


async def verify_project_access(
    project_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> bool:
    """
    Dependency to verify that a user has access to a specific project.
    
    Args:
        project_id: ID of the project to check access for
        user_id: ID of the current user
        db: Database session
        
    Returns:
        True if user has access
        
    Raises:
        HTTPException: 403 if user doesn't have access to the project
    """
    try:
        # Create project client
        project_client = ProjectClient()
        
        # Verify access
        await project_client.verify_project_access(
            project_id=project_id,
            user_id=user_id,
        )
        
        return True
        
    except ProjectAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to project {project_id}",
        )
    except Exception as e:
        # Log the error
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to verify project access",
        )


# Type aliases for cleaner endpoint signatures
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
