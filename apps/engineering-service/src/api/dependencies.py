"""API dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from src.integrations.project_service_client import ProjectServiceClient

from packages.common.auth.middleware import get_current_user
from packages.common.auth.models import UserContext


async def get_user_context(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """Get authenticated user context.

    Args:
        user: User context from auth middleware

    Returns:
        UserContext with user information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "AUTH_001",
                "message": "Authentication required",
            },
        )
    return user


async def require_engineer_role(
    user: UserContext = Depends(get_user_context),
) -> UserContext:
    """Require engineer role for access.

    Args:
        user: User context from auth middleware

    Returns:
        UserContext if user has engineer role

    Raises:
        HTTPException: If user doesn't have engineer role
    """
    allowed_roles = ["engineer", "admin", "project_manager"]
    if not any(role in user.roles for role in allowed_roles):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "AUTH_002",
                "message": f"Required roles: {allowed_roles}",
            },
        )
    return user


async def verify_project_access(
    project_id: UUID,
    user: UserContext = Depends(get_user_context),
) -> UserContext:
    """Verify user has access to the specified project.

    Args:
        project_id: Project ID to verify access for
        user: User context from auth middleware

    Returns:
        UserContext if user has project access

    Raises:
        HTTPException: If user doesn't have project access
    """
    # Admin users have access to all projects
    if "admin" in user.roles:
        return user

    # Verify project membership via Project Service
    try:
        project_client = ProjectServiceClient()
        has_access = await project_client.verify_project_membership(
            project_id=project_id,
            user_id=UUID(user.user_id),
        )

        if not has_access:
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "AUTH_004",
                    "message": "User is not a member of this project",
                },
            )

        return user

    except Exception:
        # If project service is unavailable, fall back to role check
        if not any(
            role in user.roles for role in ["engineer", "project_manager", "designer"]
        ):
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "AUTH_002",
                    "message": "Insufficient permissions to access project",
                },
            )
        return user


async def require_document_modification_permission(
    user: UserContext = Depends(require_engineer_role),
) -> UserContext:
    """Require permission to modify engineering documents.

    Args:
        user: User context from auth middleware

    Returns:
        UserContext if user has modification permissions

    Raises:
        HTTPException: If user doesn't have modification permissions
    """
    # Check if user has write permissions for engineering documents
    allowed_permissions = [
        "write:designs",
        "write:all",
        "manage:projects",
    ]

    has_permission = any(perm in user.permissions for perm in allowed_permissions)

    if not has_permission and "admin" not in user.roles:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "AUTH_002",
                "message": "Insufficient permissions to modify documents",
            },
        )

    return user


async def get_optional_user_context(
    request: Request,
) -> Optional[UserContext]:
    """Get optional user context (doesn't require authentication).

    Args:
        request: HTTP request

    Returns:
        UserContext if authenticated, None otherwise
    """
    return getattr(request.state, "user", None)


def require_calculation_permission(
    user: UserContext = Depends(require_engineer_role),
) -> UserContext:
    """Require permission to perform engineering calculations.

    Args:
        user: User context from auth middleware

    Returns:
        UserContext if user has calculation permissions

    Raises:
        HTTPException: If user doesn't have calculation permissions
    """
    # Engineers, project managers, and admins can perform calculations
    allowed_roles = ["engineer", "admin", "project_manager"]
    if not any(role in user.roles for role in allowed_roles):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "AUTH_002",
                "message": f"Required roles: {allowed_roles}",
            },
        )
    return user


def require_code_validation_permission(
    user: UserContext = Depends(require_engineer_role),
) -> UserContext:
    """Require permission to perform code validation.

    Args:
        user: User context from auth middleware

    Returns:
        UserContext if user has validation permissions

    Raises:
        HTTPException: If user doesn't have validation permissions
    """
    # Only engineers and admins can perform code validation
    allowed_roles = ["engineer", "admin"]
    if not any(role in user.roles for role in allowed_roles):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "AUTH_002",
                "message": f"Required roles: {allowed_roles}",
            },
        )
    return user
