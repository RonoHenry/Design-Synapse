"""
Design Generator Service for AI-powered design generation.

This service orchestrates the design generation workflow:
1. Verifies project access
2. Generates design specifications using LLM
3. Creates and versions design entities
4. Calculates confidence scores
"""

import logging
from typing import Dict, Any, Optional

from ..models.design import Design
from ..repositories.design_repository import DesignRepository
from ..services.llm_client import LLMClient, LLMGenerationError, LLMTimeoutError
from ..services.project_client import ProjectClient, ProjectAccessDeniedError
from ..api.v1.schemas.requests import DesignGenerationRequest


logger = logging.getLogger(__name__)


class DesignGeneratorService:
    """Service for AI-powered design generation and versioning."""

    def __init__(
        self,
        llm_client: LLMClient,
        project_client: ProjectClient,
        design_repository: DesignRepository,
    ):
        """
        Initialize the design generator service.

        Args:
            llm_client: Client for LLM interactions
            project_client: Client for project service interactions
            design_repository: Repository for design data access
        """
        self.llm_client = llm_client
        self.project_client = project_client
        self.design_repository = design_repository

    async def generate_design(
        self,
        request: DesignGenerationRequest,
        user_id: int,
    ) -> Design:
        """
        Generate a new design from natural language description.

        This method:
        1. Verifies the user has access to the project
        2. Calls the LLM to generate a design specification
        3. Parses and validates the LLM response
        4. Creates a Design entity with the specification
        5. Saves the design to the database

        Args:
            request: Design generation request with description and requirements
            user_id: ID of the user creating the design

        Returns:
            Created Design instance

        Raises:
            ProjectAccessDeniedError: If user doesn't have access to the project
            LLMGenerationError: If LLM generation fails
            LLMTimeoutError: If LLM request times out
        """
        logger.info(
            f"Starting design generation for user {user_id}, "
            f"project {request.project_id}, building_type {request.building_type}"
        )

        # Step 1: Verify project access
        logger.debug(f"Verifying project access for user {user_id}")
        await self.project_client.verify_project_access(
            project_id=request.project_id,
            user_id=user_id,
        )
        logger.info(f"Project access verified for user {user_id}")

        # Step 2: Generate design specification using LLM
        logger.debug("Calling LLM to generate design specification")
        llm_response = await self.llm_client.generate_design_specification(
            description=request.description,
            building_type=request.building_type,
            requirements=request.requirements,
        )
        logger.info(
            f"LLM generation successful. Model: {llm_response['model_version']}, "
            f"Confidence: {llm_response['confidence_score']}"
        )

        # Step 3: Extract data from LLM response
        specification = llm_response["specification"]
        confidence_score = llm_response["confidence_score"]
        model_version = llm_response["model_version"]

        # Extract building metadata from specification
        building_info = specification.get("building_info", {})
        total_area = building_info.get("total_area")
        num_floors = building_info.get("num_floors")

        # Extract materials list
        materials = specification.get("materials", [])
        material_names = [m.get("name") for m in materials if m.get("name")]

        # Step 4: Create Design entity
        logger.debug("Creating design entity")
        design = self.design_repository.create_design(
            project_id=request.project_id,
            name=request.name,
            description=request.description,
            specification=specification,
            building_type=request.building_type,
            total_area=total_area,
            num_floors=num_floors,
            materials=material_names if material_names else None,
            generation_prompt=request.description,
            confidence_score=confidence_score,
            ai_model_version=model_version,
            version=1,
            status="draft",
            created_by=user_id,
        )

        logger.info(
            f"Design created successfully. ID: {design.id}, "
            f"Name: {design.name}, Version: {design.version}"
        )

        return design

    async def create_design_version(
        self,
        design_id: int,
        updates: Dict[str, Any],
        user_id: int,
    ) -> Design:
        """
        Create a new version of an existing design.

        This method:
        1. Retrieves the parent design
        2. Creates a new design with incremented version number
        3. Sets the parent_design_id to link versions
        4. Applies the provided updates

        Args:
            design_id: ID of the parent design to create a version from
            updates: Dictionary of fields to update in the new version
            user_id: ID of the user creating the version

        Returns:
            Created Design instance (new version)

        Raises:
            ValueError: If parent design is not found
        """
        logger.info(
            f"Creating new version of design {design_id} for user {user_id}"
        )

        # Step 1: Retrieve parent design
        parent_design = self.design_repository.get_design_by_id(
            design_id, include_archived=False
        )

        if not parent_design:
            error_msg = f"Design with ID {design_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(
            f"Parent design found. Current version: {parent_design.version}"
        )

        # Step 2: Prepare new version data
        # Start with parent design data
        new_version_data = {
            "project_id": parent_design.project_id,
            "name": parent_design.name,
            "description": parent_design.description,
            "specification": parent_design.specification,
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

        # Step 3: Apply updates
        for key, value in updates.items():
            if key in new_version_data and key not in [
                "version",
                "parent_design_id",
                "created_by",
            ]:
                new_version_data[key] = value
                logger.debug(f"Applying update: {key} = {value}")

        # If specification is updated, recalculate metadata
        if "specification" in updates:
            specification = updates["specification"]
            building_info = specification.get("building_info", {})
            new_version_data["total_area"] = building_info.get("total_area")
            new_version_data["num_floors"] = building_info.get("num_floors")

            materials = specification.get("materials", [])
            material_names = [m.get("name") for m in materials if m.get("name")]
            new_version_data["materials"] = material_names if material_names else None

        # Step 4: Create new version
        logger.debug(f"Creating new version {new_version_data['version']}")
        new_design = self.design_repository.create_design(**new_version_data)

        logger.info(
            f"Design version created successfully. ID: {new_design.id}, "
            f"Version: {new_design.version}, Parent ID: {new_design.parent_design_id}"
        )

        return new_design

    def _calculate_confidence_score(
        self,
        specification: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> float:
        """
        Calculate confidence score for a generated design.

        The score is based on:
        - Completeness of the specification (70-95 points)
        - Matching of requirements (up to 5 additional points)

        Args:
            specification: Generated design specification
            requirements: Original requirements from the request

        Returns:
            Confidence score between 70.0 and 100.0
        """
        score = 70.0  # Base score

        # Check completeness of specification sections
        if "building_info" in specification:
            score += 5.0
        if "structure" in specification:
            score += 5.0
        if "spaces" in specification and len(specification.get("spaces", [])) > 0:
            score += 5.0
        if "materials" in specification and len(specification.get("materials", [])) > 0:
            score += 5.0
        if "compliance" in specification:
            score += 5.0

        # Check if requirements are met
        building_info = specification.get("building_info", {})

        if "num_floors" in requirements:
            if building_info.get("num_floors") == requirements["num_floors"]:
                score += 2.5

        if "total_area" in requirements:
            if building_info.get("total_area") == requirements["total_area"]:
                score += 2.5

        # Ensure score doesn't exceed 100
        return min(score, 100.0)
