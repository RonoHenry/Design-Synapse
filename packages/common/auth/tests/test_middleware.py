"""Tests for authentication middleware integration."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from ..middleware import (AuthDependency, AuthMiddleware, get_current_user,
                          require_permissions, require_roles)
from ..models import AuthResult, UserContext
from ..service_auth import ServiceAuthenticator
from ..validator import JWTValidator


class TestAuthMiddleware:
    """Test authentication middleware functionality."""

    @pytest.fixture
    def secret_key(self):
        """Test secret key."""
        return "test-middleware-secret"

    @pytest.fixture
    def app(self, secret_key):
        """FastAPI app with auth middleware."""
        app = FastAPI()

        app.add_middleware(
            AuthMiddleware,
            secret_key=secret_key,
            service_secret_key=secret_key,
            excluded_paths=["/health", "/public"],
            require_auth=True,
        )

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        @app.get("/public")
        async def public():
            return {"message": "public endpoint"}

        @app.get("/protected")
        async def protected(request: Request):
            user = getattr(request.state, "user", None)
            return {"user_id": user.user_id if user else None}

        @app.get("/admin")
        async def admin_endpoint(user: UserContext = Depends(require_roles("admin"))):
            return {"message": "admin access", "user": user.user_id}

        @app.get("/designer")
        async def designer_endpoint(
            user: UserContext = Depends(require_permissions("write:designs")),
        ):
            return {"message": "designer access", "user": user.user_id}

        return app

    @pytest.fixture
    def client(self, app):
        """Test client."""
        return TestClient(app)

    @pytest.fixture
    def jwt_validator(self, secret_key):
        """JWT validator for creating test tokens."""
        return JWTValidator(secret_key=secret_key)

    @pytest.fixture
    def service_auth(self, secret_key):
        """Service authenticator for creating service tokens."""
        return ServiceAuthenticator(secret_key=secret_key)

    @pytest.fixture
    def valid_user_token(self, jwt_validator, secret_key):
        """Valid user JWT token."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        payload = {
            "sub": "user123",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "roles": ["designer", "viewer"],
            "permissions": ["read:projects", "write:designs"],
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @pytest.fixture
    def admin_token(self, secret_key):
        """Admin user JWT token."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        payload = {
            "sub": "admin123",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "roles": ["admin"],
            "permissions": ["read:all", "write:all", "manage:users"],
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    def test_excluded_paths_no_auth(self, client):
        """Test excluded paths don't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"message": "public endpoint"}

    def test_protected_endpoint_no_token(self, client):
        """Test protected endpoint without token returns 401."""
        response = client.get("/protected")
        assert response.status_code == 401
        assert "error_code" in response.json()

    def test_protected_endpoint_invalid_token(self, client):
        """Test protected endpoint with invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/protected", headers=headers)
        assert response.status_code == 401

    def test_protected_endpoint_valid_token(self, client, valid_user_token):
        """Test protected endpoint with valid token succeeds."""
        headers = {"Authorization": f"Bearer {valid_user_token}"}
        response = client.get("/protected", headers=headers)

        assert response.status_code == 200
        assert response.json()["user_id"] == "user123"

    def test_service_to_service_authentication(self, client, service_auth):
        """Test service-to-service authentication."""
        headers = service_auth.get_service_headers("test-service")
        response = client.get("/protected", headers=headers)

        assert response.status_code == 200
        assert "service:test-service" in response.json()["user_id"]

    def test_role_based_access_control_admin(self, client, admin_token):
        """Test role-based access control for admin endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/admin", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "admin access"

    def test_role_based_access_control_denied(self, client, valid_user_token):
        """Test role-based access control denies non-admin."""
        headers = {"Authorization": f"Bearer {valid_user_token}"}
        response = client.get("/admin", headers=headers)

        assert response.status_code == 403
        assert "error_code" in response.json()

    def test_permission_based_access_control(self, client, valid_user_token):
        """Test permission-based access control."""
        headers = {"Authorization": f"Bearer {valid_user_token}"}
        response = client.get("/designer", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "designer access"

    def test_user_context_injection(self, client, valid_user_token):
        """Test user context is properly injected into request."""
        headers = {"Authorization": f"Bearer {valid_user_token}"}

        with patch.object(AuthMiddleware, "_inject_user_headers") as mock_inject:
            response = client.get("/protected", headers=headers)
            assert response.status_code == 200

            # Verify user context was injected
            mock_inject.assert_called_once()
            args = mock_inject.call_args[0]
            user_context = args[1]
            assert user_context.user_id == "user123"
            assert "designer" in user_context.roles


class TestAuthDependency:
    """Test authentication dependency functionality."""

    @pytest.fixture
    def mock_request(self):
        """Mock request with user context."""
        request = Mock(spec=Request)
        request.state = Mock()
        return request

    def test_auth_dependency_with_user(self, mock_request):
        """Test auth dependency when user is present."""
        user_context = UserContext(
            user_id="test123",
            email="test@example.com",
            roles=["viewer"],
            permissions=["read:projects"],
        )
        mock_request.state.user = user_context

        dependency = AuthDependency(require_auth=True)

        # Use asyncio to run the async function
        import asyncio

        result = asyncio.run(dependency(mock_request))

        assert result == user_context

    def test_auth_dependency_no_user_required(self, mock_request):
        """Test auth dependency when user is required but not present."""
        mock_request.state.user = None

        dependency = AuthDependency(require_auth=True)

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(dependency(mock_request))

        assert exc_info.value.status_code == 401

    def test_auth_dependency_no_user_optional(self, mock_request):
        """Test auth dependency when user is optional and not present."""
        mock_request.state.user = None

        dependency = AuthDependency(require_auth=False)

        import asyncio

        result = asyncio.run(dependency(mock_request))

        assert result is None

    def test_get_current_user_convenience(self, mock_request):
        """Test get_current_user convenience function."""
        user_context = UserContext(
            user_id="current123",
            email="current@example.com",
            roles=["designer"],
            permissions=["write:designs"],
        )
        mock_request.state.user = user_context

        import asyncio

        result = asyncio.run(get_current_user(mock_request))

        assert result == user_context


class TestRolePermissionDependencies:
    """Test role and permission dependency factories."""

    @pytest.fixture
    def admin_user(self):
        """Admin user context."""
        return UserContext(
            user_id="admin123",
            email="admin@example.com",
            roles=["admin"],
            permissions=["read:all", "write:all"],
        )

    @pytest.fixture
    def designer_user(self):
        """Designer user context."""
        return UserContext(
            user_id="designer123",
            email="designer@example.com",
            roles=["designer"],
            permissions=["read:projects", "write:designs"],
        )

    def test_require_roles_success(self, admin_user):
        """Test require_roles dependency with valid role."""
        role_dependency = require_roles("admin")

        import asyncio

        result = asyncio.run(role_dependency(admin_user))

        assert result == admin_user

    def test_require_roles_failure(self, designer_user):
        """Test require_roles dependency with invalid role."""
        role_dependency = require_roles("admin")

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(role_dependency(designer_user))

        assert exc_info.value.status_code == 403
        assert "AUTH_002" in str(exc_info.value.detail)

    def test_require_roles_multiple(self, designer_user):
        """Test require_roles dependency with multiple valid roles."""
        role_dependency = require_roles("admin", "designer")

        import asyncio

        result = asyncio.run(role_dependency(designer_user))

        assert result == designer_user

    def test_require_permissions_success(self, designer_user):
        """Test require_permissions dependency with valid permission."""
        perm_dependency = require_permissions("write:designs")

        import asyncio

        result = asyncio.run(perm_dependency(designer_user))

        assert result == designer_user

    def test_require_permissions_failure(self, designer_user):
        """Test require_permissions dependency with invalid permission."""
        perm_dependency = require_permissions("manage:users")

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(perm_dependency(designer_user))

        assert exc_info.value.status_code == 403
        assert "AUTH_002" in str(exc_info.value.detail)

    def test_require_permissions_multiple(self, designer_user):
        """Test require_permissions dependency with multiple permissions."""
        perm_dependency = require_permissions("read:projects", "write:designs")

        import asyncio

        result = asyncio.run(perm_dependency(designer_user))

        assert result == designer_user


class TestMiddlewareErrorHandling:
    """Test middleware error handling scenarios."""

    @pytest.fixture
    def app_optional_auth(self, secret_key):
        """FastAPI app with optional authentication."""
        app = FastAPI()

        app.add_middleware(
            AuthMiddleware, secret_key=secret_key, require_auth=False  # Optional auth
        )

        @app.get("/optional")
        async def optional_endpoint(request: Request):
            user = getattr(request.state, "user", None)
            return {"authenticated": user is not None}

        return app

    def test_optional_auth_no_token(self):
        """Test optional authentication without token."""
        app = FastAPI()

        app.add_middleware(
            AuthMiddleware, secret_key="test-key", require_auth=False  # Optional auth
        )

        @app.get("/optional")
        async def optional_endpoint(request: Request):
            user = getattr(request.state, "user", None)
            return {"authenticated": user is not None}

        client = TestClient(app)
        response = client.get("/optional")
        assert response.status_code == 200
        assert response.json()["authenticated"] is False

    def test_middleware_logging(self, client, valid_user_token):
        """Test middleware logging functionality."""
        with patch("packages.common.auth.middleware.logger") as mock_logger:
            headers = {"Authorization": f"Bearer {valid_user_token}"}
            response = client.get("/protected", headers=headers)

            assert response.status_code == 200

            # Verify successful authentication was logged
            mock_logger.info.assert_called()
            log_call = mock_logger.info.call_args[0][0]
            assert "Authenticated request" in log_call
