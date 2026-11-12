"""Unit tests for authentication and authorization logic.

Covers Requirements 10.1-10.6:
- 10.1: JWT token validation middleware
- 10.2: Role-based access control (RBAC) - engineer role permissions
- 10.3: Document modification permissions
- 10.4: Project membership verification
- 10.5: Permission checks for engineering operations
- 10.6: Appropriate error responses for auth failures
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.api.dependencies import (
    get_optional_user_context,
    get_user_context,
    require_calculation_permission,
    require_code_validation_permission,
    require_document_modification_permission,
    require_engineer_role,
    verify_project_access,
)

from packages.common.auth.models import UserContext

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engineer_user():
    """Build a standard engineer user with write permissions."""
    return UserContext(
        user_id=str(uuid4()),
        email="engineer@example.com",
        roles=["engineer"],
        permissions=["write:designs", "read:designs"],
    )


@pytest.fixture
def admin_user():
    """Admin user with full permissions."""
    return UserContext(
        user_id=str(uuid4()),
        email="admin@example.com",
        roles=["admin"],
        permissions=["write:all", "read:all"],
    )


@pytest.fixture
def project_manager_user():
    """Project manager user."""
    return UserContext(
        user_id=str(uuid4()),
        email="pm@example.com",
        roles=["project_manager"],
        permissions=["manage:projects", "read:designs"],
    )


@pytest.fixture
def viewer_user():
    """Viewer user with read-only permissions."""
    return UserContext(
        user_id=str(uuid4()),
        email="viewer@example.com",
        roles=["viewer"],
        permissions=["read:designs"],
    )


@pytest.fixture
def no_role_user():
    """User with no roles."""
    return UserContext(
        user_id=str(uuid4()),
        email="norole@example.com",
        roles=[],
        permissions=[],
    )


@pytest.fixture
def multi_role_user():
    """User with multiple roles."""
    return UserContext(
        user_id=str(uuid4()),
        email="multi@example.com",
        roles=["engineer", "project_manager"],
        permissions=["write:designs", "manage:projects"],
    )


# ---------------------------------------------------------------------------
# Requirement 10.1 — JWT token validation (get_user_context)
# ---------------------------------------------------------------------------


class TestGetUserContext:
    """Tests for JWT token validation via get_user_context dependency (Req 10.1)."""

    @pytest.mark.asyncio
    async def test_valid_user_context_is_returned(self, engineer_user):
        """Authenticated user context passes through unchanged."""
        result = await get_user_context(user=engineer_user)

        assert result is engineer_user
        assert result.user_id == engineer_user.user_id
        assert result.email == engineer_user.email
        assert result.roles == engineer_user.roles

    @pytest.mark.asyncio
    async def test_none_user_raises_401(self):
        """Missing authentication raises HTTP 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_401_response_has_correct_error_code(self):
        """401 response includes AUTH_001 error code."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        assert exc_info.value.detail["error_code"] == "AUTH_001"

    @pytest.mark.asyncio
    async def test_401_response_has_descriptive_message(self):
        """401 response includes a human-readable message."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        assert "Authentication required" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_user_with_empty_roles_is_still_authenticated(self, no_role_user):
        """A user with no roles is still considered authenticated."""
        result = await get_user_context(user=no_role_user)

        assert result is no_role_user

    @pytest.mark.asyncio
    async def test_admin_user_context_is_returned(self, admin_user):
        """Admin user context passes through correctly."""
        result = await get_user_context(user=admin_user)

        assert result is admin_user
        assert "admin" in result.roles


# ---------------------------------------------------------------------------
# Requirement 10.2 — RBAC: engineer role permissions
# ---------------------------------------------------------------------------


class TestRequireEngineerRole:
    """Tests for engineer role RBAC (Req 10.2)."""

    @pytest.mark.asyncio
    async def test_engineer_role_is_allowed(self, engineer_user):
        """User with 'engineer' role passes the check."""
        result = await require_engineer_role(user=engineer_user)

        assert result is engineer_user

    @pytest.mark.asyncio
    async def test_admin_role_is_allowed(self, admin_user):
        """User with 'admin' role passes the engineer role check."""
        result = await require_engineer_role(user=admin_user)

        assert result is admin_user

    @pytest.mark.asyncio
    async def test_project_manager_role_is_allowed(self, project_manager_user):
        """User with 'project_manager' role passes the engineer role check."""
        result = await require_engineer_role(user=project_manager_user)

        assert result is project_manager_user

    @pytest.mark.asyncio
    async def test_viewer_role_is_denied(self, viewer_user):
        """User with only 'viewer' role is denied with HTTP 403."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=viewer_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_roles_is_denied(self, no_role_user):
        """User with no roles is denied with HTTP 403."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=no_role_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_403_response_has_correct_error_code(self, viewer_user):
        """403 response includes AUTH_002 error code."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=viewer_user)

        assert exc_info.value.detail["error_code"] == "AUTH_002"

    @pytest.mark.asyncio
    async def test_multi_role_user_with_engineer_is_allowed(self, multi_role_user):
        """User with multiple roles including 'engineer' is allowed."""
        result = await require_engineer_role(user=multi_role_user)

        assert result is multi_role_user

    @pytest.mark.asyncio
    async def test_403_message_lists_required_roles(self, viewer_user):
        """403 response message includes the list of required roles."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=viewer_user)

        message = exc_info.value.detail["message"]
        assert "engineer" in message or "Required roles" in message


