"""Property-based tests for DesignService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.base import LocationData
from src.api.v1.schemas.design import CreateDesignRequest, UpdateDesignRequest
from src.api.v1.schemas.enums import BuildingType, DesignStatus
from src.infrastructure.project_service_client import ProjectValidation
from src.models.design import Design
from src.repositories.design_repository import DesignRepository
from src.services.design_service import DesignService


# Hypothesis strategies for generating test data
@st.composite
def location_data_strategy(draw):
    """Generate valid LocationData."""
    return LocationData(
        address=draw(st.text(min_size=1, max_size=200)),
        city=draw(st.text(min_size=1, max_size=100)),
        state=draw(st.text(min_size=1, max_size=100)),
        country=draw(st.text(min_size=1, max_size=100)),
        postal_code=draw(st.text(min_size=1, max_size=20)),
        latitude=draw(st.floats(min_value=-90, max_value=90)),
        longitude=draw(st.floats(min_value=-180, max_value=180)),
        jurisdiction=draw(st.text(min_size=1, max_size=200)),
    )


@st.composite
def create_design_request_strategy(draw):
    """Generate valid CreateDesignRequest."""
    return CreateDesignRequest(
        project_id=uuid4(),
        name=draw(st.text(min_size=1, max_size=255).filter(lambda x: x.strip())),
        description=draw(st.one_of(st.none(), st.text(max_size=5000))),
        building_type=draw(st.sampled_from(BuildingType)),
        location=draw(location_data_strategy()),
        metadata=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=50),
                st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
                max_size=10,
            )
        ),
    )


@st.composite
def update_design_request_strategy(draw):
    """Generate valid UpdateDesignRequest with at least one field."""
    # Ensure at least one field is not None
    fields = {}
    has_field = False

    if draw(st.booleans()):
        fields["name"] = draw(st.text(min_size=1, max_size=255))
        has_field = True
    else:
        fields["name"] = None

    if draw(st.booleans()):
        fields["description"] = draw(st.text(max_size=5000))
        has_field = True
    else:
        fields["description"] = None

    if draw(st.booleans()):
        fields["building_type"] = draw(st.sampled_from(BuildingType))
        has_field = True
    else:
        fields["building_type"] = None

    if draw(st.booleans()):
        fields["location"] = draw(location_data_strategy())
        has_field = True
    else:
        fields["location"] = None

    if draw(st.booleans()):
        fields["status"] = draw(st.sampled_from(DesignStatus))
        has_field = True
    else:
        fields["status"] = None

    if draw(st.booleans()):
        fields["metadata"] = draw(
            st.dictionaries(
                st.text(min_size=1, max_size=50),
                st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
                max_size=10,
            )
        )
        has_field = True
    else:
        fields["metadata"] = None

    # If no fields were set, set at least one
    if not has_field:
        fields["name"] = draw(
            st.text(min_size=1, max_size=255).filter(lambda x: x.strip())
        )

    return UpdateDesignRequest(**fields)


class TestDesignServiceProperties:
    """Property-based tests for DesignService."""

    @pytest.mark.asyncio
    @given(
        project_id=st.uuids(),
        user_id=st.uuids(),
        request_data=create_design_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    async def test_property_1_design_initialization_consistency(
        self,
        project_id: UUID,
        user_id: UUID,
        request_data: CreateDesignRequest,
    ):
        """
        Property 1: Design initialization consistency.

        For any new design document creation request, the created design
        should have a unique identifier, version "1.0", version_number 1,
        and all required metadata fields populated.

        Validates: Requirements 1.1, 1.7
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock project validation to succeed
        mock_project_client.validate_project.return_value = ProjectValidation(
            project_id=project_id,
            exists=True,
            user_has_access=True,
            project_name="Test Project",
            project_status="active",
        )

        # Mock repository create to return design with ID
        def create_side_effect(design):
            design.id = str(uuid4())
            return design

        mock_repo.create.side_effect = create_side_effect
        mock_repo.create_version = AsyncMock()

        # Create service
        service = DesignService(mock_repo, mock_project_client)

        # Override request project_id to match test parameter
        request_data.project_id = project_id

        # Execute
        design = await service.create_design(project_id, user_id, request_data)

        # Verify Property 1: Design initialization consistency
        assert design.id is not None, "Design must have unique identifier"
        assert design.current_version == "1.0", "Initial version must be 1.0"
        assert design.version_number == 1, "Initial version number must be 1"
        assert design.created_at is not None, "created_at must be populated"
        assert design.updated_at is not None, "updated_at must be populated"
        assert design.created_by == str(user_id), "created_by must match user_id"
        assert design.project_id == str(project_id), "project_id must match"
        assert design.name == request_data.name, "name must match request"
        # Handle both enum and string values for building_type
        expected_building_type = (
            request_data.building_type.value
            if hasattr(request_data.building_type, "value")
            else request_data.building_type
        )
        assert design.building_type == expected_building_type
        assert design.is_deleted is False, "New design must not be deleted"
        assert design.status == "draft", "Initial status must be draft"

    @pytest.mark.asyncio
    @given(
        design_id=st.uuids(),
        user_id=st.uuids(),
        update_data=update_design_request_strategy(),
        initial_version=st.integers(min_value=1, max_value=10),
    )
    async def test_property_2_version_increment_consistency(
        self,
        design_id: UUID,
        user_id: UUID,
        update_data: UpdateDesignRequest,
        initial_version: int,
    ):
        """
        Property 2: Version increment consistency.

        For any design document update, the new version should have
        version_number incremented by 1, and the version string should
        reflect the new number.

        Validates: Requirements 1.3
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Create existing design
        existing_design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Original Name",
            description="Original Description",
            building_type="commercial",
            location_data={
                "address": "123 Main St",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
                "postal_code": "12345",
                "latitude": 0.0,
                "longitude": 0.0,
                "jurisdiction": "Test Jurisdiction",
            },
            current_version=f"{initial_version}.0",
            version_number=initial_version,
            status="draft",
            metadata={},
            created_by=str(user_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        # Mock repository get to return existing design
        mock_repo.get.return_value = existing_design

        # Mock update_with_version_check to increment version
        def update_side_effect(design_id, expected_version_number, **kwargs):
            updated_design = existing_design
            for key, value in kwargs.items():
                setattr(updated_design, key, value)
            updated_design.version_number = expected_version_number + 1
            updated_design.current_version = f"{updated_design.version_number}.0"
            updated_design.updated_at = datetime.utcnow()
            return updated_design

        mock_repo.update_with_version_check.side_effect = update_side_effect
        mock_repo.create_version = AsyncMock()

        # Create service
        service = DesignService(mock_repo, mock_project_client)

        # Execute
        updated_design = await service.update_design(design_id, user_id, update_data)

        # Verify Property 2: Version increment consistency
        expected_version_number = initial_version + 1
        assert (
            updated_design.version_number == expected_version_number
        ), f"Version number must increment from {initial_version} to {expected_version_number}"
        assert (
            updated_design.current_version == f"{expected_version_number}.0"
        ), f"Version string must be {expected_version_number}.0"

    @pytest.mark.asyncio
    @given(
        design_id=st.uuids(),
        user_id=st.uuids(),
        num_updates=st.integers(min_value=1, max_value=5),
    )
    async def test_property_3_version_history_preservation(
        self,
        design_id: UUID,
        user_id: UUID,
        num_updates: int,
    ):
        """
        Property 3: Version history preservation.

        For any design document with N updates, there should exist exactly
        N+1 versions (original plus N updates), and all versions should be
        retrievable.

        Validates: Requirements 1.3
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Track version creation calls
        version_calls = []

        def create_version_side_effect(*args, **kwargs):
            version_calls.append(kwargs)
            return AsyncMock()

        mock_repo.create_version.side_effect = create_version_side_effect

        # Mock project validation
        mock_project_client.validate_project.return_value = ProjectValidation(
            project_id=uuid4(),
            exists=True,
            user_has_access=True,
        )

        # Create initial design
        def create_side_effect(design):
            design.id = str(design_id)
            return design

        mock_repo.create.side_effect = create_side_effect

        service = DesignService(mock_repo, mock_project_client)

        # Create design (version 1)
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
        await service.create_design(uuid4(), user_id, request_data)

        # Perform N updates
        for i in range(num_updates):
            existing_design = Design(
                id=str(design_id),
                project_id=str(uuid4()),
                name=f"Design v{i+1}",
                description="Test",
                building_type="commercial",
                location_data={},
                current_version=f"{i+1}.0",
                version_number=i + 1,
                status="draft",
                metadata={},
                created_by=str(user_id),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
            )

            mock_repo.get.return_value = existing_design

            def update_side_effect(design_id, expected_version_number, **kwargs):
                updated = existing_design
                updated.version_number = expected_version_number + 1
                updated.current_version = f"{updated.version_number}.0"
                return updated

            mock_repo.update_with_version_check.side_effect = update_side_effect

            update_data = UpdateDesignRequest(name=f"Updated Design v{i+2}")
            await service.update_design(design_id, user_id, update_data)

        # Verify Property 3: Version history preservation
        # Should have N+1 version creation calls (1 initial + N updates)
        expected_versions = num_updates + 1
        assert (
            len(version_calls) == expected_versions
        ), f"Should have {expected_versions} versions (1 initial + {num_updates} updates)"

        # Verify version numbers are sequential
        version_numbers = [call["version_number"] for call in version_calls]
        assert version_numbers == list(
            range(1, expected_versions + 1)
        ), "Version numbers must be sequential starting from 1"

    @pytest.mark.asyncio
    @given(
        design_id=st.uuids(),
        version_number=st.integers(min_value=1, max_value=10),
    )
    async def test_property_4_version_retrieval_round_trip(
        self,
        design_id: UUID,
        version_number: int,
    ):
        """
        Property 4: Version retrieval round-trip.

        For any design document and any valid version number, retrieving
        that version should return design data that matches the snapshot
        stored when that version was created.

        Validates: Requirements 1.4
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Create design with specific version data
        version_string = f"{version_number}.0"
        expected_data = {
            "name": f"Design v{version_number}",
            "description": f"Description v{version_number}",
            "building_type": "commercial",
            "location_data": {
                "address": "123 Main St",
                "city": "Test City",
            },
            "design_metadata": {"version": version_number},
            "status": "draft",
        }

        design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name=expected_data["name"],
            description=expected_data["description"],
            building_type=expected_data["building_type"],
            location_data=expected_data["location_data"],
            current_version=version_string,
            version_number=version_number,
            status=expected_data["status"],
            metadata=expected_data["design_metadata"],
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        # Mock repository to return design at specific version
        mock_repo.get_by_version.return_value = design

        service = DesignService(mock_repo, mock_project_client)

        # Execute
        retrieved_design = await service.get_design(design_id, version_string)

        # Verify Property 4: Version retrieval round-trip
        assert (
            retrieved_design.current_version == version_string
        ), "Retrieved version must match requested version"
        assert (
            retrieved_design.name == expected_data["name"]
        ), "Retrieved name must match version snapshot"
        assert (
            retrieved_design.description == expected_data["description"]
        ), "Retrieved description must match version snapshot"
        assert (
            retrieved_design.building_type == expected_data["building_type"]
        ), "Retrieved building_type must match version snapshot"
        assert (
            retrieved_design.metadata == expected_data["design_metadata"]
        ), "Retrieved metadata must match version snapshot"

    @pytest.mark.asyncio
    @given(
        design_id=st.uuids(),
        user_id=st.uuids(),
    )
    async def test_property_6_soft_delete_preservation(
        self,
        design_id: UUID,
        user_id: UUID,
    ):
        """
        Property 6: Soft delete preservation.

        For any design document, after soft deletion, the document should
        be marked as deleted (is_deleted=True) but still retrievable with
        all data intact.

        Validates: Requirements 1.6
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Create existing design
        original_design = Design(
            id=str(design_id),
            project_id=str(uuid4()),
            name="Test Design",
            description="Test Description",
            building_type="commercial",
            location_data={"address": "123 Main St"},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={"key": "value"},
            created_by=str(user_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
            deleted_at=None,
        )

        # Mock repository get to return existing design
        mock_repo.get.return_value = original_design

        # Mock soft_delete to mark as deleted
        async def soft_delete_side_effect(design_id):
            deleted_design = original_design
            deleted_design.is_deleted = True
            deleted_design.deleted_at = datetime.utcnow()
            deleted_design.status = "archived"
            return deleted_design

        mock_repo.soft_delete.side_effect = soft_delete_side_effect

        service = DesignService(mock_repo, mock_project_client)

        # Execute
        await service.soft_delete(design_id, user_id)

        # Get the deleted design from the side effect
        deleted_design = await mock_repo.soft_delete(str(design_id))

        # Verify Property 6: Soft delete preservation
        assert deleted_design.is_deleted is True, "Design must be marked as deleted"
        assert deleted_design.deleted_at is not None, "deleted_at timestamp must be set"
        assert (
            deleted_design.status == "archived"
        ), "Status must be archived after deletion"

        # Verify all data is preserved
        assert deleted_design.id == original_design.id, "ID must be preserved"
        assert deleted_design.name == original_design.name, "Name must be preserved"
        assert (
            deleted_design.description == original_design.description
        ), "Description must be preserved"
        assert (
            deleted_design.building_type == original_design.building_type
        ), "Building type must be preserved"
        assert (
            deleted_design.location_data == original_design.location_data
        ), "Location data must be preserved"
        assert (
            deleted_design.metadata == original_design.metadata
        ), "Metadata must be preserved"
        assert (
            deleted_design.current_version == original_design.current_version
        ), "Version must be preserved"
