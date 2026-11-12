"""Integration tests for protected endpoint authentication and authorization.

Tests the full HTTP request/response cycle through the FastAPI app,
verifying that:
- Public endpoints are accessible without authentication
- Protected endpoints return 401 without a valid token
- Protected endpoints return 403 when the user lacks required roles
- Protected endpoints are accessible with valid credentials

Covers Requirements 10.1-10.6.
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from packages.common.auth.models import UserContext

# Set required env vars before importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-integration-tests")
os.environ.setdefault(
    "SERVICE_SECRET_KEY", "test-service-secret-key-for-integration-tests"
)

from src.api.dependencies import get_user_context  # noqa: E402
from src.api.dependencies import require_calculation_permission  # noqa: E402
from src.api.dependencies import require_engineer_role  # noqa: E402
from src.main import app  # noqa: E402 — must come after env setup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "test-secret-key-for-integration-tests"
JWT_ALGORITHM = "HS256"
API_V1 = "/api/v1"


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------


def _make_token(
    user_id: str,
    email: str,
    roles: list,
    permissions: list,
    expired: bool = False,
    secret: str = TEST_SECRET_KEY,
) -> str:
    """Generate a JWT token for testing."""
    now = datetime.now(timezone.utc)
    if expired:
        exp = now - timedelta(hours=1)
    else:
        exp = now + timedelta(hours=1)

    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "roles": roles,
        "permissions": permissions,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def _engineer_token() -> str:
    return _make_token(
        user_id=str(uuid4()),
        email="engineer@example.com",
        roles=["engineer"],
        permissions=["write:designs", "read:designs"],
    )


def _admin_token() -> str:
    return _make_token(
        user_id=str(uuid4()),
        email="admin@example.com",
        roles=["admin"],
        permissions=["write:all", "read:all"],
    )


def _viewer_token() -> str:
    return _make_token(
        user_id=str(uuid4()),
        email="viewer@example.com",
        roles=["viewer"],
        permissions=["read:designs"],
    )


def _expired_token() -> str:
    return _make_token(
        user_id=str(uuid4()),
        email="expired@example.com",
        roles=["engineer"],
        permissions=["write:designs"],
        expired=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Create a test client for the full app."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def engineer_user():
    """Build a UserContext with the engineer role."""
    return UserContext(
        user_id=str(uuid4()),
        email="engineer@example.com",
        roles=["engineer"],
        permissions=["write:designs", "read:designs"],
    )


@pytest.fixture
def admin_user():
    """Build a UserContext with the admin role."""
    return UserContext(
        user_id=str(uuid4()),
        email="admin@example.com",
        roles=["admin"],
        permissions=["write:all", "read:all"],
    )


@pytest.fixture
def viewer_user():
    """Build a UserContext with the viewer role."""
    return UserContext(
        user_id=str(uuid4()),
        email="viewer@example.com",
        roles=["viewer"],
        permissions=["read:designs"],
    )


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


def _inject_user(user: UserContext):
    """Override all auth dependencies to inject a specific user.

    Also patches the middleware's JWT validator to accept any token
    so the middleware layer passes and the dependency override handles
    the role/permission check.
    """
    app.dependency_overrides[get_user_context] = lambda: user
    app.dependency_overrides[require_engineer_role] = lambda: user
    app.dependency_overrides[require_calculation_permission] = lambda: user


def _viewer_jwt_headers() -> dict:
    """Return Authorization headers with a valid viewer JWT token."""
    return {"Authorization": f"Bearer {_viewer_token()}"}


def _engineer_jwt_headers() -> dict:
    """Return Authorization headers with a valid engineer JWT token."""
    return {"Authorization": f"Bearer {_engineer_token()}"}


# ---------------------------------------------------------------------------
# Public endpoints — no auth required
# ---------------------------------------------------------------------------


class TestPublicEndpoints:
    """Public endpoints must be accessible without any authentication."""

    def test_root_health_endpoint_is_public(self, client):
        """GET /health returns 200 without any Authorization header."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_root_health_returns_healthy_status(self, client):
        """GET /health response body contains status=healthy."""
        response = client.get("/health")

        assert response.json()["status"] == "healthy"

    def test_api_v1_health_endpoint_is_public(self, client):
        """GET /api/v1/health returns 200 without any Authorization header."""
        response = client.get(f"{API_V1}/health")

        assert response.status_code == 200

    def test_openapi_docs_are_public(self, client):
        """GET /docs returns 200 without authentication."""
        response = client.get("/docs")

        assert response.status_code == 200

    def test_openapi_json_is_public(self, client):
        """GET /openapi.json returns 200 without authentication."""
        response = client.get("/openapi.json")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Authentication middleware — 401 without valid token
