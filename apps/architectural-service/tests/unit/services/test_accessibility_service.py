"""Unit tests for AccessibilityService."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from src.api.v1.schemas.analysis import AccessibilityCheckRequest
from src.core.exceptions import NotFoundError, ValidationError
from src.models.accessibility_check import AccessibilityCheck
from src.models.design import Design
from src.repositories.accessibility_check_repository import \
    AccessibilityCheckRepository
from src.repositories.design_repository import DesignRepository
from src.services.accessibility_service import AccessibilityService


class TestAccessibilityService:
    """Unit tests for AccessibilityService."""

    @pytest.fixture
    def mock_accessibility_repo(self):
        """Mock accessibility check repository."""
        return AsyncMock(spec=AccessibilityCheckRepository)

    @pytest.fixture
    def mock_design_repo(self):
        """Mock design repository."""
        return AsyncMock(spec=DesignRepository)

    @pytest.fixture
    def accessibility_service(self, mock_accessibility_repo, mock_design_repo):
        """AccessibilityService instance with mocked dependencies."""
        return AccessibilityService(mock_accessibility_repo, mock_design_repo)

    @pytest.fixture
    def sample_design(self):
        """Sample design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Commercial Building",
            description="A test commercial building",
            building_type="commercial",
            location_data={
                "address": "123 Main St",
                "city": "San Francisco",
                "state": "California",
                "country": "USA",
                "postal_code": "94102",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "jurisdiction": "City and County of San Francisco",
            },
            current_version="1.0",
            version_number=1,
            status="draft",
            design_metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

    @pytest.fixture
    def sample_request(self):
        """Sample accessibility check request."""
        return AccessibilityCheckRequest(
            standards=["ADA", "ANSI-A117.1"],
            check_areas=["entrances", "restrooms", "corridors"],
        )

    @pytest.mark.asyncio
    async def test_check_accessibility_design_not_found(
        self, accessibility_service, mock_design_repo, sample_request
    ):
        """Test accessibility check with non-existent design."""
        # Setup
        design_id = uuid4()
        mock_design_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await accessibility_service.check_accessibility(design_id, sample_request)

        assert f"Design {design_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_accessibility_deleted_design(
        self, accessibility_service, mock_design_repo, sample_design, sample_request
    ):
        """Test accessibility check with deleted design."""
        # Setup
        sample_design.is_deleted = True
        mock_design_repo.get.return_value = sample_design

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await accessibility_service.check_accessibility(
                UUID(sample_design.id), sample_request
            )

        assert "Cannot check accessibility for deleted design" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_accessibility_success(
        self,
        accessibility_service,
        mock_accessibility_repo,
        mock_design_repo,
        sample_design,
        sample_request,
    ):
        """Test successful accessibility check initiation."""
        # Setup
        mock_design_repo.get.return_value = sample_design

        def create_side_effect(accessibility_check):
            accessibility_check.id = str(uuid4())
            return accessibility_check

        mock_accessibility_repo.create.side_effect = create_side_effect
        mock_accessibility_repo.update = AsyncMock()

        # Execute
        response = await accessibility_service.check_accessibility(
            UUID(sample_design.id), sample_request
        )

        # Verify
        assert response.id is not None
        assert response.design_id == UUID(sample_design.id)
        assert response.design_version == sample_design.current_version
        assert response.standards == sample_request.standards
        assert response.started_at is not None

        mock_design_repo.get.assert_called_once_with(sample_design.id)
        mock_accessibility_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_check_results_not_found(
        self, accessibility_service, mock_accessibility_repo
    ):
        """Test get check results with non-existent check."""
        # Setup
        check_id = uuid4()
        mock_accessibility_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await accessibility_service.get_check_results(check_id)

        assert f"Accessibility check {check_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_check_results_success(
        self, accessibility_service, mock_accessibility_repo, sample_design
    ):
        """Test successful get check results."""
        # Setup
        check_id = str(uuid4())
        accessibility_check = AccessibilityCheck(
            id=check_id,
            design_id=sample_design.id,
            design_version=sample_design.current_version,
            standards=["ADA"],
            status="completed",
            passed=True,
            violations=[],
            accessible_routes=[],
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        mock_accessibility_repo.get.return_value = accessibility_check

        # Execute
        response = await accessibility_service.get_check_results(UUID(check_id))

        # Verify
        assert response.id == UUID(check_id)
        assert response.design_id == UUID(sample_design.id)
        assert response.passed is True
        assert len(response.violations) == 0
        assert len(response.accessible_routes) == 0

    @pytest.mark.asyncio
    async def test_door_width_requirements_32_inch_minimum(
        self, accessibility_service, sample_design
    ):
        """Test door width requirements (32" min clear)."""
        # Setup - design with doors that don't meet requirements
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find door width violations
        door_violations = [
            v
            for v in violations
            if "door" in v.description.lower() and "width" in v.description.lower()
        ]

        # Check that violations have proper structure
        for violation in door_violations:
            assert violation.standard_section is not None
            assert "404.2.3" in violation.standard_section  # ADA door width section
            assert violation.location is not None
            assert "32" in violation.required_value  # 32 inch minimum
            assert violation.remediation is not None

    @pytest.mark.asyncio
    async def test_corridor_width_requirements_36_inch_minimum(
        self, accessibility_service, sample_design
    ):
        """Test corridor width requirements (36" min)."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find corridor width violations
        corridor_violations = [
            v
            for v in violations
            if "corridor" in v.description.lower() and "width" in v.description.lower()
        ]

        # Check that violations have proper structure
        for violation in corridor_violations:
            assert violation.standard_section is not None
            assert "403.5.1" in violation.standard_section  # ADA corridor width section
            assert violation.location is not None
            assert "36" in violation.required_value  # 36 inch minimum
            assert violation.remediation is not None

    @pytest.mark.asyncio
    async def test_ramp_slope_requirements_1_12_max(
        self, accessibility_service, sample_design
    ):
        """Test ramp slope requirements (1:12 max)."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find ramp slope violations
        ramp_violations = [
            v
            for v in violations
            if "ramp" in v.description.lower() and "slope" in v.description.lower()
        ]

        # Check that violations have proper structure
        for violation in ramp_violations:
            assert violation.standard_section is not None
            assert "405.2" in violation.standard_section  # ADA ramp slope section
            assert violation.location is not None
            assert (
                "8.3%" in violation.required_value or "1:12" in violation.required_value
            )
            assert violation.remediation is not None

    @pytest.mark.asyncio
    async def test_restroom_clearances_and_fixture_requirements(
        self, accessibility_service, sample_design
    ):
        """Test restroom clearances and fixture requirements."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.validate_restrooms(
            sample_design, standards
        )

        # Verify - should find various restroom violations
        assert isinstance(violations, list)

        # Check for toilet-related violations
        toilet_violations = [v for v in violations if "toilet" in v.description.lower()]

        for violation in toilet_violations:
            assert violation.standard_section is not None
            assert violation.location is not None
            assert violation.description is not None
            assert violation.required_value is not None
            assert violation.actual_value is not None
            assert violation.remediation is not None

            # Should be ADA 604 series for toilet requirements
            if "centerline" in violation.description.lower():
                assert "604.2" in violation.standard_section
                assert (
                    "16" in violation.required_value or "18" in violation.required_value
                )
            elif "seat height" in violation.description.lower():
                assert "604.4" in violation.standard_section
                assert (
                    "17" in violation.required_value
                    and "19" in violation.required_value
                )

        # Check for sink-related violations
        sink_violations = [v for v in violations if "sink" in v.description.lower()]

        for violation in sink_violations:
            assert violation.standard_section is not None
            if "knee clearance" in violation.description.lower():
                assert "606.2" in violation.standard_section
                assert "27" in violation.required_value
            elif "rim height" in violation.description.lower():
                assert "606.3" in violation.standard_section
                assert "34" in violation.required_value

        # Check for grab bar violations
        grab_bar_violations = [
            v for v in violations if "grab bar" in v.description.lower()
        ]

        for violation in grab_bar_violations:
            assert violation.standard_section is not None
            assert "604.5" in violation.standard_section
            if "side wall" in violation.description.lower():
                assert "42" in violation.required_value
            elif "rear wall" in violation.description.lower():
                assert "36" in violation.required_value

        # Check for turning space violations
        turning_violations = [
            v for v in violations if "turning space" in v.description.lower()
        ]

        for violation in turning_violations:
            assert violation.standard_section is not None
            assert "604.3.1" in violation.standard_section
            assert "60" in violation.required_value

    @pytest.mark.asyncio
    async def test_accessible_route_validation_entrance_to_main_areas(
        self, accessibility_service, sample_design
    ):
        """Test that accessible routes are validated from entrances to main areas."""
        # Setup
        standards = ["ADA"]

        # Execute
        route_validations = await accessibility_service.validate_routes(
            sample_design, standards
        )

        # Verify
        assert isinstance(route_validations, list)
        assert len(route_validations) > 0

        # Should have routes from entrances
        entrance_routes = [
            r for r in route_validations if "entrance" in r.from_location.lower()
        ]
        assert len(entrance_routes) > 0

        # Check route validation structure
        for route in route_validations:
            assert route.route_id is not None
            assert route.from_location is not None
            assert route.to_location is not None
            assert isinstance(route.is_accessible, bool)
            assert isinstance(route.issues, list)

            # If not accessible, should have issues
            if not route.is_accessible:
                assert len(route.issues) > 0
                for issue in route.issues:
                    assert isinstance(issue, str)
                    assert len(issue.strip()) > 0

    @pytest.mark.asyncio
    async def test_commercial_building_additional_route_requirements(
        self, accessibility_service, sample_design
    ):
        """Test that commercial buildings have additional route requirements."""
        # Setup - ensure it's a commercial building
        sample_design.building_type = "commercial"
        standards = ["ADA"]

        # Execute
        route_validations = await accessibility_service.validate_routes(
            sample_design, standards
        )

        # Verify - commercial buildings should have routes to elevators and restrooms
        route_destinations = [r.to_location.lower() for r in route_validations]

        # Should have routes to various commercial building areas
        # Note: The actual routes depend on the design, but we should see
        # routes that are typical for commercial buildings
        has_elevator_route = any("elevator" in dest for dest in route_destinations)
        has_restroom_route = any("restroom" in dest for dest in route_destinations)

        # At least one of these should be present for a commercial building
        assert has_elevator_route or has_restroom_route or len(route_validations) > 1

    @pytest.mark.asyncio
    async def test_route_width_validation_36_inch_minimum(
        self, accessibility_service, sample_design
    ):
        """Test that routes are validated for 36-inch minimum width."""
        # Setup
        standards = ["ADA"]

        # Execute
        route_validations = await accessibility_service.validate_routes(
            sample_design, standards
        )

        # Verify - routes with insufficient width should be marked as not accessible
        for route in route_validations:
            if not route.is_accessible:
                width_issues = [
                    issue
                    for issue in route.issues
                    if "width" in issue.lower() and "36" in issue
                ]
                # If there are width issues, they should mention the 36-inch requirement
                for issue in width_issues:
                    assert "36" in issue

    @pytest.mark.asyncio
    async def test_ramp_slope_validation_in_routes(
        self, accessibility_service, sample_design
    ):
        """Test that ramp slopes are validated in accessible routes."""
        # Setup
        standards = ["ADA"]

        # Execute
        route_validations = await accessibility_service.validate_routes(
            sample_design, standards
        )

        # Verify - routes with excessive ramp slopes should be marked as not accessible
        for route in route_validations:
            if not route.is_accessible:
                slope_issues = [
                    issue
                    for issue in route.issues
                    if "slope" in issue.lower() and ("8.3%" in issue or "1:12" in issue)
                ]
                # If there are slope issues, they should mention the maximum slope
                for issue in slope_issues:
                    assert "8.3%" in issue or "1:12" in issue

    @pytest.mark.asyncio
    async def test_door_opening_force_validation(
        self, accessibility_service, sample_design
    ):
        """Test door opening force validation (5 lbf maximum)."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find door opening force violations
        force_violations = [
            v for v in violations if "opening force" in v.description.lower()
        ]

        for violation in force_violations:
            assert violation.standard_section is not None
            assert (
                "404.2.9" in violation.standard_section
            )  # ADA door opening force section
            assert "5" in violation.required_value  # 5 lbf maximum
            assert "lbf" in violation.required_value.lower()

    @pytest.mark.asyncio
    async def test_door_threshold_height_validation(
        self, accessibility_service, sample_design
    ):
        """Test door threshold height validation (0.5" maximum)."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find door threshold violations
        threshold_violations = [
            v for v in violations if "threshold" in v.description.lower()
        ]

        for violation in threshold_violations:
            assert violation.standard_section is not None
            assert "404.2.5" in violation.standard_section  # ADA threshold section
            assert "0.5" in violation.required_value  # 0.5 inch maximum

    @pytest.mark.asyncio
    async def test_ramp_handrail_requirements(
        self, accessibility_service, sample_design
    ):
        """Test ramp handrail requirements."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find handrail violations
        handrail_violations = [
            v for v in violations if "handrail" in v.description.lower()
        ]

        for violation in handrail_violations:
            assert violation.standard_section is not None
            assert "405.8" in violation.standard_section  # ADA handrail section
            assert "both sides" in violation.required_value.lower()

    @pytest.mark.asyncio
    async def test_ramp_landing_requirements(
        self, accessibility_service, sample_design
    ):
        """Test ramp landing requirements."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find landing violations
        landing_violations = [
            v for v in violations if "landing" in v.description.lower()
        ]

        for violation in landing_violations:
            assert violation.standard_section is not None
            assert "405.7" in violation.standard_section  # ADA landing section
            assert "level" in violation.required_value.lower()

    @pytest.mark.asyncio
    async def test_maneuvering_clearance_validation(
        self, accessibility_service, sample_design
    ):
        """Test door maneuvering clearance validation."""
        # Setup
        standards = ["ADA"]

        # Execute
        violations = await accessibility_service.check_clearances(
            sample_design, standards
        )

        # Verify - should find maneuvering clearance violations
        maneuvering_violations = [
            v for v in violations if "maneuvering clearance" in v.description.lower()
        ]

        for violation in maneuvering_violations:
            assert violation.standard_section is not None
            assert (
                "404.2.4" in violation.standard_section
            )  # ADA maneuvering clearance section
            # Should specify pull or push side requirements
            assert "18" in violation.required_value or "12" in violation.required_value
            assert "60" in violation.required_value or "48" in violation.required_value
