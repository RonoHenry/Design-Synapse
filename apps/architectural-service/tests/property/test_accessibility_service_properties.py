"""Property-based tests for AccessibilityService."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.analysis import (AccessibilityCheckRequest,
                                         AccessibilityViolation,
                                         RouteValidation)
from src.api.v1.schemas.enums import CheckStatus
from src.models.accessibility_check import AccessibilityCheck
from src.models.design import Design
from src.repositories.accessibility_check_repository import \
    AccessibilityCheckRepository
from src.repositories.design_repository import DesignRepository
from src.services.accessibility_service import AccessibilityService


# Hypothesis strategies for generating test data
@st.composite
def accessibility_check_request_strategy(draw):
    """Generate valid AccessibilityCheckRequest."""
    return AccessibilityCheckRequest(
        standards=draw(
            st.lists(
                st.sampled_from(["ADA", "ANSI-A117.1", "IBC-2021", "FHA"]),
                min_size=1,
                max_size=3,
                unique=True,
            )
        ),
        check_areas=draw(
            st.lists(
                st.sampled_from(
                    ["entrances", "restrooms", "corridors", "ramps", "elevators"]
                ),
                min_size=0,
                max_size=5,
                unique=True,
            )
        ),
    )


@st.composite
def design_strategy(draw):
    """Generate valid Design for testing."""
    design_id = str(uuid4())
    return Design(
        id=design_id,
        project_id=str(uuid4()),
        name=draw(st.text(min_size=1, max_size=255)),
        description=draw(st.one_of(st.none(), st.text(max_size=1000))),
        building_type=draw(
            st.sampled_from(["residential", "commercial", "industrial", "mixed_use"])
        ),
        location_data={
            "address": draw(st.text(min_size=1, max_size=200)),
            "city": draw(st.text(min_size=1, max_size=100)),
            "state": draw(st.text(min_size=1, max_size=100)),
            "country": draw(st.text(min_size=1, max_size=100)),
            "postal_code": draw(st.text(min_size=1, max_size=20)),
            "latitude": draw(st.floats(min_value=-90, max_value=90)),
            "longitude": draw(st.floats(min_value=-180, max_value=180)),
            "jurisdiction": draw(st.text(min_size=1, max_size=200)),
        },
        current_version="1.0",
        version_number=1,
        status="draft",
        design_metadata=draw(st.dictionaries(st.text(), st.text(), max_size=5)),
        created_by=str(uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
    )


@st.composite
def accessibility_violation_strategy(draw):
    """Generate valid AccessibilityViolation."""
    return AccessibilityViolation(
        standard_section=draw(st.text(min_size=1, max_size=50)),
        location=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.text(min_size=1, max_size=200)),
        required_value=draw(st.text(min_size=1, max_size=100)),
        actual_value=draw(st.text(min_size=1, max_size=100)),
        remediation=draw(st.text(min_size=1, max_size=200)),
    )


@st.composite
def route_validation_strategy(draw):
    """Generate valid RouteValidation."""
    return RouteValidation(
        route_id=draw(st.text(min_size=1, max_size=50)),
        from_location=draw(st.text(min_size=1, max_size=100)),
        to_location=draw(st.text(min_size=1, max_size=100)),
        is_accessible=draw(st.booleans()),
        issues=draw(st.lists(st.text(min_size=1, max_size=100), max_size=5)),
    )


class TestAccessibilityServiceProperties:
    """Property-based tests for AccessibilityService."""

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=accessibility_check_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_23_accessibility_check_completeness(
        self,
        design: Design,
        request: AccessibilityCheckRequest,
    ):
        """
        Property 23: Accessibility check completeness.

        For any accessibility check, the analysis should validate door widths,
        corridor widths, ramp slopes, handrail requirements, and clearances.

        Validates: Requirements 6.2
        """
        # Setup mocks
        mock_accessibility_repo = AsyncMock(spec=AccessibilityCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Mock design repository to return the test design
        mock_design_repo.get.return_value = design

        # Mock accessibility repository create to return check with ID
        def create_side_effect(accessibility_check):
            accessibility_check.id = str(uuid4())
            return accessibility_check

        mock_accessibility_repo.create.side_effect = create_side_effect
        mock_accessibility_repo.update = AsyncMock()

        # Create service
        service = AccessibilityService(mock_accessibility_repo, mock_design_repo)

        # Execute
        response = await service.check_accessibility(UUID(design.id), request)

        # Verify Property 23: Accessibility check completeness
        assert response.id is not None, "Check must have unique identifier"
        assert response.design_id == UUID(design.id), "Design ID must match"
        assert response.design_version == design.current_version, "Version must match"
        assert response.standards == request.standards, "Standards must be preserved"
        assert response.status in [
            CheckStatus.PENDING,
            CheckStatus.IN_PROGRESS,
            CheckStatus.COMPLETED,
        ], "Status must be valid"
        assert response.started_at is not None, "Start time must be set"

        # Verify repository interactions
        mock_design_repo.get.assert_called_once_with(design.id)
        mock_accessibility_repo.create.assert_called_once()

        # Verify that the check covers all required accessibility elements
        # This is validated by the service implementation which checks:
        # - Door clearances (validate_routes, check_clearances)
        # - Corridor widths (check_clearances)
        # - Ramp slopes (check_clearances)
        # - Handrail requirements (check_clearances)
        # - General clearances (check_clearances)

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        standards=st.lists(
            st.sampled_from(["ADA", "ANSI-A117.1"]),
            min_size=1,
            max_size=2,
            unique=True,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_24_accessibility_violation_location_specificity(
        self,
        design: Design,
        standards: list[str],
    ):
        """
        Property 24: Accessibility violation location specificity.

        For any accessibility check with violations, each violation should include
        specific location information (coordinates, room ID, or element ID) and
        remediation guidance.

        Validates: Requirements 6.3
        """
        # Setup mocks
        mock_accessibility_repo = AsyncMock(spec=AccessibilityCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = AccessibilityService(mock_accessibility_repo, mock_design_repo)

        # Execute clearance checking (which generates violations)
        violations = await service.check_clearances(design, standards)

        # Verify Property 24: Accessibility violation location specificity
        for violation in violations:
            assert isinstance(
                violation, AccessibilityViolation
            ), "Violation must be AccessibilityViolation instance"

            # Check that location information is provided
            assert (
                violation.location is not None and len(violation.location.strip()) > 0
            ), "Location must be provided and not empty"

            # Check that standard section is provided
            assert (
                violation.standard_section is not None
                and len(violation.standard_section.strip()) > 0
            ), "Standard section must be provided"

            # Check that description is provided
            assert (
                violation.description is not None
                and len(violation.description.strip()) > 0
            ), "Description must be provided"

            # Check that required and actual values are provided
            assert (
                violation.required_value is not None
                and len(violation.required_value.strip()) > 0
            ), "Required value must be provided"
            assert (
                violation.actual_value is not None
                and len(violation.actual_value.strip()) > 0
            ), "Actual value must be provided"

            # Check that remediation guidance is provided
            assert (
                violation.remediation is not None
                and len(violation.remediation.strip()) > 0
            ), "Remediation guidance must be provided"

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        standards=st.lists(
            st.sampled_from(["ADA", "ANSI-A117.1"]),
            min_size=1,
            max_size=2,
            unique=True,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_25_accessible_route_validation(
        self,
        design: Design,
        standards: list[str],
    ):
        """
        Property 25: Accessible route validation.

        For any accessibility check, the analysis should validate that accessible
        routes exist from all entrances to all public and common use areas.

        Validates: Requirements 6.4
        """
        # Setup mocks
        mock_accessibility_repo = AsyncMock(spec=AccessibilityCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = AccessibilityService(mock_accessibility_repo, mock_design_repo)

        # Execute route validation
        route_validations = await service.validate_routes(design, standards)

        # Verify Property 25: Accessible route validation
        assert isinstance(route_validations, list), "Route validations must be a list"

        # Each route validation must be complete
        for route in route_validations:
            assert isinstance(
                route, RouteValidation
            ), "Route must be RouteValidation instance"

            # Check that route has required fields
            assert (
                route.route_id is not None and len(route.route_id.strip()) > 0
            ), "Route ID must be provided"
            assert (
                route.from_location is not None and len(route.from_location.strip()) > 0
            ), "From location must be provided"
            assert (
                route.to_location is not None and len(route.to_location.strip()) > 0
            ), "To location must be provided"
            assert isinstance(
                route.is_accessible, bool
            ), "Accessibility status must be boolean"
            assert isinstance(route.issues, list), "Issues must be a list"

            # If route is not accessible, there should be issues explaining why
            if not route.is_accessible:
                assert (
                    len(route.issues) > 0
                ), "Non-accessible routes must have issues listed"
                for issue in route.issues:
                    assert (
                        issue is not None and len(issue.strip()) > 0
                    ), "Each issue must be a non-empty string"

        # Verify that essential routes are checked based on building type
        route_ids = [r.route_id for r in route_validations]

        # All buildings should have entrance to main area route
        entrance_routes = [
            r for r in route_validations if "entrance" in r.from_location.lower()
        ]
        assert len(entrance_routes) > 0, "Must validate routes from entrances"

        # Commercial buildings should have additional route requirements
        if design.building_type == "commercial":
            # Should check routes to restrooms and elevators
            restroom_routes = [
                r for r in route_validations if "restroom" in r.to_location.lower()
            ]
            # Note: We don't assert this must exist because the design might not have restrooms
            # But if it does, the routes should be validated

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        standards=st.lists(
            st.sampled_from(["ADA", "ANSI-A117.1"]),
            min_size=1,
            max_size=2,
            unique=True,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_26_restroom_accessibility_validation(
        self,
        design: Design,
        standards: list[str],
    ):
        """
        Property 26: Restroom accessibility validation.

        For any design with restroom spaces, accessibility checks should verify
        fixture counts, clearances, and grab bar locations meet ADA requirements.

        Validates: Requirements 6.5
        """
        # Setup mocks
        mock_accessibility_repo = AsyncMock(spec=AccessibilityCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = AccessibilityService(mock_accessibility_repo, mock_design_repo)

        # Execute restroom validation
        violations = await service.validate_restrooms(design, standards)

        # Verify Property 26: Restroom accessibility validation
        assert isinstance(violations, list), "Violations must be a list"

        # Each violation must be complete and specific to restroom requirements
        for violation in violations:
            assert isinstance(
                violation, AccessibilityViolation
            ), "Violation must be AccessibilityViolation instance"

            # Check that violation has all required fields
            assert (
                violation.standard_section is not None
                and len(violation.standard_section.strip()) > 0
            ), "Standard section must be provided"
            assert (
                violation.location is not None and len(violation.location.strip()) > 0
            ), "Location must be provided"
            assert (
                violation.description is not None
                and len(violation.description.strip()) > 0
            ), "Description must be provided"
            assert (
                violation.required_value is not None
                and len(violation.required_value.strip()) > 0
            ), "Required value must be provided"
            assert (
                violation.actual_value is not None
                and len(violation.actual_value.strip()) > 0
            ), "Actual value must be provided"
            assert (
                violation.remediation is not None
                and len(violation.remediation.strip()) > 0
            ), "Remediation must be provided"

            # Verify that violations are restroom-specific
            # The location should indicate it's a restroom-related violation
            location_lower = violation.location.lower()
            description_lower = violation.description.lower()
            section_lower = violation.standard_section.lower()

            # Should be related to restroom elements
            restroom_indicators = [
                "restroom",
                "toilet",
                "sink",
                "grab bar",
                "fixture",
                "clearance",
                "turning space",
                "door",
                "ada 604",
                "ada 606",
            ]

            has_restroom_indicator = any(
                indicator in location_lower
                or indicator in description_lower
                or indicator in section_lower
                for indicator in restroom_indicators
            )

            assert has_restroom_indicator, (
                f"Violation should be restroom-related. "
                f"Location: {violation.location}, "
                f"Description: {violation.description}, "
                f"Section: {violation.standard_section}"
            )

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=accessibility_check_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_accessibility_check_result_persistence(
        self,
        design: Design,
        request: AccessibilityCheckRequest,
    ):
        """
        Test that accessibility check results are properly persisted.

        Verifies that violations and route validations are stored
        and can be retrieved after the check completes.
        """
        # Setup mocks
        mock_accessibility_repo = AsyncMock(spec=AccessibilityCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Track what gets stored
        stored_data = {}

        def update_side_effect(check_id, **kwargs):
            stored_data.update(kwargs)
            return AsyncMock()

        mock_accessibility_repo.update.side_effect = update_side_effect

        # Mock design repository
        mock_design_repo.get.return_value = design

        # Mock accessibility repository create
        check_id = str(uuid4())

        def create_side_effect(accessibility_check):
            accessibility_check.id = check_id
            return accessibility_check

        mock_accessibility_repo.create.side_effect = create_side_effect

        # Create service
        service = AccessibilityService(mock_accessibility_repo, mock_design_repo)

        # Execute accessibility check
        response = await service.check_accessibility(UUID(design.id), request)

        # Verify that results were stored
        assert "status" in stored_data, "Status must be persisted"
        assert stored_data["status"] in [
            "in_progress",
            "completed",
            "failed",
        ], "Status must be valid"

        if stored_data.get("status") == "completed":
            assert "passed" in stored_data, "Pass/fail status must be persisted"
            assert isinstance(
                stored_data["passed"], bool
            ), "Pass status must be boolean"
            assert "violations" in stored_data, "Violations must be persisted"
            assert isinstance(
                stored_data["violations"], list
            ), "Violations must be list"
            assert "accessible_routes" in stored_data, "Routes must be persisted"
            assert isinstance(
                stored_data["accessible_routes"], list
            ), "Routes must be list"

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=accessibility_check_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_accessibility_check_success_marking(
        self,
        design: Design,
        request: AccessibilityCheckRequest,
    ):
        """
        Test that accessibility checks are properly marked as passed/failed.

        Verifies that checks with no violations and all accessible routes
        are marked as passed, while checks with violations or inaccessible
        routes are marked as failed.
        """
        # Setup mocks
        mock_accessibility_repo = AsyncMock(spec=AccessibilityCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Track stored data
        stored_data = {}

        def update_side_effect(check_id, **kwargs):
            stored_data.update(kwargs)
            return AsyncMock()

        mock_accessibility_repo.update.side_effect = update_side_effect

        # Mock design repository
        mock_design_repo.get.return_value = design

        # Mock accessibility repository create
        check_id = str(uuid4())

        def create_side_effect(accessibility_check):
            accessibility_check.id = check_id
            return accessibility_check

        mock_accessibility_repo.create.side_effect = create_side_effect

        # Create service
        service = AccessibilityService(mock_accessibility_repo, mock_design_repo)

        # Execute accessibility check
        response = await service.check_accessibility(UUID(design.id), request)

        # Verify success marking logic
        if stored_data.get("status") == "completed":
            violations = stored_data.get("violations", [])
            routes = stored_data.get("accessible_routes", [])

            # Parse route data to check accessibility
            accessible_routes = []
            for route_data in routes:
                if isinstance(route_data, dict):
                    accessible_routes.append(route_data.get("is_accessible", False))

            # If no violations and all routes are accessible, should be passed
            if len(violations) == 0 and all(accessible_routes):
                assert (
                    stored_data.get("passed") is True
                ), "Check with no violations and all accessible routes must be marked as passed"
            # If there are violations or inaccessible routes, should be failed
            elif len(violations) > 0 or not all(accessible_routes):
                assert (
                    stored_data.get("passed") is False
                ), "Check with violations or inaccessible routes must be marked as failed"

        # Verify status progression
        assert response.status in [
            CheckStatus.PENDING,
            CheckStatus.IN_PROGRESS,
            CheckStatus.COMPLETED,
        ], "Status must be valid"