# ---------------------------------------------------------------------------


class TestAuthenticationMiddleware:
    """Protected endpoints must return 401 when no valid token is provided."""

    def test_structural_loads_without_token_returns_401(self, client):
        """POST /structural/loads without Authorization header returns 401."""
        response = client.post(f"{API_V1}/structural/loads", json={})

        assert response.status_code == 401

    def test_structural_beams_without_token_returns_401(self, client):
        """POST /structural/beams without Authorization header returns 401."""
        response = client.post(f"{API_V1}/structural/beams", json={})

        assert response.status_code == 401

    def test_structural_columns_without_token_returns_401(self, client):
        """POST /structural/columns without Authorization header returns 401."""
        response = client.post(f"{API_V1}/structural/columns", json={})

        assert response.status_code == 401

    def test_structural_foundations_without_token_returns_401(self, client):
        """POST /structural/foundations without Authorization header returns 401."""
        response = client.post(f"{API_V1}/structural/foundations", json={})

        assert response.status_code == 401

    def test_get_design_without_token_returns_401(self, client):
        """GET /structural/designs/{id} without Authorization header returns 401."""
        response = client.get(f"{API_V1}/structural/designs/1")

        assert response.status_code == 401

    def test_update_design_without_token_returns_401(self, client):
        """PUT /structural/designs/{id} without Authorization header returns 401."""
        response = client.put(f"{API_V1}/structural/designs/1", json={})

        assert response.status_code == 401

    def test_delete_design_without_token_returns_401(self, client):
        """DELETE /structural/designs/{id} without Authorization header returns 401."""
        response = client.delete(f"{API_V1}/structural/designs/1")

        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """A malformed Bearer token returns 401."""
        headers = {"Authorization": "Bearer this-is-not-a-valid-jwt"}
        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401

    def test_expired_token_returns_401(self, client):
        """An expired JWT token returns 401."""
        headers = {"Authorization": f"Bearer {_expired_token()}"}
        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401

    def test_wrong_secret_token_returns_401(self, client):
        """A token signed with the wrong secret returns 401."""
        bad_token = _make_token(
            user_id=str(uuid4()),
            email="hacker@example.com",
            roles=["engineer"],
            permissions=["write:designs"],
            secret="wrong-secret-key",
        )
        headers = {"Authorization": f"Bearer {bad_token}"}
        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401

    def test_401_response_has_error_structure(self, client):
        """401 response body has the expected error structure."""
        response = client.post(f"{API_V1}/structural/loads", json={})

        # The app wraps HTTPException detail in an "error" key
        body = response.json()
        assert "error" in body


# ---------------------------------------------------------------------------
# Role-based access control — 403 for insufficient roles
# ---------------------------------------------------------------------------


