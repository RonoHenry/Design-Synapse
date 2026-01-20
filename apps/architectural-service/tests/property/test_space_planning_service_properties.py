"""Property-based tests for SpacePlanningService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.analysis import PlanningConstraints, SpaceRequirement
from src.core.exceptions import ValidationError
from src.models.design import Design
from src.models.space_planning import SpacePlanning
from src.services.space_planning_service import SpacePlanningService


# Test data strategies
@st.composite
def space_requirement_strategy(draw):
    """Generate SpaceRequirement for testing."""
    space_types = [
        "office",
        "conference",
        "lobby",
        "corridor",
        "storage",
        "restroom",
        "kitchen",
        "dining",
        "living_room",
        "bedroom",
        "utility",
    ]

    min_area = draw(st.floats(min_value=50, max_value=1000))
    max_area = draw(
        st.one_of(st.none(), st.floats(min_value=min_area, max_value=min_area * 2))
    )

    return SpaceRequirement(
        space_type=draw(st.sampled_from(space_types)),
        min_area=min_area,
        max_area=max_area,
        adjacencies=draw(st.lists(st.sampled_from(space_types), max_size=3)),
        requirements=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=50),
                max_size=3,
            )
        ),
    )


@st.composite
def unique_space_requirements_strategy(draw):
    """Generate list of unique SpaceRequirement for testing."""
    space_types = [
        "office",
        "conference",
        "lobby",
        "corridor",
        "storage",
        "restroom",
        "kitchen",
        "dining",
        "living_room",
        "bedroom",
        "utility",
    ]

    # Draw a subset of unique space types
    selected_types = draw(
        st.lists(st.sampled_from(space_types), min_size=1, max_size=5, unique=True)
    )

    requirements = []
    for space_type in selected_types:
        min_area = draw(st.floats(min_value=50, max_value=1000))
        max_area = draw(
            st.one_of(st.none(), st.floats(min_value=min_area, max_value=min_area * 2))
        )

        req = SpaceRequirement(
            space_type=space_type,
            min_area=min_area,
            max_area=max_area,
            adjacencies=draw(st.lists(st.sampled_from(space_types), max_size=3)),
            requirements=draw(
                st.dictionaries(
                    st.text(min_size=1, max_size=20),
                    st.text(min_size=1, max_size=50),
                    max_size=3,
                )
            ),
        )
        requirements.append(req)

    return requirements


@st.composite
def planning_constraints_strategy(draw):
    """Generate PlanningConstraints for testing."""
    return PlanningConstraints(
        total_area=draw(
            st.one_of(st.none(), st.floats(min_value=500, max_value=10000))
        ),
        shape_constraints=draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    st.text(min_size=1, max_size=20),
                    st.text(min_size=1, max_size=50),
                    max_size=3,
                ),
            )
        ),
        code_requirements=draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    st.text(min_size=1, max_size=20),
                    st.text(min_size=1, max_size=50),
                    max_size=3,
                ),
            )
        ),
    )


# Property 19: Space planning metric completeness
@given(
    design_id=st.uuids(),
    requirements=unique_space_requirements_strategy(),
    constraints=planning_constraints_strategy(),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_space_planning_metric_completeness(
    design_id, requirements, constraints
):
    """
    **Property 19: Space planning metric completeness**
    *For any* space planning analysis that completes successfully, the results
    should include area efficiency, circulation ratio, and density metrics.
    **Validates: Requirements 5.2**
    """
    # Create fresh mocks for each test
    mock_space_planning_repository = AsyncMock()
    mock_design_repository = AsyncMock()

    space_planning_service = SpacePlanningService(
        space_planning_repository=mock_space_planning_repository,
        design_repository=mock_design_repository,
    )

    # Setup: Mock design exists
    mock_design = Design(
        id=str(design_id),
        project_id=str(uuid4()),
        name="Test Design",
        building_type="residential",
        location_data={},
        is_deleted=False,
    )
    mock_design_repository.get.return_value = mock_design

    # Ensure constraints have sufficient total area
    total_required = sum(req.min_area for req in requirements)
    if constraints.total_area is None or constraints.total_area < total_required:
        constraints.total_area = total_required * 1.5

    # Mock space planning creation and update
    initial_space_planning = SpacePlanning(
        id=str(uuid4()),
        design_id=str(design_id),
        status="in_progress",
        requirements=[req.model_dump() for req in requirements],
        recommendations=[],
        metrics={},
        space_program={},
    )
    mock_space_planning_repository.create.return_value = initial_space_planning

    completed_space_planning = SpacePlanning(
        id=initial_space_planning.id,
        design_id=str(design_id),
        status="completed",
        requirements=[req.model_dump() for req in requirements],
        recommendations=[],
        metrics={
            "area_efficiency": 85.5,
            "circulation_ratio": 0.25,
            "density": 0.005,
        },
        space_program={},
    )
    mock_space_planning_repository.update.return_value = completed_space_planning

    # Execute space planning
    result = await space_planning_service.plan_spaces(
        design_id, requirements, constraints
    )

    # Verify metric completeness
    assert result.status == "completed"
    assert result.metrics is not None

    # All three required metrics should be present
    assert "area_efficiency" in result.metrics
    assert "circulation_ratio" in result.metrics
    assert "density" in result.metrics

    # Metrics should have valid values
    assert isinstance(result.metrics["area_efficiency"], (int, float))
    assert isinstance(result.metrics["circulation_ratio"], (int, float))
    assert isinstance(result.metrics["density"], (int, float))

    # Area efficiency should be a percentage (0-100)
    assert 0 <= result.metrics["area_efficiency"] <= 100

    # Circulation ratio should be non-negative
    assert result.metrics["circulation_ratio"] >= 0

    # Density should be non-negative
    assert result.metrics["density"] >= 0


# Property 20: Space requirement validation
@given(
    design_id=st.uuids(),
    requirements=unique_space_requirements_strategy(),
    constraints=planning_constraints_strategy(),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_space_requirement_validation(
    design_id, requirements, constraints
):
    """
    **Property 20: Space requirement validation**
    *For any* space planning request, if space requirements violate constraints
    (e.g., total required area exceeds available area), the request should be
    rejected with validation errors.
    **Validates: Requirements 5.4**
    """
    # Create fresh mocks for each test
    mock_space_planning_repository = AsyncMock()
    mock_design_repository = AsyncMock()

    space_planning_service = SpacePlanningService(
        space_planning_repository=mock_space_planning_repository,
        design_repository=mock_design_repository,
    )

    # Setup: Mock design exists
    mock_design = Design(
        id=str(design_id),
        project_id=str(uuid4()),
        name="Test Design",
        building_type="residential",
        location_data={},
        is_deleted=False,
    )
    mock_design_repository.get.return_value = mock_design

    # Test case 1: Valid requirements (total area sufficient)
    total_required = sum(req.min_area for req in requirements)
    valid_constraints = PlanningConstraints(
        total_area=total_required * 1.5,  # 50% buffer
        shape_constraints=constraints.shape_constraints,
        code_requirements=constraints.code_requirements,
    )

    # Mock successful creation
    mock_space_planning_repository.create.return_value = SpacePlanning(
        id=str(uuid4()),
        design_id=str(design_id),
        status="in_progress",
        requirements=[req.model_dump() for req in requirements],
    )
    mock_space_planning_repository.update.return_value = SpacePlanning(
        id=str(uuid4()),
        design_id=str(design_id),
        status="completed",
        requirements=[req.model_dump() for req in requirements],
        recommendations=[],
        metrics={"area_efficiency": 80.0, "circulation_ratio": 0.2, "density": 0.01},
        space_program={},
    )

    # Should succeed with valid constraints
    result = await space_planning_service.plan_spaces(
        design_id, requirements, valid_constraints
    )
    assert result is not None

    # Test case 2: Invalid requirements (total area insufficient)
    if total_required > 100:  # Only test if we have meaningful area requirements
        invalid_constraints = PlanningConstraints(
            total_area=total_required * 0.5,  # Insufficient area
            shape_constraints=constraints.shape_constraints,
            code_requirements=constraints.code_requirements,
        )

        # Should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            await space_planning_service.plan_spaces(
                design_id, requirements, invalid_constraints
            )

        assert "Total available area" in str(exc_info.value)
        assert "is less than required area" in str(exc_info.value)


# Property 21: Circulation path validation
@given(
    requirements=unique_space_requirements_strategy(),
    constraints=planning_constraints_strategy(),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_circulation_path_validation(requirements, constraints):
    """
    **Property 21: Circulation path validation**
    *For any* space planning analysis, circulation paths should be validated
    for minimum widths and emergency egress requirements.
    **Validates: Requirements 5.5**
    """
    # Create fresh mocks for each test
    mock_space_planning_repository = AsyncMock()
    mock_design_repository = AsyncMock()

    space_planning_service = SpacePlanningService(
        space_planning_repository=mock_space_planning_repository,
        design_repository=mock_design_repository,
    )

    # Ensure we have sufficient total area
    total_required = sum(req.min_area for req in requirements)
    if constraints.total_area is None or constraints.total_area < total_required:
        constraints.total_area = total_required * 1.5

    # Execute circulation validation
    validation_result = await space_planning_service.validate_circulation(
        requirements, constraints
    )

    # Verify validation completeness
    assert "is_valid" in validation_result
    assert "issues" in validation_result
    assert "egress_paths" in validation_result
    assert "circulation_width" in validation_result
    assert "dead_ends" in validation_result

    # Validation result should be boolean
    assert isinstance(validation_result["is_valid"], bool)

    # Issues should be a list
    assert isinstance(validation_result["issues"], list)

    # Egress paths should be validated
    assert isinstance(validation_result["egress_paths"], list)
    if validation_result["egress_paths"]:
        for egress_path in validation_result["egress_paths"]:
            assert "path_id" in egress_path
            assert "required_width" in egress_path
            assert "is_adequate" in egress_path

    # Dead ends should be identified
    assert isinstance(validation_result["dead_ends"], list)

    # If there are corridor/hallway spaces, they should be checked for width
    corridor_spaces = [
        req for req in requirements if req.space_type in ["corridor", "hallway"]
    ]
    if corridor_spaces and not validation_result["is_valid"]:
        # Should have width-related issues for narrow corridors
        width_issues = [
            issue
            for issue in validation_result["issues"]
            if "narrow" in issue.lower() or "width" in issue.lower()
        ]
        # If corridors exist and validation failed, there should be width issues
        assert len(width_issues) > 0 or len(validation_result["dead_ends"]) > 0


# Property 22: Space program document completeness
@given(
    design_id=st.uuids(),
    requirements=unique_space_requirements_strategy(),
    constraints=planning_constraints_strategy(),
)
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
async def test_property_space_program_document_completeness(
    design_id, requirements, constraints
):
    """
    **Property 22: Space program document completeness**
    *For any* completed space planning analysis, the space program document
    should include areas, relationships, and requirements for all spaces.
    **Validates: Requirements 5.6**
    """
    # Create fresh mocks for each test
    mock_space_planning_repository = AsyncMock()
    mock_design_repository = AsyncMock()

    space_planning_service = SpacePlanningService(
        space_planning_repository=mock_space_planning_repository,
        design_repository=mock_design_repository,
    )

    # Setup: Mock design exists
    mock_design = Design(
        id=str(design_id),
        project_id=str(uuid4()),
        name="Test Design",
        building_type="residential",
        location_data={},
        is_deleted=False,
    )
    mock_design_repository.get.return_value = mock_design

    # Ensure constraints have sufficient total area
    total_required = sum(req.min_area for req in requirements)
    if constraints.total_area is None or constraints.total_area < total_required:
        constraints.total_area = total_required * 1.5

    # Mock space planning creation and completion
    initial_space_planning = SpacePlanning(
        id=str(uuid4()),
        design_id=str(design_id),
        status="in_progress",
        requirements=[req.model_dump() for req in requirements],
    )
    mock_space_planning_repository.create.return_value = initial_space_planning

    # Create complete space program
    space_program = {
        "summary": {
            "total_spaces": len(requirements),
            "total_area": sum(req.min_area * 1.15 for req in requirements),
            "area_efficiency": 85.0,
            "circulation_ratio": 0.25,
        },
        "spaces": [
            {
                "type": req.space_type,
                "required_area": req.min_area,
                "recommended_area": req.min_area * 1.15,
                "adjacencies": req.adjacencies,
                "requirements": req.requirements,
                "location": {"zone": "interior"},
            }
            for req in requirements
        ],
        "relationships": {
            req.space_type: {
                "adjacent_to": req.adjacencies,
                "priority": "high" if len(req.adjacencies) > 2 else "medium",
            }
            for req in requirements
        },
        "requirements": {
            "building_code": "IBC-2021",
            "accessibility": "ADA",
            "egress": "Minimum 2 exits for occupancy > 50",
            "ventilation": "Per mechanical code requirements",
        },
    }

    completed_space_planning = SpacePlanning(
        id=initial_space_planning.id,
        design_id=str(design_id),
        status="completed",
        requirements=[req.model_dump() for req in requirements],
        recommendations=[],
        metrics={
            "area_efficiency": 85.0,
            "circulation_ratio": 0.25,
            "density": 0.005,
        },
        space_program=space_program,
    )
    mock_space_planning_repository.update.return_value = completed_space_planning

    # Execute space planning
    result = await space_planning_service.plan_spaces(
        design_id, requirements, constraints
    )

    # Verify space program completeness
    assert result.status == "completed"
    assert result.space_program is not None

    # Space program should have all required sections
    assert "summary" in result.space_program
    assert "spaces" in result.space_program
    assert "relationships" in result.space_program
    assert "requirements" in result.space_program

    # Summary should include key metrics
    summary = result.space_program["summary"]
    assert "total_spaces" in summary
    assert "total_area" in summary
    assert "area_efficiency" in summary
    assert "circulation_ratio" in summary
    assert summary["total_spaces"] == len(requirements)

    # Spaces section should include all input spaces
    spaces = result.space_program["spaces"]
    assert len(spaces) == len(requirements)

    space_types_in_program = {space["type"] for space in spaces}
    space_types_in_requirements = {req.space_type for req in requirements}
    assert space_types_in_program == space_types_in_requirements

    # Each space should have complete information
    for space in spaces:
        assert "type" in space
        assert "required_area" in space
        assert "recommended_area" in space
        assert "adjacencies" in space
        assert "requirements" in space
        assert "location" in space

    # Relationships should be defined for all spaces
    relationships = result.space_program["relationships"]
    for req in requirements:
        assert req.space_type in relationships
        assert "adjacent_to" in relationships[req.space_type]
        assert "priority" in relationships[req.space_type]

    # Requirements should include building codes
    program_requirements = result.space_program["requirements"]
    assert "building_code" in program_requirements
    assert "accessibility" in program_requirements
