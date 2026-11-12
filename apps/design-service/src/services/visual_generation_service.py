"""
Visual Generation Service - TDD Implementation.

This service generates visual outputs (floor plans, renderings, 3D models) for designs.
Implemented using Test-Driven Development methodology.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VisualGenerationError(Exception):
    """Raised when visual generation fails."""

    pass


class VisualGenerationService:
    """
    Service for generating visual outputs for designs.

    This implementation follows TDD principles with dependency injection
    for better testability and maintainability.
    """

    def __init__(
        self,
        llm_client,
        storage_client,
        design_repository,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize the visual generation service.

        Args:
            llm_client: Client for LLM/image generation
            storage_client: Client for file storage
            design_repository: Repository for design data access
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 2.0)
        """
        self.llm_client = llm_client
        self.storage_client = storage_client
        self.design_repository = design_repository
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        logger.info("VisualGenerationService initialized with TDD approach")

    async def generate_floor_plan(
        self,
        design_id: str,
        design_data: Dict[str, Any],
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> Dict[str, Any]:
        """
        Generate a floor plan for a design.

        Args:
            design_id: ID of the design
            design_data: Design specification data
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Image quality (standard, hd)

        Returns:
            Dictionary containing:
                - floor_plan_url: URL of the uploaded floor plan
                - generation_cost: Cost of generation
                - generation_time: Time taken to generate
                - metadata: Additional generation metadata

        Raises:
            VisualGenerationError: If generation fails
        """
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting floor plan generation for design {design_id}")

            # Create prompt for floor plan
            prompt = self._create_floor_plan_prompt(design_data)

            # Generate image with retry logic
            image_result = await self._generate_with_retries(
                prompt=prompt, image_type="floor_plan", size=size, quality=quality
            )

            # Upload to storage
            storage_key = f"designs/{design_id}/floor_plan_{int(datetime.now(timezone.utc).timestamp())}.png"
            upload_result = await self.storage_client.upload_file(
                file_data=image_result["image_data"],
                key=storage_key,
                content_type="image/png",
            )

            # Update design record
            await self.design_repository.update_design(
                design_id=design_id, updates={"floor_plan_url": upload_result["url"]}
            )

            generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"Floor plan generation completed for design {design_id}. "
                f"Time: {generation_time:.2f}s, Cost: ${image_result['generation_cost']:.4f}"
            )

            return {
                "floor_plan_url": upload_result["url"],
                "generation_cost": image_result["generation_cost"],
                "generation_time": generation_time,
                "metadata": {
                    "model_version": image_result["model_version"],
                    "revised_prompt": image_result["revised_prompt"],
                    "size": size,
                    "quality": quality,
                    "storage_key": storage_key,
                },
            }

        except Exception as e:
            logger.error(f"Floor plan generation failed for design {design_id}: {e}")

            # Update design with error status
            await self.design_repository.update_design(
                design_id=design_id, updates={"visual_generation_status": "failed"}
            )

            raise VisualGenerationError(f"Floor plan generation failed: {e}")

    async def generate_3d_rendering(
        self,
        design_id: str,
        design_data: Dict[str, Any],
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> Dict[str, Any]:
        """
        Generate a 3D rendering for a design.

        Args:
            design_id: ID of the design
            design_data: Design specification data
            size: Image size
            quality: Image quality

        Returns:
            Dictionary with rendering URL and metadata

        Raises:
            VisualGenerationError: If generation fails
        """
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting 3D rendering generation for design {design_id}")

            # Create prompt for 3D rendering
            prompt = self._create_rendering_prompt(design_data)

            # Generate image with retry logic
            image_result = await self._generate_with_retries(
                prompt=prompt, image_type="rendering", size=size, quality=quality
            )

            # Upload to storage
            storage_key = f"designs/{design_id}/rendering_{int(datetime.now(timezone.utc).timestamp())}.png"
            upload_result = await self.storage_client.upload_file(
                file_data=image_result["image_data"],
                key=storage_key,
                content_type="image/png",
            )

            # Update design record
            await self.design_repository.update_design(
                design_id=design_id, updates={"rendering_url": upload_result["url"]}
            )

            generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"3D rendering generation completed for design {design_id}. "
                f"Time: {generation_time:.2f}s, Cost: ${image_result['generation_cost']:.4f}"
            )

            return {
                "rendering_url": upload_result["url"],
                "generation_cost": image_result["generation_cost"],
                "generation_time": generation_time,
                "metadata": {
                    "model_version": image_result["model_version"],
                    "revised_prompt": image_result["revised_prompt"],
                    "size": size,
                    "quality": quality,
                    "storage_key": storage_key,
                },
            }

        except Exception as e:
            logger.error(f"3D rendering generation failed for design {design_id}: {e}")

            # Update design with error status
            await self.design_repository.update_design(
                design_id=design_id, updates={"visual_generation_status": "failed"}
            )

            raise VisualGenerationError(f"3D rendering generation failed: {e}")

    async def generate_3d_model(
        self,
        design_id: str,
        design_data: Dict[str, Any],
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> Dict[str, Any]:
        """
        Generate a 3D model visualization for a design.

        Args:
            design_id: ID of the design
            design_data: Design specification data
            size: Image size
            quality: Image quality

        Returns:
            Dictionary with 3D model URL and metadata

        Raises:
            VisualGenerationError: If generation fails
        """
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting 3D model generation for design {design_id}")

            # Create prompt for 3D model
            prompt = self._create_3d_model_prompt(design_data)

            # Generate image with retry logic
            image_result = await self._generate_with_retries(
                prompt=prompt, image_type="3d_model", size=size, quality=quality
            )

            # Upload to storage
            storage_key = f"designs/{design_id}/3d_model_{int(datetime.now(timezone.utc).timestamp())}.png"
            upload_result = await self.storage_client.upload_file(
                file_data=image_result["image_data"],
                key=storage_key,
                content_type="image/png",
            )

            # Update design record
            await self.design_repository.update_design(
                design_id=design_id, updates={"model_3d_url": upload_result["url"]}
            )

            generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"3D model generation completed for design {design_id}. "
                f"Time: {generation_time:.2f}s, Cost: ${image_result['generation_cost']:.4f}"
            )

            return {
                "model_3d_url": upload_result["url"],
                "generation_cost": image_result["generation_cost"],
                "generation_time": generation_time,
                "metadata": {
                    "model_version": image_result["model_version"],
                    "revised_prompt": image_result["revised_prompt"],
                    "size": size,
                    "quality": quality,
                    "storage_key": storage_key,
                },
            }

        except Exception as e:
            logger.error(f"3D model generation failed for design {design_id}: {e}")

            # Update design with error status
            await self.design_repository.update_design(
                design_id=design_id, updates={"visual_generation_status": "failed"}
            )

            raise VisualGenerationError(f"3D model generation failed: {e}")

    async def generate_all_visuals(
        self,
        design_id: str,
        design_data: Dict[str, Any],
        visual_types: List[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> Dict[str, Any]:
        """
        Generate all visual outputs for a design.

        Args:
            design_id: ID of the design
            design_data: Design specification data
            visual_types: List of visual types to generate (default: all)
            size: Image size
            quality: Image quality

        Returns:
            Dictionary with all generated visual URLs and metadata

        Raises:
            VisualGenerationError: If any generation fails
        """
        if visual_types is None:
            visual_types = ["floor_plan", "rendering", "3d_model"]

        start_time = datetime.now(timezone.utc)
        results = {}
        total_cost = 0.0

        try:
            logger.info(
                f"Starting generation of {len(visual_types)} visuals for design {design_id}"
            )

            # Update status to processing
            await self.design_repository.update_design(
                design_id=design_id, updates={"visual_generation_status": "processing"}
            )

            # Generate each visual type
            for visual_type in visual_types:
                try:
                    if visual_type == "floor_plan":
                        result = await self.generate_floor_plan(
                            design_id, design_data, size, quality
                        )
                        results["floor_plan"] = result

                    elif visual_type == "rendering":
                        result = await self.generate_3d_rendering(
                            design_id, design_data, size, quality
                        )
                        results["rendering"] = result

                    elif visual_type == "3d_model":
                        result = await self.generate_3d_model(
                            design_id, design_data, size, quality
                        )
                        results["3d_model"] = result

                    total_cost += result["generation_cost"]

                except Exception as e:
                    logger.error(
                        f"Failed to generate {visual_type} for design {design_id}: {e}"
                    )
                    results[visual_type] = {"error": str(e)}

            # Update status to completed
            await self.design_repository.update_design(
                design_id=design_id, updates={"visual_generation_status": "completed"}
            )

            total_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Calculate success/failure counts
            generated_types = [
                vt
                for vt in visual_types
                if vt in results and "error" not in results[vt]
            ]
            failed_types = [
                vt for vt in visual_types if vt in results and "error" in results[vt]
            ]

            logger.info(
                f"Visual generation completed for design {design_id}. "
                f"Total time: {total_time:.2f}s, Total cost: ${total_cost:.4f}"
            )

            return {
                "design_id": design_id,
                "results": results,
                "total_cost": total_cost,
                "total_time": total_time,
                "generated_types": generated_types,
                "failed_types": failed_types,
            }

        except Exception as e:
            logger.error(f"Visual generation failed for design {design_id}: {e}")

            # Update status to failed
            await self.design_repository.update_design(
                design_id=design_id, updates={"visual_generation_status": "failed"}
            )

            raise VisualGenerationError(f"Visual generation failed: {e}")

    async def _generate_with_retries(
        self, prompt: str, image_type: str, size: str, quality: str
    ) -> Dict[str, Any]:
        """
        Generate image with retry logic.

        Args:
            prompt: Image generation prompt
            image_type: Type of image to generate
            size: Image size
            quality: Image quality

        Returns:
            Image generation result

        Raises:
            VisualGenerationError: If all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Image generation attempt {attempt + 1}/{self.max_retries}"
                )

                result = await self.llm_client.generate_image(
                    prompt=prompt, image_type=image_type, size=size, quality=quality
                )

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Image generation attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(
                        self.retry_delay * (attempt + 1)
                    )  # Exponential backoff
                    continue
                else:
                    break

        raise VisualGenerationError(
            f"Image generation failed after {self.max_retries} attempts. Last error: {last_error}"
        )

    def _create_floor_plan_prompt(self, design_data: Dict[str, Any]) -> str:
        """
        Create a detailed prompt for floor plan generation.

        Args:
            design_data: Design specification data

        Returns:
            Detailed prompt for floor plan generation
        """
        building_type = design_data.get("building_type", "building")
        description = design_data.get("description", "")
        requirements = design_data.get("requirements", {})

        prompt = f"A detailed architectural floor plan for a {building_type}"

        if description:
            prompt += f": {description}"

        # Add specific requirements
        if "bedrooms" in requirements:
            prompt += f", {requirements['bedrooms']} bedrooms"
        if "bathrooms" in requirements:
            prompt += f", {requirements['bathrooms']} bathrooms"
        if "square_footage" in requirements:
            prompt += f", approximately {requirements['square_footage']} square feet"

        # Add style preferences
        if "style" in design_data:
            prompt += f", {design_data['style']} style"

        prompt += ". Top-down view, clean lines, professional architectural style, with room labels, dimensions, and standard architectural symbols. Black lines on white background, technical drawing style."

        return prompt

    def _create_rendering_prompt(self, design_data: Dict[str, Any]) -> str:
        """
        Create a detailed prompt for 3D rendering generation.

        Args:
            design_data: Design specification data

        Returns:
            Detailed prompt for 3D rendering generation
        """
        building_type = design_data.get("building_type", "building")
        description = design_data.get("description", "")

        prompt = f"A photorealistic 3D architectural rendering of a {building_type}"

        if description:
            prompt += f": {description}"

        # Add style and material preferences
        if "style" in design_data:
            prompt += f", {design_data['style']} architectural style"

        if "materials" in design_data:
            materials = design_data["materials"]
            if isinstance(materials, list):
                prompt += f", featuring {', '.join(materials)} materials"
            else:
                prompt += f", featuring {materials} materials"

        # Add environmental context
        prompt += ", with professional lighting and realistic textures, high quality architectural visualization"

        return prompt

    def _create_3d_model_prompt(self, design_data: Dict[str, Any]) -> str:
        """
        Create a detailed prompt for 3D model visualization.

        Args:
            design_data: Design specification data

        Returns:
            Detailed prompt for 3D model visualization
        """
        building_type = design_data.get("building_type", "building")
        description = design_data.get("description", "")

        prompt = f"A clean 3D architectural model visualization of a {building_type}"

        if description:
            prompt += f": {description}"

        # Add style preferences
        if "style" in design_data:
            prompt += f", {design_data['style']} style"

        prompt += ", shown in isometric or perspective view with clear structural details, architectural model rendering"

        return prompt

    async def _update_design_visual_field(
        self, design_id: str, field: str, value: Any
    ) -> None:
        """
        Update a specific visual field in the design record.

        Args:
            design_id: ID of the design to update
            field: Field name to update
            value: New value for the field
        """
        try:
            await self.design_repository.update_design(
                design_id=design_id, updates={field: value}
            )
            logger.debug(f"Updated design {design_id} field '{field}' to '{value}'")
        except Exception as e:
            logger.error(f"Failed to update design {design_id} field '{field}': {e}")
            raise
