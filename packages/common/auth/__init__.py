"""Common authentication middleware for cross-service validation.

This package provides JWT token validation, user context extraction,
service-to-service authentication, and role-based access control
for all microservices in the DesignSynapse platform.
"""

from .middleware import (AuthDependency, AuthMiddleware, get_current_user,
                         get_optional_user, require_permissions, require_roles)
from .models import (AuthResult, PermissionRule, ServiceToken, TokenPayload,
                     UserContext)
from .rbac import RoleBasedAccessControl
from .service_auth import ServiceAuthenticator
from .validator import JWTValidator

__all__ = [
    # Middleware
    "AuthMiddleware",
    "AuthDependency",
    "get_current_user",
    "get_optional_user",
    "require_roles",
    "require_permissions",
    # Models
    "UserContext",
    "TokenPayload",
    "ServiceToken",
    "AuthResult",
    "PermissionRule",
    # Core components
    "JWTValidator",
    "RoleBasedAccessControl",
    "ServiceAuthenticator",
]
