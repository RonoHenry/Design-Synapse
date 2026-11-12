"""Unit tests for API dependencies (authentication and authorization)."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.api.dependencies import (get_user_context,
                                  require_calculation_permission,
                                  require_code_validation_permission,
                                  require_document_modification_permission,
                                  require_engineer_role)

from packages.common.auth.models import UserContext


class TestGetUserContext:
    """Tests for get_user_context dependency."""

    async def test_get_user_context_with_valid_user(self):
        """Test getting user context with valid user."""
        user = UserContext(
            user_id=str(uuid4()),
            email="test@example.com",
            roles=["engineer"],
            permissions=["write:designs"],
        )

        result = await get_user_context(user=user)

        assert result == user
        assert result.user_id == user.user_id
        assert result.email == user.email

    async def test_get_user_context_without_user(self):
        """Test getting user context without user raises exception."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(user=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "AUTH_001"
        assert "Authentication required" in exc_info.value.detail["message"]


class TestRequireEngineerRole:
    """Tests for require_engineer_role dependency."""

    async def test_require_engineer_role_with_engineer(self):
        """Test requiring engineer role with engineer user."""
        user = UserContext(
            user_id=str(uuid4()),
            email="engineer@example.com",
            roles=["engineer"],
            permissions=[],
        )

        result = await require_engineer_role(user=user)

        assert result == user

    async def test_require_engineer_role_with_admin(self):
        """Test requiring engineer role with admin user."""
        user = UserContext(
            user_id=str(uuid4()),
            email="admin@example.com",
            roles=["admin"],
            permissions=[],
        )

        result = await require_engineer_role(user=user)

        assert result == user

    async def test_require_engineer_role_with_project_manager(self):
        """Test requiring engineer role with project manager."""
        user = UserContext(
            user_id=str(uuid4()),
            email="pm@example.com",
            roles=["project_manager"],
            permissions=[],
        )

        result = await require_engineer_role(user=user)

        assert result == user

    async def test_require_engineer_role_without_role(self):
        """Test requiring engineer role without proper role raises exception."""
        user = UserContext(
            user_id=str(uuid4()),
            email="viewer@example.com",
            roles=["viewer"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_002"

    async def test_require_engineer_role_with_no_roles(self):
        """Test requiring engineer role with no roles raises exception."""
        user = UserContext(
            user_id=str(uuid4()),
            email="norole@example.com",
            roles=[],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_engineer_role(user=user)

        assert exc_info.value.status_code == 403


class TestRequireDocumentModificationPermission:
    """Tests for require_document_modification_permission dependency."""

    async def test_require_modification_with_write_designs_permission(self):
        """Test requiring modification permission with write:designs."""
        user = UserContext(
            user_id=str(uuid4()),
            email="engineer@example.com",
            roles=["engineer"],
            permissions=["write:designs"],
        )

        result = await require_document_modification_permission(user=user)

        assert result == user

    async def test_require_modification_with_write_all_permission(self):
        """Test requiring modification permission with write:all."""
        user = UserContext(
            user_id=str(uuid4()),
            email="engineer@example.com",
            roles=["engineer"],
            permissions=["write:all"],
        )

        result = await require_document_modification_permission(user=user)

        assert result == user

    async def test_require_modification_with_manage_projects_permission(self):
        """Test requiring modification permission with manage:projects."""
        user = UserContext(
            user_id=str(uuid4()),
            email="pm@example.com",
            roles=["project_manager"],
            permissions=["manage:projects"],
        )

        result = await require_document_modification_permission(user=user)

        assert result == user

    async def test_require_modification_with_admin_role(self):
        """Test requiring modification permission with admin role."""
        user = UserContext(
            user_id=str(uuid4()),
            email="admin@example.com",
            roles=["admin"],
            permissions=[],
        )

        result = await require_document_modification_permission(user=user)

        assert result == user

    async def test_require_modification_without_permission(self):
        """Test modification permission without permission raises error."""
        user = UserContext(
            user_id=str(uuid4()),
            email="engineer@example.com",
            roles=["engineer"],
            permissions=["read:designs"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_document_modification_permission(user=user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_002"
        assert "Insufficient permissions" in exc_info.value.detail["message"]


class TestRequireCalculationPermission:
    """Tests for require_calculation_permission dependency."""

    def test_require_calculation_with_engineer(self):
        """Test requiring calculation permission with engineer."""
        user = UserContext(
            user_id=str(uuid4()),
            email="engineer@example.com",
            roles=["engineer"],
            permissions=[],
        )

        result = require_calculation_permission(user=user)

        assert result == user

    def test_require_calculation_with_admin(self):
        """Test requiring calculation permission with admin."""
        user = UserContext(
            user_id=str(uuid4()),
            email="admin@example.com",
            roles=["admin"],
            permissions=[],
        )

        result = require_calculation_permission(user=user)

        assert result == user

    def test_require_calculation_with_project_manager(self):
        """Test requiring calculation permission with project manager."""
        user = UserContext(
            user_id=str(uuid4()),
            email="pm@example.com",
            roles=["project_manager"],
            permissions=[],
        )

        result = require_calculation_permission(user=user)

        assert result == user

    def test_require_calculation_without_role(self):
        """Test requiring calculation permission without role raises exception."""
        user = UserContext(
            user_id=str(uuid4()),
            email="viewer@example.com",
            roles=["viewer"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            require_calculation_permission(user=user)

        assert exc_info.value.status_code == 403


class TestRequireCodeValidationPermission:
    """Tests for require_code_validation_permission dependency."""

    def test_require_validation_with_engineer(self):
        """Test requiring validation permission with engineer."""
        user = UserContext(
            user_id=str(uuid4()),
            email="engineer@example.com",
            roles=["engineer"],
            permissions=[],
        )

        result = require_code_validation_permission(user=user)

        assert result == user

    def test_require_validation_with_admin(self):
        """Test requiring validation permission with admin."""
        user = UserContext(
            user_id=str(uuid4()),
            email="admin@example.com",
            roles=["admin"],
            permissions=[],
        )

        result = require_code_validation_permission(user=user)

        assert result == user

    def test_require_validation_with_project_manager(self):
        """Test validation permission with project manager raises error."""
        user = UserContext(
            user_id=str(uuid4()),
            email="pm@example.com",
            roles=["project_manager"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            require_code_validation_permission(user=user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_002"

    def test_require_validation_without_role(self):
        """Test requiring validation permission without role raises exception."""
        user = UserContext(
            user_id=str(uuid4()),
            email="viewer@example.com",
            roles=["viewer"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            require_code_validation_permission(user=user)

        assert exc_info.value.status_code == 403
