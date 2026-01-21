"""Unit tests for SpacePlanningService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.api.v1.schemas.analysis import PlanningConstraints, SpaceRequirement
from src.core.exceptions import NotFoundError, ValidationError
from src.models.design import Design
from src.models.space_planning import SpacePlanning
from src.services.space_planning_service import SpacePlanningService


class TestSpacePlanningService:
    """Unit tests for SpacePlanningService."""

    @pytest.fixture
    def mock_space_planning_repository(self):
        """Mock space planning repository."""
        repo = AsyncMock()
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.get = AsyncMock()
        return repo

    @pytest.fixture
    def mock_design_repository(self):
        """Mock design repository."""
        repo = AsyncMock()
        repo.get = AsyncMock()
        return repo

    @pytest.fixture
    def space_planning_service(
        self, mock_space_planning_repository, mock_design_repository
    ):
        """SpacePlanningService instance with mocked dependencies."""
        return SpacePlanningService(
            space_planning_repository=mock_space_planning_repository,
            design_repository=mock_design_repository,
        )

    @pytest.fixture
    def sample_design(self):
        """Sample design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="residential",
            location_data={},
            is_deleted=False,
        )

    @pytest.fixture
    def office_requirements(self):
        """Office building space requirements."""
        return [
            SpaceRequirement(
                space_type="office",
                min_area=150.0,
                max_area=200.0,
                adjacencies=["corridor", "lobby"],
                requirements={"natural_light": True, "privacy": "high"},
            ),
            SpaceRequirement(
                space_type="conference",
                min_area=300.0,
                max_area=400.0,
                adjacencies=["office", "lobby"],
                requirements={"av_equipment": True, "soundproofing": True},
            ),
            SpaceRequirement(
                space_type="lobby",
                min_area=200.0,
                adjacencies=["office", "conference", "corridor"],
                requirements={"reception_desk": True},
            ),
            SpaceRequirement(
                space_type="corridor",
                min_area=100.0,
                adjacencies=["office", "lobby"],
                requirements={"width": "6 feet minimum"},
            ),
        ]

    @pytest.fixture
    def residential_requirements(self):
        """Residential space requirements."""
        return [
            SpaceRequirement(
                space_type="living_room",
                min_area=250.0,
                max_area=350.0,
                adjacencies=["kitchen", "dining"],
                requirements={"natural_light": True, "fireplace": True},
            ),
            SpaceRequirement(
                space_type="kitchen",
                min_area=120.0,
                max_area=180.0,
                adjacencies=["living_room", "dining"],
                requirements={"island": True, "pantry": True},
            ),
            SpaceRequirement(
                space_type="dining",
                min_area=100.0,
                adjacencies=["living_room", "kitchen"],
                requirements={"seating": "8 people"},
            ),
            SpaceRequirement(
                space_type="bedroom",
                min_area=120.0,
                max_area=200.0,
                adjacencies=["corridor"],
                requirements={"closet": True, "en_suite": False},
            ),
        ]

    @pytest.fixture
    def basic_constraints(self):
        """Basic planning constraints."""
        return PlanningConstraints(
            total_area=1000.0,
            shape_constraints={"aspect_ratio": "1.5:1"},
            code_requirements={"egress_width": "44 inches"},
        )

    async def test_layout_recommendations_office_building(
        self,
        space_planning_service,
        mock_design_repository,
        mock_space_planning_repository,
        sample_design,
        office_requirements,
        basic_constraints,
    ):
        """
        Test layout recommendations for office building types.
        Requirements: 5.1, 5.2
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Mock space planning creation and completion
        initial_planning = SpacePlanning(
            id=str(uuid4()),
            design_id=sample_design.id,
            status="in_progress",
            requirements=[req.model_dump() for req in office_requirements],
        )
        mock_space_planning_repository.create.return_value = initial_planning

        completed_planning = SpacePlanning(
            id=initial_planning.id,
            design_id=sample_design.id,
            status="completed",
            requirements=[req.model_dump() for req in office_requirements],
            recommendations=[
                {
                    "space_type": "conference",
                    "recommended_area": 345.0,
                    "location": {"zone": "perimeter", "orientation": "south"},
                    "rationale": "placed on perimeter for natural light; adjacent to office, lobby as required",
                },
                {
                    "space_type": "office",
                    "recommended_area": 172.5,
                    "location": {"zone": "perimeter", "orientation": "south"},
                    "rationale": "placed on perimeter for natural light; adjacent to corridor, lobby as required",
                },
                {
                    "space_type": "lobby",
                    "recommended_area": 230.0,
                    "location": {"zone": "circulation"},
                    "rationale": "positioned for optimal circulation flow; adjacent to office, conference, corridor as required",
                },
                {
                    "space_type": "corridor",
                    "recommended_area": 115.0,
                    "location": {"zone": "circulation"},
                    "rationale": "positioned for optimal circulation flow; adjacent to office, lobby as required",
                },
            ],
            metrics={
                "area_efficiency": 86.25,
                "circulation_ratio": 0.23,
                "density": 0.008,
            },
            space_program={},
        )
        mock_space_planning_repository.update.return_value = completed_planning

        # Execute space planning
        result = await space_planning_service.plan_spaces(
            uuid4(), office_requirements, basic_constraints
        )

        # Verify recommendations for office building
        assert result.status == "completed"
        assert len(result.recommendations) == 4

        # Check conference room recommendation (largest space first)
        conference_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "conference"
        )
        assert conference_rec["recommended_area"] > 300.0  # Buffer added
        assert conference_rec["location"]["zone"] == "perimeter"  # Natural light
        assert "natural light" in conference_rec["rationale"]

        # Check office recommendation
        office_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "office"
        )
        assert office_rec["recommended_area"] > 150.0  # Buffer added
        assert office_rec["location"]["zone"] == "perimeter"  # Natural light

        # Check circulation spaces
        lobby_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "lobby"
        )
        assert lobby_rec["location"]["zone"] == "circulation"

        corridor_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "corridor"
        )
        assert corridor_rec["location"]["zone"] == "circulation"

    async def test_layout_recommendations_residential_building(
        self,
        space_planning_service,
        mock_design_repository,
        mock_space_planning_repository,
        sample_design,
        residential_requirements,
        basic_constraints,
    ):
        """
        Test layout recommendations for residential building types.
        Requirements: 5.1, 5.2
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Adjust constraints for residential requirements
        total_required = sum(req.min_area for req in residential_requirements)
        residential_constraints = PlanningConstraints(
            total_area=total_required * 1.3,
            shape_constraints=basic_constraints.shape_constraints,
            code_requirements=basic_constraints.code_requirements,
        )

        # Mock space planning creation and completion
        initial_planning = SpacePlanning(
            id=str(uuid4()),
            design_id=sample_design.id,
            status="in_progress",
            requirements=[req.model_dump() for req in residential_requirements],
        )
        mock_space_planning_repository.create.return_value = initial_planning

        completed_planning = SpacePlanning(
            id=initial_planning.id,
            design_id=sample_design.id,
            status="completed",
            requirements=[req.model_dump() for req in residential_requirements],
            recommendations=[
                {
                    "space_type": "living_room",
                    "recommended_area": 287.5,
                    "location": {"zone": "perimeter", "orientation": "south"},
                    "rationale": "placed on perimeter for natural light; adjacent to kitchen, dining as required",
                },
                {
                    "space_type": "kitchen",
                    "recommended_area": 138.0,
                    "location": {"zone": "service"},
                    "rationale": "located in service zone for utility access; adjacent to living_room, dining as required",
                },
                {
                    "space_type": "bedroom",
                    "recommended_area": 138.0,
                    "location": {"zone": "perimeter", "orientation": "south"},
                    "rationale": "placed on perimeter for natural light; adjacent to corridor as required",
                },
                {
                    "space_type": "dining",
                    "recommended_area": 115.0,
                    "location": {"zone": "interior"},
                    "rationale": "standard placement; adjacent to living_room, kitchen as required",
                },
            ],
            metrics={
                "area_efficiency": 85.0,
                "circulation_ratio": 0.25,
                "density": 0.006,
            },
            space_program={},
        )
        mock_space_planning_repository.update.return_value = completed_planning

        # Execute space planning
        result = await space_planning_service.plan_spaces(
            uuid4(), residential_requirements, residential_constraints
        )

        # Verify recommendations for residential building
        assert result.status == "completed"
        assert len(result.recommendations) == 4

        # Check living room recommendation (largest space first)
        living_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "living_room"
        )
        assert living_rec["recommended_area"] > 250.0  # Buffer added
        assert living_rec["location"]["zone"] == "perimeter"  # Natural light

        # Check kitchen recommendation
        kitchen_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "kitchen"
        )
        assert kitchen_rec["recommended_area"] > 120.0  # Buffer added
        assert kitchen_rec["location"]["zone"] == "service"  # Utility access

        # Check bedroom recommendation
        bedroom_rec = next(
            rec for rec in result.recommendations if rec["space_type"] == "bedroom"
        )
        assert bedroom_rec["recommended_area"] > 120.0  # Buffer added
        assert bedroom_rec["location"]["zone"] == "perimeter"  # Natural light

    async def test_metric_calculations_edge_cases(self, space_planning_service):
        """
        Test metric calculations with edge cases.
        Requirements: 5.2
        """
        # Test case 1: Very small spaces
        small_requirements = [
            SpaceRequirement(
                space_type="utility",
                min_area=25.0,
                adjacencies=[],
                requirements={},
            ),
        ]
        small_constraints = PlanningConstraints(total_area=50.0)

        metrics = await space_planning_service.calculate_metrics(
            small_requirements, small_constraints
        )

        assert 0 <= metrics.area_efficiency <= 100
        assert metrics.circulation_ratio >= 0
        assert metrics.density >= 0

        # Test case 2: Very large spaces
        large_requirements = [
            SpaceRequirement(
                space_type="warehouse",
                min_area=5000.0,
                adjacencies=[],
                requirements={},
            ),
        ]
        large_constraints = PlanningConstraints(total_area=6000.0)

        metrics = await space_planning_service.calculate_metrics(
            large_requirements, large_constraints
        )

        assert 0 <= metrics.area_efficiency <= 100
        assert metrics.circulation_ratio >= 0
        assert metrics.density >= 0

        # Test case 3: Perfect fit (100% efficiency)
        perfect_requirements = [
            SpaceRequirement(
                space_type="office",
                min_area=100.0,
                adjacencies=[],
                requirements={},
            ),
        ]
        perfect_constraints = PlanningConstraints(total_area=100.0)

        metrics = await space_planning_service.calculate_metrics(
            perfect_requirements, perfect_constraints
        )

        assert metrics.area_efficiency == 100.0
        assert metrics.circulation_ratio == 0.0  # No circulation space
        assert metrics.density >= 0

    async def test_circulation_validation_complex_layouts(self, space_planning_service):
        """
        Test circulation validation with complex layouts.
        Requirements: 5.5
        """
        # Test case 1: Layout with narrow corridors
        narrow_corridor_requirements = [
            SpaceRequirement(
                space_type="corridor",
                min_area=30.0,  # Too narrow (less than 44 inches wide)
                adjacencies=["office"],
                requirements={},
            ),
            SpaceRequirement(
                space_type="office",
                min_area=150.0,
                adjacencies=["corridor"],
                requirements={},
            ),
        ]
        constraints = PlanningConstraints(total_area=200.0)

        validation = await space_planning_service.validate_circulation(
            narrow_corridor_requirements, constraints
        )

        assert validation["is_valid"] is False
        assert len(validation["issues"]) > 0
        assert any("narrow" in issue.lower() for issue in validation["issues"])

        # Test case 2: Layout with dead ends
        dead_end_requirements = [
            SpaceRequirement(
                space_type="office",
                min_area=150.0,
                adjacencies=[],  # No adjacencies = potential dead end
                requirements={},
            ),
            SpaceRequirement(
                space_type="storage",
                min_area=50.0,
                adjacencies=[],  # Storage is allowed to have no adjacencies
                requirements={},
            ),
        ]

        validation = await space_planning_service.validate_circulation(
            dead_end_requirements, constraints
        )

        # Office should be flagged as dead end, storage should not
        assert "office" in validation["dead_ends"]
        assert "storage" not in validation["dead_ends"]

        # Test case 3: Valid circulation layout
        valid_requirements = [
            SpaceRequirement(
                space_type="corridor",
                min_area=80.0,  # Wide enough
                adjacencies=["office", "lobby"],
                requirements={},
            ),
            SpaceRequirement(
                space_type="office",
                min_area=150.0,
                adjacencies=["corridor"],
                requirements={},
            ),
            SpaceRequirement(
                space_type="lobby",
                min_area=100.0,
                adjacencies=["corridor"],
                requirements={},
            ),
        ]

        validation = await space_planning_service.validate_circulation(
            valid_requirements, constraints
        )

        assert validation["is_valid"] is True
        assert len(validation["issues"]) == 0
        assert len(validation["dead_ends"]) == 0

        # Should have egress path information
        assert len(validation["egress_paths"]) > 0
        egress_path = validation["egress_paths"][0]
        assert "required_width" in egress_path
        assert "is_adequate" in egress_path

    async def test_design_not_found_error(
        self,
        space_planning_service,
        mock_design_repository,
        office_requirements,
        basic_constraints,
    ):
        """
        Test error handling when design doesn't exist.
        Requirements: 5.1
        """
        # Setup: Mock design not found
        mock_design_repository.get.return_value = None

        design_id = uuid4()

        # Should raise NotFoundError
        with pytest.raises(NotFoundError) as exc_info:
            await space_planning_service.plan_spaces(
                design_id, office_requirements, basic_constraints
            )

        assert f"Design {design_id} not found" in str(exc_info.value)

    async def test_deleted_design_error(
        self,
        space_planning_service,
        mock_design_repository,
        office_requirements,
        basic_constraints,
    ):
        """
        Test error handling when design is deleted.
        Requirements: 5.1
        """
        # Setup: Mock deleted design
        deleted_design = Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Deleted Design",
            building_type="residential",
            location_data={},
            is_deleted=True,  # Design is deleted
        )
        mock_design_repository.get.return_value = deleted_design

        design_id = uuid4()

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await space_planning_service.plan_spaces(
                design_id, office_requirements, basic_constraints
            )

        assert "Cannot plan spaces for deleted design" in str(exc_info.value)

    async def test_insufficient_area_validation(
        self,
        space_planning_service,
        mock_design_repository,
        sample_design,
        office_requirements,
    ):
        """
        Test validation when total area is insufficient.
        Requirements: 5.4
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Create constraints with insufficient area
        total_required = sum(req.min_area for req in office_requirements)
        insufficient_constraints = PlanningConstraints(
            total_area=total_required * 0.5  # Only 50% of required area
        )

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await space_planning_service.plan_spaces(
                uuid4(), office_requirements, insufficient_constraints
            )

        assert "Total available area" in str(exc_info.value)
        assert "is less than required area" in str(exc_info.value)

    async def test_duplicate_space_types_validation(
        self,
        space_planning_service,
        mock_design_repository,
        sample_design,
        basic_constraints,
    ):
        """
        Test validation when duplicate space types are provided.
        Requirements: 5.4
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Create requirements with duplicate space types
        duplicate_requirements = [
            SpaceRequirement(
                space_type="office",
                min_area=150.0,
                adjacencies=[],
                requirements={},
            ),
            SpaceRequirement(
                space_type="office",  # Duplicate
                min_area=200.0,
                adjacencies=[],
                requirements={},
            ),
        ]

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await space_planning_service.plan_spaces(
                uuid4(), duplicate_requirements, basic_constraints
            )

        assert "Duplicate space types found" in str(exc_info.value)

    async def test_invalid_area_constraints_validation(
        self,
        space_planning_service,
        mock_design_repository,
        sample_design,
        basic_constraints,
    ):
        """
        Test validation when max area is less than min area.
        Requirements: 5.4
        """
        # Setup: Mock design exists
        mock_design_repository.get.return_value = sample_design

        # Create requirements with invalid area constraints
        invalid_requirements = [
            SpaceRequirement(
                space_type="office",
                min_area=200.0,
                max_area=150.0,  # Max less than min
                adjacencies=[],
                requirements={},
            ),
        ]

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await space_planning_service.plan_spaces(
                uuid4(), invalid_requirements, basic_constraints
            )

        assert "Maximum area" in str(exc_info.value)
        assert "cannot be less than minimum area" in str(exc_info.value)
