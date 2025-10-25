"""
Optimization Service for AI-powered design optimization.

This service orchestrates the design optimization workflow:
1. Analyzes design specifications
2. Generates optimization suggestions using LLM
3. Creates DesignOptimization entities
4. Applies optimizations by creating new design versions
"""

import logging
from typing import List, Dict, Any

from ..models.design import Design
from ..models.design_optimization import DesignOptimization
from ..repositories.design_repository import DesignRepository
from ..repositories.optimization_repository import OptimizationRepository
from ..services.llm_client import LLMClient, LLMGenerationError, LLMTimeoutError


logger = logging.getLogger(__name__)


class OptimizationService:
    """Service for AI-powered design optimization."""

    def __init__(
        self,
        llm_client: LLMClient,
        optimization_repository: OptimizationRepository,
        design_repository: DesignRepository,
    ):
        """
        Initialize the optimization service.

        Args:
            llm_client: Client for LLM interactions
            optimization_repository: Repository for optimization data access
            design_repository: Repository for design data access
        """
        self.llm_client = llm_client
        self.optimization_repository = optimization_repository
        self.design_repository = design_repository

    async def generate_optimizations(
        self,
        design: Design,
        optimization_types: List[str],
    ) -> List[DesignOptimization]:
        """
        Generate optimization suggestions for a design.

        This method:
        1. Analyzes the design specification
        2. Calls the LLM to generate optimization suggestions
        3. Parses the LLM response
        4. Creates DesignOptimization entities
        5. Saves optimizations to the database

        Args:
            design: Design to generate optimizations for
            optimization_types: Types of optimizations to generate
                               (e.g., ["cost", "structural", "sustainability"])

        Returns:
            List of created DesignOptimization instances

        Raises:
            LLMGenerationError: If LLM generation fails
            LLMTimeoutError: If LLM request times out
        """
        logger.info(
            f"Starting optimization generation for design {design.id}, "
            f"types: {optimization_types}"
        )

        # Step 1: Call LLM to generate optimization suggestions
        logger.debug("Calling LLM to generate optimization suggestions")
        llm_response = await self.llm_client.generate_optimizations(
            design_specification=design.specification,
            optimization_types=optimization_types,
        )

        optimizations_data = llm_response["optimizations"]
        logger.info(
            f"LLM generation successful. Generated {len(optimizations_data)} suggestions"
        )

        # Step 2: Create DesignOptimization entities
        created_optimizations = []

        for opt_data in optimizations_data:
            logger.debug(
                f"Creating optimization: {opt_data.get('optimization_type')} - "
                f"{opt_data.get('title')}"
            )

            optimization = self.optimization_repository.create_optimization(
                design_id=design.id,
                optimization_type=opt_data["optimization_type"],
                title=opt_data["title"],
                description=opt_data["description"],
                estimated_cost_impact=opt_data.get("estimated_cost_impact"),
                implementation_difficulty=opt_data["implementation_difficulty"],
                priority=opt_data["priority"],
                status="suggested",
            )

            created_optimizations.append(optimization)
            logger.debug(f"Optimization created with ID: {optimization.id}")

        logger.info(
            f"Optimization generation complete. Created {len(created_optimizations)} optimizations"
        )

        return created_optimizations

    async def apply_optimization(
        self,
        optimization_id: int,
        user_id: int,
    ) -> Design:
        """
        Apply an optimization suggestion by creating a new design version.

        This method:
        1. Retrieves the optimization
        2. Updates optimization status to 'applied'
        3. Retrieves the associated design
        4. Creates a new design version with the optimization applied
        5. Returns the new design version

        Args:
            optimization_id: ID of the optimization to apply
            user_id: ID of the user applying the optimization

        Returns:
            Created Design instance (new version with optimization applied)

        Raises:
            ValueError: If optimization or design is not found
        """
        logger.info(
            f"Applying optimization {optimization_id} for user {user_id}"
        )

        # Step 1: Update optimization status to 'applied'
        logger.debug(f"Updating optimization {optimization_id} status to 'applied'")
        optimization = self.optimization_repository.update_optimization_status(
            optimization_id=optimization_id,
            status="applied",
            user_id=user_id,
        )

        if not optimization:
            error_msg = f"Optimization with ID {optimization_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"Optimization status updated. Type: {optimization.optimization_type}, "
            f"Title: {optimization.title}"
        )

        # Step 2: Retrieve the associated design
        logger.debug(f"Retrieving design {optimization.design_id}")
        parent_design = self.design_repository.get_design_by_id(
            optimization.design_id, include_archived=False
        )

        if not parent_design:
            error_msg = f"Design with ID {optimization.design_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(
            f"Parent design found. Current version: {parent_design.version}"
        )

        # Step 3: Create new design version with optimization applied
        # For now, we create a new version with the same specification
        # In a real implementation, we would modify the specification
        # based on the optimization details
        new_version_data = {
            "project_id": parent_design.project_id,
            "name": parent_design.name,
            "description": self._build_optimized_description(
                parent_design.description,
                optimization,
            ),
            "specification": self._apply_optimization_to_specification(
                parent_design.specification,
                optimization,
            ),
            "building_type": parent_design.building_type,
            "total_area": parent_design.total_area,
            "num_floors": parent_design.num_floors,
            "materials": parent_design.materials,
            "generation_prompt": parent_design.generation_prompt,
            "confidence_score": parent_design.confidence_score,
            "ai_model_version": parent_design.ai_model_version,
            "version": parent_design.version + 1,
            "parent_design_id": parent_design.id,
            "status": "draft",
            "created_by": user_id,
        }

        logger.debug(f"Creating new version {new_version_data['version']}")
        new_design = self.design_repository.create_design(**new_version_data)

        logger.info(
            f"Design version created successfully. ID: {new_design.id}, "
            f"Version: {new_design.version}, Parent ID: {new_design.parent_design_id}"
        )

        return new_design

    def _build_optimized_description(
        self,
        original_description: str,
        optimization: DesignOptimization,
    ) -> str:
        """
        Build an updated description that includes the applied optimization.

        Args:
            original_description: Original design description
            optimization: Applied optimization

        Returns:
            Updated description
        """
        if not original_description:
            return f"Optimized with: {optimization.title}"

        return f"{original_description}\n\nOptimization applied: {optimization.title}"

    def _apply_optimization_to_specification(
        self,
        specification: Dict[str, Any],
        optimization: DesignOptimization,
    ) -> Dict[str, Any]:
        """
        Apply optimization changes to the design specification.

        This is a simplified implementation that adds optimization metadata.
        In a real implementation, this would modify the specification based on
        the specific optimization type and details.

        Args:
            specification: Original design specification
            optimization: Optimization to apply

        Returns:
            Updated specification
        """
        # Create a copy of the specification
        updated_spec = specification.copy()

        # Add optimization metadata
        if "optimizations_applied" not in updated_spec:
            updated_spec["optimizations_applied"] = []

        updated_spec["optimizations_applied"].append({
            "optimization_id": optimization.id,
            "optimization_type": optimization.optimization_type,
            "title": optimization.title,
            "description": optimization.description,
            "estimated_cost_impact": optimization.estimated_cost_impact,
        })

        # Apply specific changes based on optimization type
        # This is a simplified implementation
        if optimization.optimization_type == "cost":
            # For cost optimizations, we might update materials or structure
            if "materials" in updated_spec:
                # Add a note about cost optimization
                for material in updated_spec["materials"]:
                    if "notes" not in material:
                        material["notes"] = []
                    material["notes"].append(f"Cost optimized: {optimization.title}")

        elif optimization.optimization_type == "structural":
            # For structural optimizations, we might update structure details
            if "structure" in updated_spec:
                if "optimization_notes" not in updated_spec["structure"]:
                    updated_spec["structure"]["optimization_notes"] = []
                updated_spec["structure"]["optimization_notes"].append(
                    optimization.title
                )

        elif optimization.optimization_type == "sustainability":
            # For sustainability optimizations, we might add sustainability features
            if "sustainability" not in updated_spec:
                updated_spec["sustainability"] = {}
            if "features" not in updated_spec["sustainability"]:
                updated_spec["sustainability"]["features"] = []
            updated_spec["sustainability"]["features"].append({
                "title": optimization.title,
                "description": optimization.description,
            })

        return updated_spec