# ---------------------------------------------------------------------------
# Requirement 10.3 — Document modification permissions
# ---------------------------------------------------------------------------


class TestRequireDocumentModificationPermission:
    """Tests for document modification permission checks (Req 10.3)."""

    @pytest.mark.asyncio
    async def test_write_designs_permission_is_allowed(self, engineer_user):
        """User with 'write:designs' permission can modify documents."""
        result = await require_document_modification_permission(user=engineer_user)

        assert result is engineer_user

    @pytest.mark.asyncio
    async def test_write_all_permission_is_allowed(self):
        """User with 'write:all' permission can modify documents."""
        user = UserContext(
            user_id=str(uuid4()),
            email="power@example.com",
            roles=["engineer"],
            permissions=["write:all"],
        )

        result = await require_document_modification_permission(user=user)

        assert result is user

    @pytest.mark.asyncio
    async def test_manage_projects_permission_is_allowed(self, project_manager_user):
        """User with 'manage:projects' permission can modify documents."""
        result = await require_document_modification_permission(
            user=project_manager_user
        )

        assert result is project_manager_user

    @pytest.mark.asyncio
    async def test_admin_role_bypasses_permission_check(self, admin_user):
        """Admin role bypasses explicit permission check."""
        result = await require_document_modification_permission(user=admin_user)

        assert result is admin_user

    @pytest.mark.asyncio
    async def test_read_only_permission_is_denied(self):
        """User with only 'read:designs' permission cannot modify documents."""
        user = UserContext(
            user_id=str(uuid4()),
            email="readonly@example.com",
            roles=["engineer"],
            permissions=["read:designs"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_document_modification_permission(user=user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_permissions_is_denied(self):
        """User with no permissions cannot modify documents."""
        user = UserContext(
            user_id=str(uuid4()),
            email="noperm@example.com",
            roles=["engineer"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_document_modification_permission(user=user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_002"

    @pytest.mark.asyncio
    async def test_403_message_mentions_insufficient_permissions(self):
        """403 response message mentions insufficient permissions."""
        user = UserContext(
            user_id=str(uuid4()),
            email="noperm@example.com",
            roles=["engineer"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_document_modification_permission(user=user)

        assert "Insufficient permissions" in exc_info.value.detail["message"]


# ---------------------------------------------------------------------------
# Requirement 10.4 — Project membership verification
# ---------------------------------------------------------------------------


class TestVerifyProjectAccess:
    """Tests for project membership verification (Req 10.4)."""

    @pytest.mark.asyncio
    async def test_admin_bypasses_project_membership_check(self, admin_user):
        """Admin user bypasses project service call entirely."""
        project_id = uuid4()

        with patch("src.api.dependencies.ProjectServiceClient") as mock_client_class:
            result = await verify_project_access(project_id=project_id, user=admin_user)

        assert result is admin_user
        mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_member_with_project_access_is_allowed(self, engineer_user):
        """User who is a project member is allowed access."""
        project_id = uuid4()

        mock_client = MagicMock()
        mock_client.verify_project_membership = AsyncMock(return_value=True)

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            return_value=mock_client,
        ):
            result = await verify_project_access(
                project_id=project_id, user=engineer_user
            )

        assert result is engineer_user

    @pytest.mark.asyncio
    async def test_non_member_is_denied(self, engineer_user):
        """User who is not a project member is denied with HTTP 403."""
        project_id = uuid4()

        mock_client = MagicMock()
        mock_client.verify_project_membership = AsyncMock(return_value=False)

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            return_value=mock_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_project_access(project_id=project_id, user=engineer_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_non_member_403_has_correct_error_code(self, engineer_user):
        """Non-member 403 response includes AUTH_004 error code."""
        project_id = uuid4()

        mock_client = MagicMock()
        mock_client.verify_project_membership = AsyncMock(return_value=False)

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            return_value=mock_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_project_access(project_id=project_id, user=engineer_user)

        assert exc_info.value.detail["error_code"] == "AUTH_004"

    @pytest.mark.asyncio
    async def test_project_service_unavailable_falls_back_to_role_check(
        self, engineer_user
    ):
        """When project service is unavailable, falls back to role-based check."""
        project_id = uuid4()

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            side_effect=Exception("Service unavailable"),
        ):
            # Engineer role should pass the fallback check
            result = await verify_project_access(
                project_id=project_id, user=engineer_user
            )

        assert result is engineer_user

    @pytest.mark.asyncio
    async def test_project_service_unavailable_denies_viewer(self, viewer_user):
        """When project service is unavailable, viewer role is denied."""
        project_id = uuid4()

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            side_effect=Exception("Service unavailable"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_project_access(project_id=project_id, user=viewer_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_project_service_called_with_correct_ids(self, engineer_user):
        """Project service is called with the correct project and user IDs."""
        project_id = uuid4()

        mock_client = MagicMock()
        mock_client.verify_project_membership = AsyncMock(return_value=True)

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            return_value=mock_client,
        ):
            await verify_project_access(project_id=project_id, user=engineer_user)

        mock_client.verify_project_membership.assert_called_once()
        call_kwargs = mock_client.verify_project_membership.call_args.kwargs
        assert call_kwargs["project_id"] == project_id


# ---------------------------------------------------------------------------
# Requirement 10.5 — Permission checks for engineering operations
# ---------------------------------------------------------------------------


class TestRequireCalculationPermission:
    """Tests for calculation operation permission checks (Req 10.5)."""

    def test_engineer_can_perform_calculations(self, engineer_user):
        """Engineer role is allowed to perform calculations."""
        result = require_calculation_permission(user=engineer_user)

        assert result is engineer_user

    def test_admin_can_perform_calculations(self, admin_user):
        """Admin role is allowed to perform calculations."""
        result = require_calculation_permission(user=admin_user)

        assert result is admin_user

    def test_project_manager_can_perform_calculations(self, project_manager_user):
        """Project manager role is allowed to perform calculations."""
        result = require_calculation_permission(user=project_manager_user)

        assert result is project_manager_user

    def test_viewer_cannot_perform_calculations(self, viewer_user):
        """Viewer role is denied calculation access with HTTP 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_calculation_permission(user=viewer_user)

        assert exc_info.value.status_code == 403

    def test_no_role_cannot_perform_calculations(self, no_role_user):
        """User with no roles is denied calculation access."""
        with pytest.raises(HTTPException) as exc_info:
            require_calculation_permission(user=no_role_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_002"


class TestRequireCodeValidationPermission:
    """Tests for code validation permission checks (Req 10.5)."""

    def test_engineer_can_validate_code(self, engineer_user):
        """Engineer role is allowed to perform code validation."""
        result = require_code_validation_permission(user=engineer_user)

        assert result is engineer_user

    def test_admin_can_validate_code(self, admin_user):
        """Admin role is allowed to perform code validation."""
        result = require_code_validation_permission(user=admin_user)

        assert result is admin_user

    def test_project_manager_cannot_validate_code(self, project_manager_user):
        """Project manager role is denied code validation (engineer/admin only)."""
        with pytest.raises(HTTPException) as exc_info:
            require_code_validation_permission(user=project_manager_user)

        assert exc_info.value.status_code == 403

    def test_viewer_cannot_validate_code(self, viewer_user):
        """Viewer role is denied code validation."""
        with pytest.raises(HTTPException) as exc_info:
            require_code_validation_permission(user=viewer_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_002"

    def test_no_role_cannot_validate_code(self, no_role_user):
        """User with no roles is denied code validation."""
        with pytest.raises(HTTPException) as exc_info:
            require_code_validation_permission(user=no_role_user)

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Requirement 10.6 — Appropriate error responses
# ---------------------------------------------------------------------------


class TestErrorResponseFormat:
    """Tests for correct error response format (Req 10.6)."""

    @pytest.mark.asyncio
    async def test_401_response_structure(self):
        """401 response has correct structure with error_code and message."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        detail = exc_info.value.detail
        assert "error_code" in detail
        assert "message" in detail
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_403_response_structure(self, viewer_user):
        """403 response has correct structure with error_code and message."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=viewer_user)

        detail = exc_info.value.detail
        assert "error_code" in detail
        assert "message" in detail
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_auth_error_codes_are_consistent(self):
        """Authentication errors always use AUTH_001 error code."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        assert exc_info.value.detail["error_code"] == "AUTH_001"

    @pytest.mark.asyncio
    async def test_authz_error_codes_are_consistent(self, viewer_user):
        """Authorization errors always use AUTH_002 error code."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=viewer_user)

        assert exc_info.value.detail["error_code"] == "AUTH_002"

    @pytest.mark.asyncio
    async def test_project_access_error_code(self, engineer_user):
        """Project access denial uses AUTH_004 error code."""
        project_id = uuid4()

        mock_client = MagicMock()
        mock_client.verify_project_membership = AsyncMock(return_value=False)

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            return_value=mock_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_project_access(project_id=project_id, user=engineer_user)

        assert exc_info.value.detail["error_code"] == "AUTH_004"

    @pytest.mark.asyncio
    async def test_error_messages_are_not_empty(self, viewer_user):
        """Error messages are non-empty strings."""
        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=viewer_user)

        message = exc_info.value.detail["message"]
        assert isinstance(message, str)
        assert len(message) > 0

    @pytest.mark.asyncio
    async def test_internal_details_not_exposed_in_errors(self):
        """Error responses do not expose internal implementation details."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        detail = exc_info.value.detail
        # Should not contain stack traces or internal paths
        detail_str = str(detail)
        assert "Traceback" not in detail_str
        assert "src/" not in detail_str


# ---------------------------------------------------------------------------
# Optional user context
# ---------------------------------------------------------------------------


class TestGetOptionalUserContext:
    """Tests for optional user context (unauthenticated access)."""

    @pytest.mark.asyncio
    async def test_returns_user_when_present_in_request_state(self, engineer_user):
        """Returns user context when it exists in request state."""
        mock_request = MagicMock()
        mock_request.state.user = engineer_user

        result = await get_optional_user_context(request=mock_request)

        assert result is engineer_user

    @pytest.mark.asyncio
    async def test_returns_none_when_no_user_in_request_state(self):
        """Returns None when no user context in request state."""
        mock_request = MagicMock()
        # Simulate missing attribute
        del mock_request.state.user
        mock_request.state = MagicMock(spec=[])  # No 'user' attribute

        result = await get_optional_user_context(request=mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_does_not_raise_when_unauthenticated(self):
        """Optional context does not raise an exception when unauthenticated."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])

        # Should not raise
        result = await get_optional_user_context(request=mock_request)

        assert result is None


# ---------------------------------------------------------------------------
# Edge cases and boundary conditions
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for auth/authz logic."""

    @pytest.mark.asyncio
    async def test_user_with_multiple_roles_gets_highest_privilege(self):
        """User with both engineer and viewer roles gets engineer access."""
        user = UserContext(
            user_id=str(uuid4()),
            email="multi@example.com",
            roles=["viewer", "engineer"],
            permissions=["read:designs"],
        )

        result = await require_engineer_role(user=user)

        assert result is user

    @pytest.mark.asyncio
    async def test_case_sensitive_role_matching(self):
        """Role matching is case-sensitive — 'Engineer' != 'engineer'."""
        user = UserContext(
            user_id=str(uuid4()),
            email="case@example.com",
            roles=["Engineer"],  # Capital E
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_user_with_only_write_all_permission_can_modify_docs(self):
        """User with 'write:all' but no explicit 'write:designs' can modify docs."""
        user = UserContext(
            user_id=str(uuid4()),
            email="writeall@example.com",
            roles=["engineer"],
            permissions=["write:all"],
        )

        result = await require_document_modification_permission(user=user)

        assert result is user

    def test_calculation_permission_with_multiple_roles_including_engineer(self):
        """User with multiple roles including engineer can perform calculations."""
        user = UserContext(
            user_id=str(uuid4()),
            email="multi@example.com",
            roles=["viewer", "engineer"],
            permissions=[],
        )

        result = require_calculation_permission(user=user)

        assert result is user

    @pytest.mark.asyncio
    async def test_project_access_passes_correct_user_id_type(self, engineer_user):
        """Project service is called with UUID type for user_id."""
        from uuid import UUID

        project_id = uuid4()

        mock_client = AsyncMock()
        mock_client.verify_project_membership.return_value = True

        with patch(
            "src.api.dependencies.ProjectServiceClient",
            return_value=mock_client,
        ):
            await verify_project_access(project_id=project_id, user=engineer_user)

        call_kwargs = mock_client.verify_project_membership.call_args.kwargs
        assert isinstance(call_kwargs["user_id"], UUID)
