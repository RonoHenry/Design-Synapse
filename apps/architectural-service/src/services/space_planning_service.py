"""Space planning service for layout optimization and space analysis."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.api.v1.schemas.analysis import (LayoutRecommendation,
                                         PlanningConstraints, SpaceMetrics,
                                         SpacePlanningRequest,
                                         SpaceRequirement)
from src.core.exceptions import NotFoundError, ValidationError
from src.models.space_planning import SpacePlanning
from src.repositories.design_repository import DesignRepository
from src.repositories.space_planning_repository import SpacePlanningRepository

logger = logging.getLogger(__name__)


class SpacePlanningService:
    """
    Service for space planning and layout optimization.

    Provides automated space planning assistance including layout
    recommendations, space utilization metrics, and circulation validation.
    """

    def __init__(
        self,
        space_planning_repository: SpacePlanningRepository,
        design_repository: DesignRepository,
    ):
        """
        Initialize SpacePlanningService.

        Args:
            space_planning_repository: Repository for space planning data access
            design_repository: Repository for design data access
        """
        self.space_planning_repository = space_planning_repository
        self.design_repository = design_repository

    async def plan_spaces(
        self,
        design_id: UUID,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
        optimization_goals: Optional[List[str]] = None,
    ) -> SpacePlanning:
        """
        Generate space planning recommendations based on requirements.

        Analyzes space requirements and constraints to generate layout
        recommendations based on functional relationships and optimization goals.

        Args:
            design_id: Design ID to plan spaces for
            requirements: List of space requirements
            constraints: Planning constraints
            optimization_goals: Optional optimization goals

        Returns:
            SpacePlanning instance with recommendations

        Raises:
            NotFoundError: If design doesn't exist
            ValidationError: If requirements are invalid
        """
        # Validate design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found",
                details={"design_id": str(design_id)},
            )

        # Check if design is deleted
        if design.is_deleted:
            raise ValidationError(
                f"Cannot plan spaces for deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Validate requirements
        self._validate_requirements(requirements, constraints)

        # Create space planning record
        space_planning = SpacePlanning(
            id=str(uuid4()),
            design_id=str(design_id),
            status="in_progress",
            requirements=[req.model_dump() for req in requirements],
            recommendations=[],
            metrics={},
            space_program={},
            started_at=datetime.utcnow(),
        )

        # Save initial record
        space_planning = await self.space_planning_repository.create(space_planning)

        try:
            # Generate layout recommendations
            recommendations = await self._generate_layout_recommendations(
                requirements, constraints, optimization_goals or []
            )

            # Calculate space metrics
            metrics = await self.calculate_metrics(requirements, constraints)

            # Generate space program document
            space_program = await self._generate_space_program(
                requirements, recommendations, metrics
            )

            # Update space planning with results
            update_data = {
                "status": "completed",
                "recommendations": [rec.model_dump() for rec in recommendations],
                "metrics": metrics.model_dump(),
                "space_program": space_program,
                "completed_at": datetime.utcnow(),
            }

            space_planning = await self.space_planning_repository.update(
                space_planning.id, **update_data
            )

            logger.info(
                f"Completed space planning for design {design_id} "
                f"with {len(recommendations)} recommendations"
            )

            return space_planning

        except Exception as e:
            # Mark as failed
            await self.space_planning_repository.update(
                space_planning.id,
                status="failed",
                completed_at=datetime.utcnow(),
            )
            logger.error(f"Space planning failed for design {design_id}: {e}")
            raise ValidationError(
                f"Space planning failed: {str(e)}",
                details={"design_id": str(design_id), "error": str(e)},
            )

    async def calculate_metrics(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
    ) -> SpaceMetrics:
        """
        Calculate space utilization metrics.

        Calculates area efficiency, circulation ratios, and density
        based on space requirements and constraints.

        Args:
            requirements: List of space requirements
            constraints: Planning constraints

        Returns:
            SpaceMetrics with calculated values
        """
        # Calculate total required area
        total_required = sum(req.min_area for req in requirements)

        # Get total available area from constraints
        total_available = constraints.total_area or total_required * 1.3

        # Calculate area efficiency (usable area / total area)
        area_efficiency = min((total_required / total_available) * 100, 100.0)

        # Calculate circulation ratio (assume 20-30% for circulation)
        circulation_area = total_available - total_required
        circulation_ratio = (
            circulation_area / total_required if total_required > 0 else 0.3
        )

        # Calculate density (assume average occupancy based on space types)
        total_occupancy = self._calculate_total_occupancy(requirements)
        density = total_occupancy / total_available if total_available > 0 else 0

        metrics = SpaceMetrics(
            area_efficiency=round(area_efficiency, 2),
            circulation_ratio=round(circulation_ratio, 3),
            density=round(density, 4),
        )

        logger.debug(
            f"Calculated metrics: efficiency={metrics.area_efficiency}%, "
            f"circulation={metrics.circulation_ratio}, density={metrics.density}"
        )

        return metrics

    async def optimize_layout(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
        goals: List[str],
    ) -> List[LayoutRecommendation]:
        """
        Optimize layout based on goals.

        Analyzes current layout and suggests improvements based on
        optimization goals such as efficiency, circulation, or adjacencies.

        Args:
            requirements: Space requirements
            constraints: Planning constraints
            goals: Optimization goals

        Returns:
            List of layout recommendations
        """
        recommendations = []

        # Process each optimization goal
        for goal in goals:
            if goal == "maximize_efficiency":
                recommendations.extend(
                    await self._optimize_for_efficiency(requirements, constraints)
                )
            elif goal == "improve_circulation":
                recommendations.extend(
                    await self._optimize_for_circulation(requirements, constraints)
                )
            elif goal == "enhance_adjacencies":
                recommendations.extend(
                    await self._optimize_for_adjacencies(requirements, constraints)
                )

        # Remove duplicates and prioritize
        unique_recommendations = self._deduplicate_recommendations(recommendations)

        logger.debug(
            f"Generated {len(unique_recommendations)} optimization recommendations"
        )

        return unique_recommendations

    async def validate_circulation(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
    ) -> Dict[str, any]:
        """
        Validate circulation paths and emergency egress routes.

        Ensures proper circulation paths and emergency egress routes
        meet building code requirements.

        Args:
            requirements: Space requirements
            constraints: Planning constraints

        Returns:
            Dictionary with circulation validation results
        """
        validation_results = {
            "is_valid": True,
            "issues": [],
            "egress_paths": [],
            "circulation_width": {},
            "dead_ends": [],
        }

        # Validate minimum corridor widths
        min_corridor_width = 44  # inches, typical building code requirement
        for req in requirements:
            if req.space_type in ["corridor", "hallway"]:
                if req.min_area < (min_corridor_width / 12) * 10:  # Convert to sq ft
                    validation_results["issues"].append(
                        f"Corridor {req.space_type} may be too narrow "
                        f"(min {min_corridor_width} inches required)"
                    )
                    validation_results["is_valid"] = False

        # Check egress requirements
        total_occupancy = self._calculate_total_occupancy(requirements)
        required_egress_width = max(32, total_occupancy * 0.2)  # 0.2 inches per person

        validation_results["egress_paths"] = [
            {
                "path_id": "primary_egress",
                "required_width": required_egress_width,
                "is_adequate": True,
                "notes": "Primary egress path from main spaces to exit",
            }
        ]

        # Check for dead ends
        for req in requirements:
            if not req.adjacencies and req.space_type not in ["storage", "utility"]:
                validation_results["dead_ends"].append(req.space_type)
                validation_results["issues"].append(
                    f"Space {req.space_type} may create dead end condition"
                )

        logger.debug(
            f"Circulation validation: {len(validation_results['issues'])} issues found"
        )

        return validation_results

    async def _generate_layout_recommendations(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
        goals: List[str],
    ) -> List[LayoutRecommendation]:
        """Generate layout recommendations based on functional relationships."""
        recommendations = []

        # Sort requirements by area (largest first for better placement)
        sorted_requirements = sorted(
            requirements, key=lambda x: x.min_area, reverse=True
        )

        for i, req in enumerate(sorted_requirements):
            # Calculate recommended area (add 10-20% buffer)
            buffer_factor = 1.15 if "maximize_efficiency" in goals else 1.2
            recommended_area = req.min_area * buffer_factor

            # Determine optimal location based on adjacencies
            location = self._determine_optimal_location(req, sorted_requirements[:i])

            # Generate rationale
            rationale = self._generate_placement_rationale(req, location, goals)

            recommendation = LayoutRecommendation(
                space_type=req.space_type,
                recommended_area=round(recommended_area, 1),
                location=location,
                rationale=rationale,
            )

            recommendations.append(recommendation)

        return recommendations

    async def _generate_space_program(
        self,
        requirements: List[SpaceRequirement],
        recommendations: List[LayoutRecommendation],
        metrics: SpaceMetrics,
    ) -> Dict[str, any]:
        """Generate comprehensive space program document."""
        space_program = {
            "summary": {
                "total_spaces": len(requirements),
                "total_area": sum(rec.recommended_area for rec in recommendations),
                "area_efficiency": metrics.area_efficiency,
                "circulation_ratio": metrics.circulation_ratio,
            },
            "spaces": [],
            "relationships": {},
            "requirements": {},
        }

        # Add space details
        for req, rec in zip(requirements, recommendations):
            space_info = {
                "type": req.space_type,
                "required_area": req.min_area,
                "recommended_area": rec.recommended_area,
                "adjacencies": req.adjacencies,
                "requirements": req.requirements,
                "location": rec.location,
            }
            space_program["spaces"].append(space_info)

        # Build adjacency matrix
        space_types = [req.space_type for req in requirements]
        for req in requirements:
            space_program["relationships"][req.space_type] = {
                "adjacent_to": req.adjacencies,
                "priority": "high" if len(req.adjacencies) > 2 else "medium",
            }

        # Add code requirements
        space_program["requirements"] = {
            "building_code": "IBC-2021",
            "accessibility": "ADA",
            "egress": "Minimum 2 exits for occupancy > 50",
            "ventilation": "Per mechanical code requirements",
        }

        return space_program

    def _validate_requirements(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
    ) -> None:
        """Validate space requirements and constraints."""
        if not requirements:
            raise ValidationError(
                "At least one space requirement must be provided",
                details={"requirements": "empty"},
            )

        # Check for duplicate space types
        space_types = [req.space_type for req in requirements]
        if len(space_types) != len(set(space_types)):
            raise ValidationError(
                "Duplicate space types found in requirements",
                details={"space_types": space_types},
            )

        # Validate total area constraints
        total_required = sum(req.min_area for req in requirements)
        if constraints.total_area and constraints.total_area < total_required:
            raise ValidationError(
                f"Total available area ({constraints.total_area}) is less than "
                f"required area ({total_required})",
                details={
                    "total_available": constraints.total_area,
                    "total_required": total_required,
                },
            )

        # Validate individual requirements
        for req in requirements:
            if req.max_area and req.max_area < req.min_area:
                raise ValidationError(
                    f"Maximum area ({req.max_area}) cannot be less than "
                    f"minimum area ({req.min_area}) for {req.space_type}",
                    details={"space_type": req.space_type},
                )

    def _calculate_total_occupancy(self, requirements: List[SpaceRequirement]) -> int:
        """Calculate total occupancy based on space types and areas."""
        occupancy_factors = {
            "office": 100,  # sq ft per person
            "conference": 15,
            "lobby": 30,
            "corridor": 300,
            "storage": 300,
            "restroom": 40,
            "kitchen": 200,
            "dining": 15,
            "living_room": 200,
            "bedroom": 200,
        }

        total_occupancy = 0
        for req in requirements:
            factor = occupancy_factors.get(req.space_type, 100)
            occupancy = max(1, int(req.min_area / factor))
            total_occupancy += occupancy

        return total_occupancy

    def _determine_optimal_location(
        self,
        requirement: SpaceRequirement,
        placed_spaces: List[SpaceRequirement],
    ) -> Dict[str, any]:
        """Determine optimal location for a space based on adjacencies."""
        location = {
            "zone": "interior",
            "floor": 1,
            "orientation": "any",
            "adjacency_score": 0,
        }

        # Determine zone based on space type
        if requirement.space_type in ["office", "conference", "living_room"]:
            location["zone"] = "perimeter"
            location["orientation"] = "south"  # Prefer natural light
        elif requirement.space_type in ["kitchen", "restroom", "utility"]:
            location["zone"] = "service"
        elif requirement.space_type in ["corridor", "lobby", "entry"]:
            location["zone"] = "circulation"

        # Calculate adjacency score based on placed spaces
        adjacency_score = 0
        for placed in placed_spaces:
            if placed.space_type in requirement.adjacencies:
                adjacency_score += 10
            elif requirement.space_type in placed.adjacencies:
                adjacency_score += 5

        location["adjacency_score"] = adjacency_score

        return location

    def _generate_placement_rationale(
        self,
        requirement: SpaceRequirement,
        location: Dict[str, any],
        goals: List[str],
    ) -> str:
        """Generate rationale for space placement."""
        rationale_parts = []

        # Zone-based rationale
        if location["zone"] == "perimeter":
            rationale_parts.append("placed on perimeter for natural light")
        elif location["zone"] == "service":
            rationale_parts.append("located in service zone for utility access")
        elif location["zone"] == "circulation":
            rationale_parts.append("positioned for optimal circulation flow")

        # Adjacency rationale
        if requirement.adjacencies:
            rationale_parts.append(
                f"adjacent to {', '.join(requirement.adjacencies)} as required"
            )

        # Goal-based rationale
        if "maximize_efficiency" in goals:
            rationale_parts.append("sized for maximum space efficiency")
        if "improve_circulation" in goals:
            rationale_parts.append("positioned to enhance circulation")

        return "; ".join(rationale_parts) if rationale_parts else "standard placement"

    async def _optimize_for_efficiency(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
    ) -> List[LayoutRecommendation]:
        """Generate recommendations to maximize space efficiency."""
        recommendations = []

        for req in requirements:
            # Suggest minimum viable area
            recommended_area = req.min_area * 1.05  # Only 5% buffer

            recommendation = LayoutRecommendation(
                space_type=req.space_type,
                recommended_area=recommended_area,
                location={"zone": "compact", "efficiency_optimized": True},
                rationale="minimized area for maximum efficiency",
            )
            recommendations.append(recommendation)

        return recommendations

    async def _optimize_for_circulation(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
    ) -> List[LayoutRecommendation]:
        """Generate recommendations to improve circulation."""
        recommendations = []

        # Focus on circulation spaces
        for req in requirements:
            if req.space_type in ["corridor", "lobby", "entry"]:
                # Suggest wider circulation spaces
                recommended_area = req.min_area * 1.3

                recommendation = LayoutRecommendation(
                    space_type=req.space_type,
                    recommended_area=recommended_area,
                    location={"zone": "circulation", "width_optimized": True},
                    rationale="increased width for better circulation flow",
                )
                recommendations.append(recommendation)

        return recommendations

    async def _optimize_for_adjacencies(
        self,
        requirements: List[SpaceRequirement],
        constraints: PlanningConstraints,
    ) -> List[LayoutRecommendation]:
        """Generate recommendations to enhance adjacencies."""
        recommendations = []

        for req in requirements:
            if req.adjacencies:
                recommendation = LayoutRecommendation(
                    space_type=req.space_type,
                    recommended_area=req.min_area * 1.1,
                    location={
                        "zone": "adjacency_optimized",
                        "adjacent_spaces": req.adjacencies,
                    },
                    rationale=f"positioned to optimize adjacency to {', '.join(req.adjacencies)}",
                )
                recommendations.append(recommendation)

        return recommendations

    def _deduplicate_recommendations(
        self,
        recommendations: List[LayoutRecommendation],
    ) -> List[LayoutRecommendation]:
        """Remove duplicate recommendations and prioritize."""
        seen_spaces = set()
        unique_recommendations = []

        for rec in recommendations:
            if rec.space_type not in seen_spaces:
                unique_recommendations.append(rec)
                seen_spaces.add(rec.space_type)

        return unique_recommendations
