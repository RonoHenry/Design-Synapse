"""Authentication and authorization module for Engineering Service."""

from .dependencies import (
    get_current_user,
    get_optional_user,
    require_engineer_role,
    require_permissions,
    require_project_membership,
    require_roles,
)
from .middleware import setup_auth_middleware

__all__ = [
    "setup_auth_middleware",
    "get_current_user",
    "get_optional_user",
    "require_roles",
    "require_permissions",
    "require_engineer_role",
    "require_project_membership",
]