class TestRoleBasedAccessControl:
    """Protected endpoints return 403 when the user lacks required roles."""

    def test_viewer_cannot_post_structural_loads(self, client, viewer_user):
        """Viewer role is denied access to POST /structural/loads."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers=_viewer_jwt_headers(),
        )

        assert response.status_code == 403

    def test_viewer_cannot_post_structural_beams(self, client, viewer_user):
        """Viewer role is denied access to POST /structural/beams."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/beams",
            json={},
            headers=_viewer_jwt_headers(),
        )

        assert response.status_code == 403

    def test_viewer_cannot_post_structural_columns(self, client, viewer_user):
        """Viewer role is denied access to POST /structural/columns."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/columns",
            json={},
            headers=_viewer_jwt_headers(),
        )

        assert response.status_code == 403

    def test_viewer_cannot_post_structural_foundations(self, client, viewer_user):
        """Viewer role is denied access to POST /structural/foundations."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/foundations",
            json={},
            headers=_viewer_jwt_headers(),
        )

        assert response.status_code == 403

    def test_viewer_cannot_update_design(self, client, viewer_user):
        """Viewer role is denied access to PUT /structural/designs/{id}."""
        _inject_user(viewer_user)

        response = client.put(
            f"{API_V1}/structural/designs/1",
            json={},
            headers=_viewer_jwt_headers(),
        )

        assert response.status_code == 403

    def test_viewer_cannot_delete_design(self, client, viewer_user):
        """Viewer role is denied access to DELETE /structural/designs/{id}."""
        _inject_user(viewer_user)

        response = client.delete(
            f"{API_V1}/structural/designs/1",
            headers=_viewer_jwt_headers(),
        )

        assert response.status_code == 403

    def test_403_response_has_error_structure(self, client, viewer_user):
        """403 response body has the expected error structure."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers=_viewer_jwt_headers(),
        )

        body = response.json()
        assert "error" in body


# ---------------------------------------------------------------------------
# Authorized access — engineer and admin can reach endpoints
# ---------------------------------------------------------------------------


class TestAuthorizedAccess:
    """Engineer and admin users can reach protected endpoints (past auth gate)."""

    def test_engineer_reaches_structural_loads_endpoint(self, client, engineer_user):
        """Engineer user gets past auth gate on POST /structural/loads.

        The endpoint may return 422 (validation) or 500 (service error)
        but NOT 401 or 403.
        """
        _inject_user(engineer_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers=_engineer_jwt_headers(),
        )

        assert response.status_code not in (401, 403)

    def test_admin_reaches_structural_loads_endpoint(self, client, admin_user):
        """Admin user gets past auth gate on POST /structural/loads."""
        _inject_user(admin_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )

        assert response.status_code not in (401, 403)

    def test_engineer_reaches_structural_beams_endpoint(self, client, engineer_user):
        """Engineer user gets past auth gate on POST /structural/beams."""
        _inject_user(engineer_user)

        response = client.post(
            f"{API_V1}/structural/beams",
            json={},
            headers=_engineer_jwt_headers(),
        )

        assert response.status_code not in (401, 403)

    def test_engineer_reaches_structural_columns_endpoint(self, client, engineer_user):
        """Engineer user gets past auth gate on POST /structural/columns."""
        _inject_user(engineer_user)

        response = client.post(
            f"{API_V1}/structural/columns",
            json={},
            headers=_engineer_jwt_headers(),
        )

        assert response.status_code not in (401, 403)

    def test_engineer_reaches_structural_foundations_endpoint(
        self, client, engineer_user
    ):
        """Engineer user gets past auth gate on POST /structural/foundations."""
        _inject_user(engineer_user)

        response = client.post(
            f"{API_V1}/structural/foundations",
            json={},
            headers=_engineer_jwt_headers(),
        )

        assert response.status_code not in (401, 403)

    def test_engineer_reaches_get_design_endpoint(self, client, engineer_user):
        """Engineer user gets past auth gate on GET /structural/designs/{id}."""
        _inject_user(engineer_user)

        response = client.get(
            f"{API_V1}/structural/designs/999",
            headers=_engineer_jwt_headers(),
        )

        # 404 is fine — it means auth passed, design just doesn't exist
        assert response.status_code not in (401, 403)

    def test_engineer_reaches_update_design_endpoint(self, client, engineer_user):
        """Engineer user gets past auth gate on PUT /structural/designs/{id}."""
        _inject_user(engineer_user)

        response = client.put(
            f"{API_V1}/structural/designs/999",
            json={},
            headers=_engineer_jwt_headers(),
        )

        assert response.status_code not in (401, 403)

    def test_engineer_reaches_delete_design_endpoint(self, client, engineer_user):
        """Engineer user gets past auth gate on DELETE /structural/designs/{id}."""
        _inject_user(engineer_user)

        response = client.delete(
            f"{API_V1}/structural/designs/999",
            headers=_engineer_jwt_headers(),
        )

        assert response.status_code not in (401, 403)

    def test_viewer_can_read_design_with_auth(self, client, viewer_user):
        """Viewer can GET a design (read-only endpoint uses get_user_context)."""
        # GET /designs/{id} only requires get_user_context, not engineer role
        _inject_user(viewer_user)

        response = client.get(
            f"{API_V1}/structural/designs/999",
            headers=_viewer_jwt_headers(),
        )

        # 404 is fine — auth passed
        assert response.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# JWT token flow — end-to-end with real middleware
# ---------------------------------------------------------------------------


class TestJWTTokenFlow:
    """End-to-end tests using real JWT tokens through the auth middleware."""

    def test_valid_engineer_jwt_passes_middleware(self, client):
        """A valid engineer JWT token passes the auth middleware."""
        token = _engineer_token()
        headers = {"Authorization": f"Bearer {token}"}

        # The endpoint will fail for other reasons (no DB), but not 401
        response = client.get(f"{API_V1}/structural/designs/1", headers=headers)

        assert response.status_code != 401

    def test_valid_admin_jwt_passes_middleware(self, client):
        """A valid admin JWT token passes the auth middleware."""
        token = _admin_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"{API_V1}/structural/designs/1", headers=headers)

        assert response.status_code != 401

    def test_expired_jwt_blocked_by_middleware(self, client):
        """An expired JWT token is blocked by the auth middleware."""
        token = _expired_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401

    def test_tampered_jwt_blocked_by_middleware(self, client):
        """A tampered JWT token is blocked by the auth middleware."""
        token = _engineer_token()
        # Tamper with the payload section
        parts = token.split(".")
        tampered = parts[0] + ".TAMPERED" + parts[2]
        headers = {"Authorization": f"Bearer {tampered}"}

        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401

    def test_missing_bearer_prefix_blocked(self, client):
        """Token without 'Bearer ' prefix is blocked."""
        token = _engineer_token()
        # Send token without "Bearer " prefix
        headers = {"Authorization": token}

        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401

    def test_empty_authorization_header_blocked(self, client):
        """Empty Authorization header is blocked."""
        headers = {"Authorization": ""}

        response = client.post(f"{API_V1}/structural/loads", json={}, headers=headers)

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Error response format validation
# ---------------------------------------------------------------------------


class TestErrorResponseFormat:
    """Auth error responses must have the correct format."""

    def test_401_response_is_json(self, client):
        """401 response is valid JSON."""
        response = client.post(f"{API_V1}/structural/loads", json={})

        assert response.headers["content-type"].startswith("application/json")

    def test_401_response_has_error_key(self, client):
        """401 response body contains an 'error' key."""
        response = client.post(f"{API_V1}/structural/loads", json={})

        body = response.json()
        assert "error" in body

    def test_403_response_is_json(self, client, viewer_user):
        """403 response is valid JSON."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers=_viewer_jwt_headers(),
        )

        assert response.headers["content-type"].startswith("application/json")

    def test_403_response_has_error_key(self, client, viewer_user):
        """403 response body contains an 'error' key."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers=_viewer_jwt_headers(),
        )

        body = response.json()
        assert "error" in body

    def test_401_does_not_expose_internal_paths(self, client):
        """401 response does not expose internal file paths or stack traces."""
        response = client.post(f"{API_V1}/structural/loads", json={})

        body_str = response.text
        assert "src/" not in body_str
        assert "Traceback" not in body_str
        assert "packages/" not in body_str

    def test_403_does_not_expose_internal_paths(self, client, viewer_user):
        """403 response does not expose internal file paths or stack traces."""
        _inject_user(viewer_user)

        response = client.post(
            f"{API_V1}/structural/loads",
            json={},
            headers={"Authorization": "Bearer injected"},
        )

        body_str = response.text
        assert "Traceback" not in body_str


# ---------------------------------------------------------------------------
# Excluded paths — middleware bypass
# ---------------------------------------------------------------------------


class TestExcludedPaths:
    """Paths in the excluded list bypass the auth middleware entirely."""

    def test_docs_path_bypasses_auth(self, client):
        """GET /docs bypasses auth middleware."""
        response = client.get("/docs")
        assert response.status_code != 401

    def test_redoc_path_bypasses_auth(self, client):
        """GET /redoc bypasses auth middleware."""
        response = client.get("/redoc")
        assert response.status_code != 401

    def test_openapi_json_bypasses_auth(self, client):
        """GET /openapi.json bypasses auth middleware."""
        response = client.get("/openapi.json")
        assert response.status_code != 401

    def test_health_path_bypasses_auth(self, client):
        """GET /health bypasses auth middleware."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_api_v1_health_path_bypasses_auth(self, client):
        """GET /api/v1/health bypasses auth middleware."""
        response = client.get(f"{API_V1}/health")
        assert response.status_code == 200
