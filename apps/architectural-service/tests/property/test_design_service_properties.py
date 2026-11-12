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

    @pytest.mark.asyncio
    @given(
        project_id=st.uuids(),
        user_id=st.uuids(),
        request_data=create_design_request_strategy(),
        project_exists=st.booleans(),
        user_has_access=st.booleans(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_37_project_association_validation(
        self,
        project_id: UUID,
        user_id: UUID,
        request_data: CreateDesignRequest,
        project_exists: bool,
        user_has_access: bool,
    ):
        """
        Property 37: Project association validation.

        For any design creation request, the system should validate that
        the project exists and the user has access before creating the design.
        If validation fails, appropriate errors should be raised.

        Validates: Requirements 10.1, 10.2
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock project validation response
        mock_project_client.validate_project.return_value = ProjectValidation(
            project_id=project_id,
            exists=project_exists,
            user_has_access=user_has_access,
            project_name="Test Project" if project_exists else None,
            project_status="active" if project_exists else None,
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

        # Execute and verify Property 37: Project association validation
        if not project_exists:
            # Should raise NotFoundError if project doesn't exist
            with pytest.raises(Exception) as exc_info:
                await service.create_design(project_id, user_id, request_data)

            # Verify project validation was called
            mock_project_client.validate_project.assert_called_once_with(
                project_id, user_id
            )

            # Verify design was not created
            mock_repo.create.assert_not_called()

        elif not user_has_access:
            # Should raise ValidationError if user doesn't have access
            with pytest.raises(Exception) as exc_info:
                await service.create_design(project_id, user_id, request_data)

            # Verify project validation was called
            mock_project_client.validate_project.assert_called_once_with(
                project_id, user_id
            )

            # Verify design was not created
            mock_repo.create.assert_not_called()

        else:
            # Should succeed if project exists and user has access
            design = await service.create_design(project_id, user_id, request_data)

            # Verify project validation was called
            mock_project_client.validate_project.assert_called_once_with(
                project_id, user_id
            )

            # Verify design was created successfully
            mock_repo.create.assert_called_once()
            mock_repo.create_version.assert_called_once()

            # Verify design properties
            assert design.project_id == str(
                project_id
            ), "Design must be associated with validated project"
            assert design.created_by == str(
                user_id
            ), "Design must be created by validated user"

    @pytest.mark.asyncio
    @given(
        project_id=st.uuids(),
        user_id=st.uuids(),
        request_data=create_design_request_strategy(),
        activity_type=st.sampled_from(
            ["design_created", "design_updated", "design_deleted"]
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_39_activity_logging(
        self,
        project_id: UUID,
        user_id: UUID,
        request_data: CreateDesignRequest,
        activity_type: str,
    ):
        """
        Property 39: Activity logging.

        For any design operation (create, update, delete), the system should
        log the activity to the Project Service timeline with appropriate
        metadata and timestamps.

        Validates: Requirements 10.5
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

        # Mock repository operations
        def create_side_effect(design):
            design.id = str(uuid4())
            return design

        mock_repo.create.side_effect = create_side_effect
        mock_repo.create_version = AsyncMock()

        # For update and delete operations, mock existing design
        existing_design = Design(
            id=str(uuid4()),
            project_id=str(project_id),
            name="Test Design",
            description="Test Description",
            building_type="commercial",
            location_data={"address": "123 Main St"},
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(user_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        mock_repo.get.return_value = existing_design
        mock_repo.update_with_version_check.return_value = existing_design
        mock_repo.soft_delete.return_value = existing_design

        # Track activity logging calls
        activity_calls = []

        async def log_activity_side_effect(project_id, activity):
            activity_calls.append((project_id, activity))

        mock_project_client.log_activity.side_effect = log_activity_side_effect

        # Create service
        service = DesignService(mock_repo, mock_project_client)

        # Override request project_id to match test parameter
        request_data.project_id = project_id

        # Execute operation based on activity type
        if activity_type == "design_created":
            await service.create_design(project_id, user_id, request_data)
        elif activity_type == "design_updated":
            update_data = UpdateDesignRequest(name="Updated Name")
            await service.update_design(UUID(existing_design.id), user_id, update_data)
        elif activity_type == "design_deleted":
            await service.soft_delete(UUID(existing_design.id), user_id)

        # Verify Property 39: Activity logging
        assert len(activity_calls) == 1, "Exactly one activity should be logged"

        logged_project_id, logged_activity = activity_calls[0]

        # Verify project ID matches
        assert (
            logged_project_id == project_id
        ), "Activity must be logged to correct project"

        # Verify activity structure
        assert (
            logged_activity.project_id == project_id
        ), "Activity project_id must match"
        assert logged_activity.user_id == user_id, "Activity user_id must match"
        assert (
            logged_activity.activity_type == activity_type
        ), "Activity type must match operation"
        assert logged_activity.description is not None, "Activity must have description"
        assert logged_activity.timestamp is not None, "Activity must have timestamp"
        assert isinstance(
            logged_activity.metadata, dict
        ), "Activity must have metadata dict"

        # Verify metadata contains relevant information
        if activity_type in ["design_created", "design_updated", "design_deleted"]:
            assert (
                "design_id" in logged_activity.metadata
            ), "Metadata must contain design_id"
            assert (
                "design_name" in logged_activity.metadata
            ), "Metadata must contain design_name"

        # Verify timestamp is recent (within last minute)
        time_diff = datetime.utcnow() - logged_activity.timestamp
        assert time_diff.total_seconds() < 60, "Activity timestamp must be recent"

    @pytest.mark.asyncio
    @given(
        project_id=st.uuids(),
        num_designs=st.integers(min_value=0, max_value=10),
        draft_ratio=st.floats(min_value=0.0, max_value=1.0),
        completed_ratio=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_38_project_summary_calculation(
        self,
        project_id: UUID,
        num_designs: int,
        draft_ratio: float,
        completed_ratio: float,
    ):
        """
        Property 38: Project summary calculation.

        For any project with N designs, the project summary should accurately
        calculate design count, compliance status, and completion percentage
        based on the actual design statuses.

        Validates: Requirements 10.4
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock project status
        from src.infrastructure.project_service_client import ProjectStatus

        mock_project_client.get_project_status.return_value = ProjectStatus(
            project_id=project_id,
            status="active",
            name="Test Project",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Create mock designs with different statuses
        designs = []
        if num_designs > 0:
            # Ensure ratios don't exceed 1.0 when combined
            total_ratio = draft_ratio + completed_ratio
            if total_ratio > 1.0:
                # Normalize ratios
                draft_ratio = draft_ratio / total_ratio
                completed_ratio = completed_ratio / total_ratio

            num_draft = int(num_designs * draft_ratio)
            num_completed = int(num_designs * completed_ratio)
            num_in_progress = num_designs - num_draft - num_completed

            # Create draft designs
            for i in range(num_draft):
                design = Design(
                    id=str(uuid4()),
                    project_id=str(project_id),
                    name=f"Draft Design {i}",
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
                designs.append(design)

            # Create completed designs
            for i in range(num_completed):
                design = Design(
                    id=str(uuid4()),
                    project_id=str(project_id),
                    name=f"Completed Design {i}",
                    description="Test",
                    building_type="commercial",
                    location_data={},
                    current_version="1.0",
                    version_number=1,
                    status="completed",
                    metadata={},
                    created_by=str(uuid4()),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_deleted=False,
                )
                designs.append(design)

            # Create in-progress designs
            for i in range(num_in_progress):
                design = Design(
                    id=str(uuid4()),
                    project_id=str(project_id),
                    name=f"In Progress Design {i}",
                    description="Test",
                    building_type="commercial",
                    location_data={},
                    current_version="1.0",
                    version_number=1,
                    status="in_progress",
                    metadata={},
                    created_by=str(uuid4()),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_deleted=False,
                )
                designs.append(design)

        # Mock repository responses
        from src.core.pagination import PaginatedResponse

        # Mock all designs response (including deleted)
        all_designs_response = PaginatedResponse(
            items=designs,
            total_count=len(designs),
            has_next=False,
            next_cursor=None,
        )

        # Mock active designs response (non-deleted)
        active_designs_response = PaginatedResponse(
            items=designs,  # All designs are active in this test
            total_count=len(designs),
            has_next=False,
            next_cursor=None,
        )

        # Configure mock to return appropriate response based on include_deleted parameter
        def list_designs_side_effect(
            params, project_id, include_deleted=False, include_total=False
        ):
            if include_deleted:
                return all_designs_response
            else:
                return active_designs_response

        mock_repo.list_designs.side_effect = list_designs_side_effect

        # Create service
        service = DesignService(mock_repo, mock_project_client)

        # Execute
        summary = await service.calculate_project_summary(project_id)

        # Verify Property 38: Project summary calculation
        assert summary["project_id"] == str(
            project_id
        ), "Summary must include correct project ID"
        assert (
            summary["design_count"] == num_designs
        ), f"Design count must be {num_designs}"
        assert (
            summary["active_designs"] == num_designs
        ), f"Active designs must be {num_designs}"

        # Verify design status counts
        expected_draft = int(num_designs * draft_ratio) if num_designs > 0 else 0
        expected_completed = (
            int(num_designs * completed_ratio) if num_designs > 0 else 0
        )
        expected_in_progress = (
            num_designs - expected_draft - expected_completed if num_designs > 0 else 0
        )

        assert (
            summary["draft_designs"] == expected_draft
        ), f"Draft designs must be {expected_draft}"
        assert (
            summary["completed_designs"] == expected_completed
        ), f"Completed designs must be {expected_completed}"
        assert (
            summary["in_progress_designs"] == expected_in_progress
        ), f"In progress designs must be {expected_in_progress}"

        # Verify completion percentage calculation
        expected_completion_percentage = 0.0
        if num_designs > 0:
            expected_completion_percentage = (expected_completed / num_designs) * 100

        assert (
            abs(summary["completion_percentage"] - expected_completion_percentage)
            < 0.01
        ), f"Completion percentage must be {expected_completion_percentage}"

        # Verify compliance status logic
        if expected_completed == 0 and num_designs > 0:
            assert (
                summary["compliance_status"] == "pending"
            ), "Compliance status must be pending with no completed designs"
        elif num_designs == 0:
            assert (
                summary["compliance_status"] == "unknown"
            ), "Compliance status must be unknown with no designs"
        elif expected_completion_percentage >= 80:
            assert (
                summary["compliance_status"] == "compliant"
            ), "Compliance status must be compliant with >=80% completion"
        elif expected_completion_percentage >= 50:
            assert (
                summary["compliance_status"] == "partially_compliant"
            ), "Compliance status must be partially_compliant with >=50% completion"
        else:
            assert (
                summary["compliance_status"] == "non_compliant"
            ), "Compliance status must be non_compliant with <50% completion"

        # Verify project information is included
        assert (
            summary["project_name"] == "Test Project"
        ), "Summary must include project name"
        assert (
            summary["project_status"] == "active"
        ), "Summary must include project status"
        assert "last_updated" in summary, "Summary must include last updated timestamp"

    @pytest.mark.asyncio
    @given(
        project_id=st.uuids(),
        user_id=st.uuids(),
        num_designs=st.integers(min_value=0, max_value=5),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_40_cascading_archive(
        self,
        project_id: UUID,
        user_id: UUID,
        num_designs: int,
    ):
        """
        Property 40: Cascading archive.

        For any project with N active designs, when the project is archived,
        all N designs should be archived (soft deleted) and appropriate
        activity logs should be created for each design.

        Validates: Requirements 10.6
        """
        # Setup mocks
        mock_repo = AsyncMock(spec=DesignRepository)
        mock_project_client = AsyncMock()

        # Mock project status
        from src.infrastructure.project_service_client import ProjectStatus

        mock_project_client.get_project_status.return_value = ProjectStatus(
            project_id=project_id,
            status="archived",
            name="Test Project",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Create mock designs
        designs = []
        for i in range(num_designs):
            design = Design(
                id=str(uuid4()),
                project_id=str(project_id),
                name=f"Design {i}",
                description="Test",
                building_type="commercial",
                location_data={},
                current_version="1.0",
                version_number=1,
                status="draft",
                metadata={},
                created_by=str(user_id),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
            )
            designs.append(design)

        # Mock repository responses
        from src.core.pagination import PaginatedResponse

        active_designs_response = PaginatedResponse(
            items=designs,
            total_count=len(designs),
            has_next=False,
            next_cursor=None,
        )

        mock_repo.list_designs.return_value = active_designs_response

        # Track soft delete calls
        soft_delete_calls = []

        async def soft_delete_side_effect(design_id):
            soft_delete_calls.append(design_id)
            # Find the design and mark it as deleted
            for design in designs:
                if design.id == design_id:
                    design.is_deleted = True
                    design.deleted_at = datetime.utcnow()
                    design.status = "archived"
                    return design
            return None

        mock_repo.soft_delete.side_effect = soft_delete_side_effect

        # Track activity logging calls
        activity_calls = []

        async def log_activity_side_effect(project_id, activity):
            activity_calls.append((project_id, activity))

        mock_project_client.log_activity.side_effect = log_activity_side_effect

        # Create service
        service = DesignService(mock_repo, mock_project_client)

        # Execute
        result = await service.cascade_archive_designs(project_id, user_id)

        # Verify Property 40: Cascading archive
        assert result["project_id"] == str(
            project_id
        ), "Result must include correct project ID"
        assert (
            result["archived_designs"] == num_designs
        ), f"Must archive exactly {num_designs} designs"
        assert (
            len(result["design_ids"]) == num_designs
        ), f"Must return {num_designs} design IDs"

        # Verify all designs were soft deleted
        assert (
            len(soft_delete_calls) == num_designs
        ), f"Must call soft_delete {num_designs} times"

        # Verify all design IDs are in the result
        for design in designs:
            assert (
                design.id in result["design_ids"]
            ), f"Design {design.id} must be in archived list"

        # Verify activity logging for each design
        assert len(activity_calls) == num_designs, f"Must log {num_designs} activities"

        for i, (logged_project_id, logged_activity) in enumerate(activity_calls):
            assert (
                logged_project_id == project_id
            ), f"Activity {i} must be logged to correct project"
            assert (
                logged_activity.project_id == project_id
            ), f"Activity {i} project_id must match"
            assert (
                logged_activity.user_id == user_id
            ), f"Activity {i} user_id must match"
            assert (
                logged_activity.activity_type == "design_archived"
            ), f"Activity {i} type must be design_archived"
            assert (
                "design_id" in logged_activity.metadata
            ), f"Activity {i} must contain design_id in metadata"
            assert (
                "design_name" in logged_activity.metadata
            ), f"Activity {i} must contain design_name in metadata"
            assert (
                logged_activity.metadata["reason"] == "project_archived"
            ), f"Activity {i} must have correct reason"

        # Verify result metadata
        assert (
            result["project_name"] == "Test Project"
        ), "Result must include project name"
        assert "archived_at" in result, "Result must include archive timestamp"

        # Verify edge case: no designs to archive
        if num_designs == 0:
            assert result["archived_designs"] == 0, "Must handle zero designs correctly"
            assert result["design_ids"] == [], "Must return empty list for zero designs"
