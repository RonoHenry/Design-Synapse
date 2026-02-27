"""Authentication middleware for cross-service validation."""

import logging
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from .models import AuthResult, UserContext
from .rbac import RoleBasedAccessControl
from .service_auth import ServiceAuthenticator
from .validator import JWTValidator

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for JWT token validation and user context extraction."""

    def __init__(
        self,
        app,
        secret_key: Optional[str] = None,
        service_secret_key: Optional[str] = None,
        excluded_paths: Optional[list] = None,
        require_auth: bool = True,
    ):
        """Initialize authentication middleware.

        Args:
            app: FastAPI application instance
            secret_key: Secret key for JWT validation
            service_secret_key: Secret key for service-to-service auth
            excluded_paths: List of paths to exclude from authentication
            require_auth: Whether to require authentication by default
        """
        super().__init__(app)

        self.jwt_validator = JWTValidator(secret_key)
        self.service_auth = ServiceAuthenticator(service_secret_key)
        self.rbac = RoleBasedAccessControl()
        self.require_auth = require_auth

        # Setup default excluded paths
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]

        # Setup default RBAC rules
        self.rbac.setup_default_rules()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Extract and validate token
        auth_result = await self._authenticate_request(request)

        if not auth_result.success:
            if self.require_auth:
                logger.warning(
                    f"Authentication failed for {request.url.path}: {auth_result.error_message}",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "error_code": auth_result.error_code,
                        "client_ip": request.client.host if request.client else None,
                    },
                )
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error_code": auth_result.error_code,
                        "message": auth_result.error_message,
                    },
                )
            else:
                # Continue without authentication if not required
                return await call_next(request)

        # Check authorization
        if auth_result.user_context:
            authz_result = self.rbac.check_permissions(
                auth_result.user_context, request.url.path
            )

            if not authz_result.success:
                logger.warning(
                    f"Authorization failed for {request.url.path}: {authz_result.error_message}",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "user_id": auth_result.user_context.user_id,
                        "roles": auth_result.user_context.roles,
                        "error_code": authz_result.error_code,
                    },
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error_code": authz_result.error_code,
                        "message": authz_result.error_message,
                    },
                )

            # Add user context to request state
            request.state.user = auth_result.user_context

            # Add user context headers for downstream services
            self._inject_user_headers(request, auth_result.user_context)

        # Log successful authentication
        logger.info(
            f"Authenticated request to {request.url.path}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "user_id": auth_result.user_context.user_id
                if auth_result.user_context
                else None,
                "service_name": auth_result.user_context.service_name
                if auth_result.user_context
                else None,
            },
        )

        return await call_next(request)

    async def _authenticate_request(self, request: Request) -> AuthResult:
        """Authenticate incoming request.

        Args:
            request: HTTP request to authenticate

        Returns:
            AuthResult with authentication outcome
        """
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return AuthResult(
                success=False,
                error_message="Authorization header missing",
                error_code="AUTH_001",
            )

        # Check if this is a service-to-service request
        service_name = request.headers.get("X-Service-Name")
        service_type = request.headers.get("X-Service-Type")

        if service_name and service_type == "internal":
            # Validate service token
            return self.service_auth.validate_service_token(auth_header)
        else:
            # Validate user JWT token
            return self.jwt_validator.validate_token(auth_header)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication.

        Args:
            path: Request path to check

        Returns:
            True if path should be excluded from authentication
        """
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        return False

    def _inject_user_headers(self, request: Request, user_context: UserContext):
        """Inject user context headers for downstream services.

        Args:
            request: HTTP request to modify
            user_context: User context to inject
        """
        # Create mutable headers dict
        headers = dict(request.headers)

        # Add user context headers
        headers["X-User-ID"] = user_context.user_id
        headers["X-User-Email"] = user_context.email
        headers["X-User-Roles"] = ",".join(user_context.roles)
        headers["X-User-Permissions"] = ",".join(user_context.permissions)

        if user_context.service_name:
            headers["X-Service-Name"] = user_context.service_name

        # Update request headers (this is a bit hacky but necessary for FastAPI)
        request._headers = headers
        request.scope["headers"] = [
            (key.lower().encode(), value.encode()) for key, value in headers.items()
        ]


class AuthDependency:
    """FastAPI dependency for extracting user context from request."""

    def __init__(self, require_auth: bool = True):
        """Initialize auth dependency.

        Args:
            require_auth: Whether to require authentication
        """
        self.require_auth = require_auth
        self.security = HTTPBearer(auto_error=require_auth)

    async def __call__(self, request: Request) -> Optional[UserContext]:
        """Extract user context from authenticated request.

        Args:
            request: HTTP request with user context

        Returns:
            UserContext if authenticated, None otherwise

        Raises:
            HTTPException: If authentication is required but not present
        """
        # Check if user context was set by middleware
        user_context = getattr(request.state, "user", None)

        if not user_context and self.require_auth:
            raise HTTPException(
                status_code=401,
                detail={"error_code": "AUTH_001", "message": "Authentication required"},
            )

        return user_context


# Convenience instances
get_current_user = AuthDependency(require_auth=True)
get_optional_user = AuthDependency(require_auth=False)


def require_roles(*roles: str):
    """Dependency factory for requiring specific roles.

    Args:
        *roles: Required roles

    Returns:
        FastAPI dependency function
    """

    async def role_dependency(user: UserContext = get_current_user) -> UserContext:
        if not any(role in user.roles for role in roles):
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "AUTH_002",
                    "message": f"Required roles: {list(roles)}",
                },
            )
        return user

    return role_dependency


def require_permissions(*permissions: str):
    """Dependency factory for requiring specific permissions.

    Args:
        *permissions: Required permissions

    Returns:
        FastAPI dependency function
    """

    async def permission_dependency(
        user: UserContext = get_current_user,
    ) -> UserContext:
        rbac = RoleBasedAccessControl()
        user_permissions = rbac.get_user_permissions(user)

        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "AUTH_002",
                    "message": f"Required permissions: {list(permissions)}",
                },
            )
        return user

    return permission_dependency
