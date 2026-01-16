"""Unit tests for DesignService."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.api.v1.schemas.base import LocationData
from src.api.v1.schemas.design import CreateDesignRequest, UpdateDesignRequest
from src.api.v1.schemas.enums import BuildingType, DesignStatus
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.infrastructure.project_service_client import ProjectValidation
from src.models.design import Design
from src.repositories.design_repository import DesignRepository
from src.services.design_service import DesignService


class TestDesignServiceUnitTests:
    """Unit tests for DesignService edge cases."""

    @pytest.mark.asyncio
    async def test_create_with_invalid_project(self):
        """Test design creation with invalid project."""
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock project validation to fail - project doesn't exist
        mock_project_client.validate_project.return_value = ProjectValidation(
            project_id=uuid4(),
            exists=False,
            user_has_access=False,
        )

        service = DesignService(mock_repo, mock_project_client)

        # Create request
        request_data = CreateDesignRequest(
            project_id=uuid4(),
            name="Test Design",
            building_type=BuildingType.COMMERCIAL,
            location=LocationData(
                address="123 Main St",
                city="Test City",
                state="Test State",
                country="Test Country",
                postal_code="12345",
                latitude=0.0,
                longitude=0.0,
                jurisdiction="Test Jurisdiction",
            ),
        )

        # Execute and verify
        with pytest.raises(NotFoundError) as exc_info:
            await service.create_design(uuid4(), uuid4(), request_data)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_with_no_access(self):
        """Test design creation when user doesn't have access to project."""
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock project validation - project exists but user has no access
        mock_project_client.validate_project.return_value = ProjectValidation(
            project_id=uuid4(),
            exists=True,
            user_has_access=False,
        )

        service = DesignService(mock_repo, mock_project_client)

        # Create request
        request_data = CreateDesignRequest(
            project_id=uuid4(),
            name="Test Design",
            building_type=BuildingType.COMMERCIAL,
            location=LocationData(
                address="123 Main St",
                city="Test City",
                state="Test State",
                country="Test Country",
                postal_code="12345",
                latitude=0.0,
                longitude=0.0,
                jurisdiction="Test Jurisdiction",
            ),
        )

        # Execute and verify
        with pytest.raises(ValidationError) as exc_info:
            await service.create_design(uuid4(), uuid4(), request_data)

        assert "access" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_with_non_existent_design(self):
        """Test update with non-existent design."""
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock repository to return None (design not found)
        mock_repo.get.return_value = None

        service = DesignService(mock_repo, mock_project_client)

        # Create update request
        update_data = UpdateDesignRequest(name="Updated Design")

        # Execute and verify
        with pytest.raises(NotFoundError) as exc_info:
            await service.update_design(uuid4(), uuid4(), update_data)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_deleted_design(self):
        """Test update of a deleted design."""
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Create deleted design
        design = Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Design",
            description="Test",
            building_type="commercial",
            location_data={},
            current_version="1.0",
            version_number=1,
            status="archived",
            metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=True,  # Design is deleted
            deleted_at=datetime.utcnow(),
        )

        mock_repo.get.return_value = design

        service = DesignService(mock_repo, mock_project_client)

        # Create update request
        update_data = UpdateDesignRequest(name="Updated Design")

        # Execute and verify
        with pytest.raises(ValidationError) as exc_info:
            await service.update_design(uuid4(), uuid4(), update_data)

        assert "deleted" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_with_invalid_version(self):
        """Test get with invalid version."""
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock repository to return None for specific version
        mock_repo.get_by_version.return_value = None

        service = DesignService(mock_repo, mock_project_client)

        # Execute and verify
        with pytest.raises(NotFoundError) as exc_info:
            await service.get_design(uuid4(), version="99.0")

        assert "not found" in str(exc_info.value).lower()
        assert "version" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_concurrent_update_conflicts(self):
        """Test concurrent update conflicts (optimistic locking)."""
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Create existing design
        design = Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Design",
            description="Test",
            building_type="commercial",
            location_data={},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        mock_repo.get.return_value = design

        # Mock update_with_version_check to raise ValueError (version conflict)
        mock_repo.update_with_version_check.side_effect = ValueError(
            "Version conflict: expected 1, got 2"
        )

        service = DesignService(mock_repo, mock_project_client)

        # Create update request
        update_data = UpdateDesignRequest(name="Updated Design")

        # Execute and verify
        with pytest.raises(ConflictError) as exc_info:
            await service.update_design(uuid4(), uuid4(), update_data)

        assert (
            "concurrent" in str(exc_info.value).lower()
            or "conflict" in str(exc_info.value).lower()
        )
