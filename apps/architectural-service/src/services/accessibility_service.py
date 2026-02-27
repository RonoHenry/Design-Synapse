"""Accessibility checking service for ADA and accessibility standards compliance."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.analysis import (AccessibilityCheckRequest,
                                         AccessibilityCheckResponse,
                                         AccessibilityViolation,
                                         RouteValidation)
from src.api.v1.schemas.enums import CheckStatus
from src.core.exceptions import NotFoundError, ValidationError
from src.models.accessibility_check import AccessibilityCheck
from src.models.design import Design
from src.repositories.accessibility_check_repository import \
    AccessibilityCheckRepository
from src.repositories.design_repository import DesignRepository

logger = logging.getLogger(__name__)


class AccessibilityService:
    """
    Service for accessibility compliance checking.

    Handles accessibility check initiation, route validation,
    clearance checking, and restroom compliance validation.
    """

    def __init__(
        self,
        accessibility_repository: AccessibilityCheckRepository,
        design_repository: DesignRepository,
    ):
        """
        Initialize AccessibilityService.

        Args:
            accessibility_repository: Repository for accessibility check data
            design_repository: Repository for design data
        """
        self.accessibility_repository = accessibility_repository
        self.design_repository = design_repository

    async def check_accessibility(
        self,
        design_id: UUID,
        request: AccessibilityCheckRequest,
    ) -> AccessibilityCheckResponse:
        """
        Initiate accessibility compliance check for a design.

        Validates design exists, creates accessibility check record,
        and starts asynchronous accessibility validation process.

        Args:
            design_id: Design ID to check accessibility for
            request: Accessibility check request parameters

        Returns:
            AccessibilityCheckResponse with check details

        Raises:
            NotFoundError: If design doesn't exist
            ValidationError: If design is not in valid state for checking
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found",
                details={"design_id": str(design_id)},
            )

        # Check if design is deleted
        if design.is_deleted:
            raise ValidationError(
                f"Cannot check accessibility for deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Create accessibility check record
        accessibility_check = AccessibilityCheck(
            id=str(uuid4()),
            design_id=str(design_id),
            design_version=design.current_version,
            standards=request.standards,
            status="pending",
            passed=None,
            violations=[],
            accessible_routes=[],
            started_at=datetime.utcnow(),
        )

        # Save accessibility check
        accessibility_check = await self.accessibility_repository.create(
            accessibility_check
        )

        logger.info(
            f"Created accessibility check {accessibility_check.id} for design {design_id}"
        )

        # Start asynchronous accessibility validation
        # In a real implementation, this would be queued as a background task
        try:
            await self._perform_accessibility_validation(
                accessibility_check, design, request.check_areas
            )
        except Exception as e:
            logger.error(f"Accessibility validation failed: {e}")
            # Update status to failed
            accessibility_check.status = "failed"
            accessibility_check.completed_at = datetime.utcnow()
            await self.accessibility_repository.update(
                accessibility_check.id, status="failed", completed_at=datetime.utcnow()
            )

        # Return response
        return self._build_accessibility_response(accessibility_check)

    async def validate_routes(
        self,
        design: Design,
        standards: List[str],
    ) -> List[RouteValidation]:
        """
        Validate accessible routes in the design.

        Checks that accessible routes exist from all entrances to
        all public and common use areas.

        Args:
            design: Design to validate routes for
            standards: List of accessibility standards to check against

        Returns:
            List of route validations with accessibility status

        Raises:
            ValidationError: If route validation fails
        """
        route_validations = []

        try:
            # Extract route information from design metadata
            routes = self._extract_routes_from_design(design)

            # Validate each route for accessibility compliance
            for route in routes:
                route_validation = await self._validate_single_route(route, standards)
                route_validations.append(route_validation)

            # Check for required routes that may be missing
            required_routes = self._identify_required_routes(design)
            for required_route in required_routes:
                if not any(
                    r.route_id == required_route["id"] for r in route_validations
                ):
                    # Add missing route as non-accessible
                    route_validations.append(
                        RouteValidation(
                            route_id=required_route["id"],
                            from_location=required_route["from"],
                            to_location=required_route["to"],
                            is_accessible=False,
                            issues=["Route not provided in design"],
                        )
                    )

        except Exception as e:
            logger.error(f"Route validation failed: {e}")
            raise ValidationError(
                f"Failed to validate accessible routes: {str(e)}",
                details={"error": str(e)},
            )

        return route_validations

    async def check_clearances(
        self,
        design: Design,
        standards: List[str],
    ) -> List[AccessibilityViolation]:
        """
        Check door widths, corridor widths, and other clearance requirements.

        Validates clearances against ADA and other accessibility standards.

        Args:
            design: Design to check clearances for
            standards: List of accessibility standards to check against

        Returns:
            List of clearance violations found

        Raises:
            ValidationError: If clearance checking fails
        """
        violations = []

        try:
            # Extract clearance data from design
            clearances = self._extract_clearances_from_design(design)

            # Check door clearances
            door_violations = await self._check_door_clearances(
                clearances.get("doors", []), standards
            )
            violations.extend(door_violations)

            # Check corridor clearances
            corridor_violations = await self._check_corridor_clearances(
                clearances.get("corridors", []), standards
            )
            violations.extend(corridor_violations)

            # Check ramp clearances
            ramp_violations = await self._check_ramp_clearances(
                clearances.get("ramps", []), standards
            )
            violations.extend(ramp_violations)

            # Check maneuvering clearances
            maneuvering_violations = await self._check_maneuvering_clearances(
                clearances.get("maneuvering", []), standards
            )
            violations.extend(maneuvering_violations)

        except Exception as e:
            logger.error(f"Clearance checking failed: {e}")
            raise ValidationError(
                f"Failed to check clearances: {str(e)}",
                details={"error": str(e)},
            )

        return violations

    async def validate_restrooms(
        self,
        design: Design,
        standards: List[str],
    ) -> List[AccessibilityViolation]:
        """
        Validate restroom accessibility compliance.

        Checks restroom clearances, fixture requirements, and grab bar locations
        against ADA and other accessibility standards.

        Args:
            design: Design to validate restrooms for
            standards: List of accessibility standards to check against

        Returns:
            List of restroom accessibility violations

        Raises:
            ValidationError: If restroom validation fails
        """
        violations = []

        try:
            # Extract restroom data from design
            restrooms = self._extract_restrooms_from_design(design)

            for restroom in restrooms:
                # Check fixture clearances
                fixture_violations = await self._check_restroom_fixture_clearances(
                    restroom, standards
                )
                violations.extend(fixture_violations)

                # Check grab bar requirements
                grab_bar_violations = await self._check_grab_bar_requirements(
                    restroom, standards
                )
                violations.extend(grab_bar_violations)

                # Check door clearances
                door_violations = await self._check_restroom_door_clearances(
                    restroom, standards
                )
                violations.extend(door_violations)

                # Check turning space
                turning_violations = await self._check_restroom_turning_space(
                    restroom, standards
                )
                violations.extend(turning_violations)

        except Exception as e:
            logger.error(f"Restroom validation failed: {e}")
            raise ValidationError(
                f"Failed to validate restrooms: {str(e)}",
                details={"error": str(e)},
            )

        return violations

    async def get_check_results(self, check_id: UUID) -> AccessibilityCheckResponse:
        """
        Retrieve accessibility check results.

        Args:
            check_id: Accessibility check ID

        Returns:
            AccessibilityCheckResponse with current check status and results

        Raises:
            NotFoundError: If accessibility check doesn't exist
        """
        accessibility_check = await self.accessibility_repository.get(str(check_id))
        if accessibility_check is None:
            raise NotFoundError(
                f"Accessibility check {check_id} not found",
                details={"check_id": str(check_id)},
            )

        return self._build_accessibility_response(accessibility_check)

    async def _perform_accessibility_validation(
        self,
        accessibility_check: AccessibilityCheck,
        design: Design,
        check_areas: List[str],
    ) -> None:
        """
        Perform the actual accessibility validation.

        This is the core validation logic that checks the design
        against all specified accessibility standards.

        Args:
            accessibility_check: Accessibility check record to update
            design: Design to validate
            check_areas: Specific areas to check
        """
        try:
            # Update status to in_progress
            accessibility_check.status = "in_progress"
            await self.accessibility_repository.update(
                accessibility_check.id, status="in_progress"
            )

            all_violations = []
            all_routes = []

            # Validate accessible routes
            route_validations = await self.validate_routes(
                design, accessibility_check.standards
            )
            all_routes.extend(route_validations)

            # Check clearances
            clearance_violations = await self.check_clearances(
                design, accessibility_check.standards
            )
            all_violations.extend(clearance_violations)

            # Validate restrooms
            restroom_violations = await self.validate_restrooms(
                design, accessibility_check.standards
            )
            all_violations.extend(restroom_violations)

            # Convert to JSON-serializable format
            violations_data = [v.model_dump() for v in all_violations]
            routes_data = [r.model_dump() for r in all_routes]

            # Determine overall pass/fail status
            passed = len(all_violations) == 0 and all(
                r.is_accessible for r in all_routes
            )

            # Update accessibility check with results
            accessibility_check.status = "completed"
            accessibility_check.passed = passed
            accessibility_check.violations = violations_data
            accessibility_check.accessible_routes = routes_data
            accessibility_check.completed_at = datetime.utcnow()

            await self.accessibility_repository.update(
                accessibility_check.id,
                status="completed",
                passed=passed,
                violations=violations_data,
                accessible_routes=routes_data,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Completed accessibility check {accessibility_check.id}: "
                f"passed={passed}, violations={len(all_violations)}, "
                f"accessible_routes={len([r for r in all_routes if r.is_accessible])}"
            )

        except Exception as e:
            logger.error(f"Accessibility validation failed: {e}")
            # Update status to failed
            await self.accessibility_repository.update(
                accessibility_check.id,
                status="failed",
                completed_at=datetime.utcnow(),
            )
            raise

    def _extract_routes_from_design(self, design: Design) -> List[Dict]:
        """
        Extract route information from design metadata.

        Args:
            design: Design to extract routes from

        Returns:
            List of route dictionaries
        """
        # In a real implementation, this would parse the design data
        # and extract actual route information from drawings/models
        routes = []

        # Example routes based on building type
        if design.building_type == "commercial":
            routes.extend(
                [
                    {
                        "id": "main_entrance_to_elevator",
                        "from": "Main Entrance",
                        "to": "Elevator Lobby",
                        "width": 44,  # inches
                        "length": 120,  # inches
                        "has_ramps": False,
                        "slope": 0.0,
                    },
                    {
                        "id": "elevator_to_restroom",
                        "from": "Elevator Lobby",
                        "to": "Public Restroom",
                        "width": 36,  # inches
                        "length": 80,  # inches
                        "has_ramps": False,
                        "slope": 0.0,
                    },
                ]
            )
        elif design.building_type == "residential":
            routes.extend(
                [
                    {
                        "id": "entrance_to_living",
                        "from": "Main Entrance",
                        "to": "Living Room",
                        "width": 32,  # inches
                        "length": 60,  # inches
                        "has_ramps": True,
                        "slope": 0.08,  # 8% slope
                    },
                ]
            )

        return routes

    def _identify_required_routes(self, design: Design) -> List[Dict]:
        """
        Identify required accessible routes based on design and building type.

        Args:
            design: Design to identify required routes for

        Returns:
            List of required route dictionaries
        """
        required_routes = []

        # All buildings need entrance to main areas
        required_routes.append(
            {
                "id": "entrance_to_main_area",
                "from": "Main Entrance",
                "to": "Main Area",
            }
        )

        # Commercial buildings need additional routes
        if design.building_type == "commercial":
            required_routes.extend(
                [
                    {
                        "id": "entrance_to_restroom",
                        "from": "Main Entrance",
                        "to": "Public Restroom",
                    },
                    {
                        "id": "entrance_to_elevator",
                        "from": "Main Entrance",
                        "to": "Elevator",
                    },
                ]
            )

        return required_routes

    async def _validate_single_route(
        self, route: Dict, standards: List[str]
    ) -> RouteValidation:
        """
        Validate a single accessible route.

        Args:
            route: Route dictionary with dimensions and properties
            standards: List of accessibility standards

        Returns:
            RouteValidation with accessibility status
        """
        issues = []

        # Check minimum width requirements
        min_width = 36  # ADA minimum 36 inches
        if route.get("width", 0) < min_width:
            issues.append(
                f"Route width {route.get('width')}\" is less than required {min_width}\""
            )

        # Check ramp slope requirements
        if route.get("has_ramps", False):
            max_slope = 0.083  # ADA maximum 1:12 (8.33%)
            if route.get("slope", 0) > max_slope:
                issues.append(
                    f"Ramp slope {route.get('slope')*100:.1f}% exceeds maximum {max_slope*100:.1f}%"
                )

        # Check for level landings
        if route.get("has_ramps", False) and not route.get("has_landings", False):
            issues.append("Ramps must have level landings at top and bottom")

        is_accessible = len(issues) == 0

        return RouteValidation(
            route_id=route["id"],
            from_location=route["from"],
            to_location=route["to"],
            is_accessible=is_accessible,
            issues=issues,
        )

    def _extract_clearances_from_design(self, design: Design) -> Dict:
        """
        Extract clearance data from design metadata.

        Args:
            design: Design to extract clearances from

        Returns:
            Dictionary with clearance data by type
        """
        # In a real implementation, this would parse actual design data
        clearances = {
            "doors": [
                {
                    "id": "main_entrance",
                    "location": "Main Entrance",
                    "clear_width": 30,  # inches
                    "opening_force": 8,  # lbf
                    "threshold_height": 0.75,  # inches
                },
                {
                    "id": "restroom_door",
                    "location": "Public Restroom",
                    "clear_width": 28,  # inches
                    "opening_force": 5,  # lbf
                    "threshold_height": 0.5,  # inches
                },
            ],
            "corridors": [
                {
                    "id": "main_corridor",
                    "location": "Main Corridor",
                    "width": 44,  # inches
                    "length": 200,  # inches
                },
                {
                    "id": "secondary_corridor",
                    "location": "Secondary Corridor",
                    "width": 32,  # inches
                    "length": 100,  # inches
                },
            ],
            "ramps": [
                {
                    "id": "entrance_ramp",
                    "location": "Main Entrance",
                    "slope": 0.08,  # 8%
                    "width": 36,  # inches
                    "length": 96,  # inches
                    "has_handrails": True,
                    "has_landings": True,
                },
            ],
            "maneuvering": [
                {
                    "id": "door_maneuvering_1",
                    "location": "Main Entrance",
                    "approach_side": "pull",
                    "clearance_width": 18,  # inches
                    "clearance_depth": 60,  # inches
                },
            ],
        }

        return clearances

    async def _check_door_clearances(
        self, doors: List[Dict], standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check door clearance requirements."""
        violations = []

        for door in doors:
            # Check clear width (ADA 404.2.3)
            min_clear_width = 32  # inches
            if door.get("clear_width", 0) < min_clear_width:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 404.2.3",
                        location=door.get("location", "Unknown"),
                        description="Door clear width insufficient",
                        required_value=f"{min_clear_width} inches minimum",
                        actual_value=f"{door.get('clear_width', 0)} inches",
                        remediation="Increase door clear width to 32 inches minimum",
                    )
                )

            # Check opening force (ADA 404.2.9)
            max_opening_force = 5  # lbf
            if door.get("opening_force", 0) > max_opening_force:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 404.2.9",
                        location=door.get("location", "Unknown"),
                        description="Door opening force exceeds maximum",
                        required_value=f"{max_opening_force} lbf maximum",
                        actual_value=f"{door.get('opening_force', 0)} lbf",
                        remediation="Reduce door opening force or install automatic door operator",
                    )
                )

            # Check threshold height (ADA 404.2.5)
            max_threshold = 0.5  # inches
            if door.get("threshold_height", 0) > max_threshold:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 404.2.5",
                        location=door.get("location", "Unknown"),
                        description="Door threshold height exceeds maximum",
                        required_value=f"{max_threshold} inches maximum",
                        actual_value=f"{door.get('threshold_height', 0)} inches",
                        remediation="Reduce threshold height to 0.5 inches maximum",
                    )
                )

        return violations

    async def _check_corridor_clearances(
        self, corridors: List[Dict], standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check corridor width requirements."""
        violations = []

        for corridor in corridors:
            # Check minimum width (ADA 403.5.1)
            min_width = 36  # inches
            if corridor.get("width", 0) < min_width:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 403.5.1",
                        location=corridor.get("location", "Unknown"),
                        description="Corridor width insufficient",
                        required_value=f"{min_width} inches minimum",
                        actual_value=f"{corridor.get('width', 0)} inches",
                        remediation="Increase corridor width to 36 inches minimum",
                    )
                )

        return violations

    async def _check_ramp_clearances(
        self, ramps: List[Dict], standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check ramp slope and clearance requirements."""
        violations = []

        for ramp in ramps:
            # Check slope (ADA 405.2)
            max_slope = 0.083  # 1:12 ratio (8.33%)
            if ramp.get("slope", 0) > max_slope:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 405.2",
                        location=ramp.get("location", "Unknown"),
                        description="Ramp slope exceeds maximum",
                        required_value=f"{max_slope*100:.1f}% maximum (1:12)",
                        actual_value=f"{ramp.get('slope', 0)*100:.1f}%",
                        remediation="Reduce ramp slope to 1:12 maximum or provide alternative accessible route",
                    )
                )

            # Check width (ADA 405.5)
            min_width = 36  # inches
            if ramp.get("width", 0) < min_width:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 405.5",
                        location=ramp.get("location", "Unknown"),
                        description="Ramp width insufficient",
                        required_value=f"{min_width} inches minimum",
                        actual_value=f"{ramp.get('width', 0)} inches",
                        remediation="Increase ramp width to 36 inches minimum",
                    )
                )

            # Check handrails (ADA 405.8)
            if not ramp.get("has_handrails", False):
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 405.8",
                        location=ramp.get("location", "Unknown"),
                        description="Ramp missing required handrails",
                        required_value="Handrails on both sides",
                        actual_value="No handrails provided",
                        remediation="Install handrails on both sides of ramp",
                    )
                )

            # Check landings (ADA 405.7)
            if not ramp.get("has_landings", False):
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 405.7",
                        location=ramp.get("location", "Unknown"),
                        description="Ramp missing required landings",
                        required_value="Level landings at top and bottom",
                        actual_value="No landings provided",
                        remediation="Provide level landings at top and bottom of ramp",
                    )
                )

        return violations

    async def _check_maneuvering_clearances(
        self, clearances: List[Dict], standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check door maneuvering clearance requirements."""
        violations = []

        for clearance in clearances:
            approach_side = clearance.get("approach_side", "")

            # Check maneuvering clearances based on approach side (ADA 404.2.4)
            if approach_side == "pull":
                min_width = 18  # inches
                min_depth = 60  # inches
            else:  # push side
                min_width = 12  # inches
                min_depth = 48  # inches

            if clearance.get("clearance_width", 0) < min_width:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 404.2.4",
                        location=clearance.get("location", "Unknown"),
                        description=f"Door maneuvering clearance width insufficient ({approach_side} side)",
                        required_value=f"{min_width} inches minimum",
                        actual_value=f"{clearance.get('clearance_width', 0)} inches",
                        remediation=f"Increase maneuvering clearance width to {min_width} inches minimum",
                    )
                )

            if clearance.get("clearance_depth", 0) < min_depth:
                violations.append(
                    AccessibilityViolation(
                        standard_section="ADA 404.2.4",
                        location=clearance.get("location", "Unknown"),
                        description=f"Door maneuvering clearance depth insufficient ({approach_side} side)",
                        required_value=f"{min_depth} inches minimum",
                        actual_value=f"{clearance.get('clearance_depth', 0)} inches",
                        remediation=f"Increase maneuvering clearance depth to {min_depth} inches minimum",
                    )
                )

        return violations

    def _extract_restrooms_from_design(self, design: Design) -> List[Dict]:
        """
        Extract restroom data from design metadata.

        Args:
            design: Design to extract restrooms from

        Returns:
            List of restroom dictionaries
        """
        # In a real implementation, this would parse actual design data
        restrooms = [
            {
                "id": "public_restroom_1",
                "location": "First Floor Public Restroom",
                "type": "single_user",
                "door_clear_width": 30,  # inches
                "turning_space_diameter": 58,  # inches
                "fixtures": {
                    "toilet": {
                        "centerline_distance": 16,  # inches from wall
                        "seat_height": 17,  # inches
                        "grab_bars": {
                            "side_wall": {"length": 40, "height": 33},  # inches
                            "rear_wall": {"length": 32, "height": 33},  # inches
                        },
                    },
                    "sink": {
                        "knee_clearance_height": 27,  # inches
                        "knee_clearance_depth": 8,  # inches
                        "rim_height": 34,  # inches
                    },
                },
            },
        ]

        return restrooms

    async def _check_restroom_fixture_clearances(
        self, restroom: Dict, standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check restroom fixture clearance requirements."""
        violations = []
        location = restroom.get("location", "Unknown")

        # Check toilet clearances
        toilet = restroom.get("fixtures", {}).get("toilet", {})

        # Toilet centerline distance (ADA 604.2)
        required_centerline = 16  # inches minimum, 18 inches maximum
        actual_centerline = toilet.get("centerline_distance", 0)
        if actual_centerline < 16 or actual_centerline > 18:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.2",
                    location=location,
                    description="Toilet centerline distance incorrect",
                    required_value="16-18 inches from side wall",
                    actual_value=f"{actual_centerline} inches",
                    remediation="Position toilet 16-18 inches from side wall centerline",
                )
            )

        # Toilet seat height (ADA 604.4)
        required_seat_height_min = 17  # inches
        required_seat_height_max = 19  # inches
        actual_seat_height = toilet.get("seat_height", 0)
        if (
            actual_seat_height < required_seat_height_min
            or actual_seat_height > required_seat_height_max
        ):
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.4",
                    location=location,
                    description="Toilet seat height incorrect",
                    required_value=f"{required_seat_height_min}-{required_seat_height_max} inches",
                    actual_value=f"{actual_seat_height} inches",
                    remediation=f"Adjust toilet seat height to {required_seat_height_min}-{required_seat_height_max} inches",
                )
            )

        # Check sink clearances
        sink = restroom.get("fixtures", {}).get("sink", {})

        # Knee clearance height (ADA 606.2)
        required_knee_height = 27  # inches minimum
        actual_knee_height = sink.get("knee_clearance_height", 0)
        if actual_knee_height < required_knee_height:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 606.2",
                    location=location,
                    description="Sink knee clearance height insufficient",
                    required_value=f"{required_knee_height} inches minimum",
                    actual_value=f"{actual_knee_height} inches",
                    remediation="Provide minimum 27 inches knee clearance height under sink",
                )
            )

        # Sink rim height (ADA 606.3)
        max_rim_height = 34  # inches
        actual_rim_height = sink.get("rim_height", 0)
        if actual_rim_height > max_rim_height:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 606.3",
                    location=location,
                    description="Sink rim height exceeds maximum",
                    required_value=f"{max_rim_height} inches maximum",
                    actual_value=f"{actual_rim_height} inches",
                    remediation="Lower sink rim to 34 inches maximum height",
                )
            )

        return violations

    async def _check_grab_bar_requirements(
        self, restroom: Dict, standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check grab bar requirements."""
        violations = []
        location = restroom.get("location", "Unknown")

        toilet = restroom.get("fixtures", {}).get("toilet", {})
        grab_bars = toilet.get("grab_bars", {})

        # Side wall grab bar (ADA 604.5.1)
        side_wall_bar = grab_bars.get("side_wall", {})
        required_side_length = 42  # inches minimum
        actual_side_length = side_wall_bar.get("length", 0)
        if actual_side_length < required_side_length:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.5.1",
                    location=location,
                    description="Side wall grab bar length insufficient",
                    required_value=f"{required_side_length} inches minimum",
                    actual_value=f"{actual_side_length} inches",
                    remediation="Install side wall grab bar minimum 42 inches long",
                )
            )

        # Rear wall grab bar (ADA 604.5.2)
        rear_wall_bar = grab_bars.get("rear_wall", {})
        required_rear_length = 36  # inches minimum
        actual_rear_length = rear_wall_bar.get("length", 0)
        if actual_rear_length < required_rear_length:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.5.2",
                    location=location,
                    description="Rear wall grab bar length insufficient",
                    required_value=f"{required_rear_length} inches minimum",
                    actual_value=f"{actual_rear_length} inches",
                    remediation="Install rear wall grab bar minimum 36 inches long",
                )
            )

        # Check grab bar height (ADA 604.5)
        required_height_min = 33  # inches
        required_height_max = 36  # inches

        side_height = side_wall_bar.get("height", 0)
        if side_height < required_height_min or side_height > required_height_max:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.5",
                    location=location,
                    description="Side wall grab bar height incorrect",
                    required_value=f"{required_height_min}-{required_height_max} inches",
                    actual_value=f"{side_height} inches",
                    remediation=f"Install side wall grab bar at {required_height_min}-{required_height_max} inches height",
                )
            )

        rear_height = rear_wall_bar.get("height", 0)
        if rear_height < required_height_min or rear_height > required_height_max:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.5",
                    location=location,
                    description="Rear wall grab bar height incorrect",
                    required_value=f"{required_height_min}-{required_height_max} inches",
                    actual_value=f"{rear_height} inches",
                    remediation=f"Install rear wall grab bar at {required_height_min}-{required_height_max} inches height",
                )
            )

        return violations

    async def _check_restroom_door_clearances(
        self, restroom: Dict, standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check restroom door clearance requirements."""
        violations = []
        location = restroom.get("location", "Unknown")

        # Door clear width (ADA 404.2.3)
        min_clear_width = 32  # inches
        actual_clear_width = restroom.get("door_clear_width", 0)
        if actual_clear_width < min_clear_width:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 404.2.3",
                    location=location,
                    description="Restroom door clear width insufficient",
                    required_value=f"{min_clear_width} inches minimum",
                    actual_value=f"{actual_clear_width} inches",
                    remediation="Increase restroom door clear width to 32 inches minimum",
                )
            )

        return violations

    async def _check_restroom_turning_space(
        self, restroom: Dict, standards: List[str]
    ) -> List[AccessibilityViolation]:
        """Check restroom turning space requirements."""
        violations = []
        location = restroom.get("location", "Unknown")

        # Turning space diameter (ADA 604.3.1)
        min_turning_diameter = 60  # inches
        actual_turning_diameter = restroom.get("turning_space_diameter", 0)
        if actual_turning_diameter < min_turning_diameter:
            violations.append(
                AccessibilityViolation(
                    standard_section="ADA 604.3.1",
                    location=location,
                    description="Restroom turning space insufficient",
                    required_value=f"{min_turning_diameter} inches diameter minimum",
                    actual_value=f"{actual_turning_diameter} inches diameter",
                    remediation="Provide minimum 60-inch diameter turning space in restroom",
                )
            )

        return violations

    def _build_accessibility_response(
        self, accessibility_check: AccessibilityCheck
    ) -> AccessibilityCheckResponse:
        """
        Build AccessibilityCheckResponse from AccessibilityCheck model.

        Args:
            accessibility_check: AccessibilityCheck model instance

        Returns:
            AccessibilityCheckResponse schema
        """
        # Convert violations from JSON to AccessibilityViolation objects
        violations = []
        for v_data in accessibility_check.violations:
            violations.append(AccessibilityViolation(**v_data))

        # Convert routes from JSON to RouteValidation objects
        accessible_routes = []
        for r_data in accessibility_check.accessible_routes:
            accessible_routes.append(RouteValidation(**r_data))

        return AccessibilityCheckResponse(
            id=UUID(accessibility_check.id),
            design_id=UUID(accessibility_check.design_id),
            design_version=accessibility_check.design_version,
            standards=accessibility_check.standards,
            status=CheckStatus(accessibility_check.status),
            passed=accessibility_check.passed,
            violations=violations,
            accessible_routes=accessible_routes,
            started_at=accessibility_check.started_at,
            completed_at=accessibility_check.completed_at,
        )
