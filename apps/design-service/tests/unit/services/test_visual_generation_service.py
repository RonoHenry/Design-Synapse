"""
Unit tests for VisualGenerationService.

Following TDD methodology - these tests are written FIRST,
then the implementation will be created to pass them.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.services.visual_generation_service import (VisualGenerationError,
                                                    VisualGenerationService)


class TestVisualGenerationServiceInitialization:
    """Test service initialization and dependency injection."""

    def test_service_initialization_with_dependencies(self):
        """Test that service initializes with injected dependencies."""
        # Arrange
        mock_llm_client = MagicMock()
        mock_storage_client = MagicMock()
        mock_design_repository = MagicMock()

        # Act
        service = VisualGenerationService(
            llm_client=mock_llm_client,
            storage_client=mock_storage_client,
            design_repository=mock_design_repository,
        )

        # Assert
        assert service.llm_client == mock_llm_client
        assert service.storage_client == mock_storage_client
        assert service.design_repository == mock_design_repository
        assert service.max_retries == 3  # Default value
        assert service.retry_delay == 2.0  # Default value


class TestGenerateFloorPlan:
    """Test floor plan generation functionality."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_generate_floor_plan_success(self, service):
        """Test successful floor plan generation."""
        # Arrange
        design_id = "test-design-123"
        design_data = {
            "building_type": "residential",
            "description": "Modern house",
            "requirements": {"bedrooms": 3, "bathrooms": 2},
        }

        # Mock LLM response
        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_image_data",
            "generation_cost": 0.04,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced prompt",
        }

        # Mock storage response
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/floor_plan_123.png"
        }

        # Act
        result = await service.generate_floor_plan(design_id, design_data)

        # Assert
        assert result["floor_plan_url"] == "https://cdn.example.com/floor_plan_123.png"
        assert result["generation_cost"] == 0.04
        assert "generation_time" in result
        assert "metadata" in result

        # Verify LLM was called with correct parameters
        service.llm_client.generate_image.assert_called_once()
        call_args = service.llm_client.generate_image.call_args
        assert "floor plan" in call_args[1]["prompt"].lower()

        # Verify storage upload
        service.storage_client.upload_file.assert_called_once()

        # Verify design repository update
        service.design_repository.update_design.assert_called()

    @pytest.mark.asyncio
    async def test_generate_floor_plan_with_custom_parameters(self, service):
        """Test floor plan generation with custom size and quality."""
        # Arrange
        design_id = "test-design-123"
        design_data = {"building_type": "commercial"}

        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_data",
            "generation_cost": 0.08,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced prompt",
        }
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/floor_plan.png"
        }

        # Act
        result = await service.generate_floor_plan(
            design_id, design_data, size="1792x1024", quality="hd"
        )

        # Assert
        service.llm_client.generate_image.assert_called_once()
        call_args = service.llm_client.generate_image.call_args
        assert call_args[1]["image_type"] == "floor_plan"
        assert call_args[1]["size"] == "1792x1024"
        assert call_args[1]["quality"] == "hd"

    @pytest.mark.asyncio
    async def test_generate_floor_plan_llm_failure(self, service):
        """Test floor plan generation when LLM fails."""
        # Arrange
        design_id = "test-design-123"
        design_data = {"building_type": "residential"}

        service.llm_client.generate_image.side_effect = Exception("LLM API error")

        # Act & Assert
        with pytest.raises(VisualGenerationError, match="Floor plan generation failed"):
            await service.generate_floor_plan(design_id, design_data)

        # Verify design status was updated to failed
        service.design_repository.update_design.assert_called_with(
            design_id=design_id, updates={"visual_generation_status": "failed"}
        )

    @pytest.mark.asyncio
    async def test_generate_floor_plan_storage_failure(self, service):
        """Test floor plan generation when storage upload fails."""
        # Arrange
        design_id = "test-design-123"
        design_data = {"building_type": "residential"}

        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_data",
            "generation_cost": 0.04,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced prompt",
        }
        service.storage_client.upload_file.side_effect = Exception("Storage error")

        # Act & Assert
        with pytest.raises(VisualGenerationError, match="Floor plan generation failed"):
            await service.generate_floor_plan(design_id, design_data)


class TestGenerate3DRendering:
    """Test 3D rendering generation functionality."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_generate_3d_rendering_success(self, service):
        """Test successful 3D rendering generation."""
        # Arrange
        design_id = "test-design-456"
        design_data = {
            "building_type": "commercial",
            "description": "Office building",
            "style": "modern",
        }

        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_rendering_data",
            "generation_cost": 0.04,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced rendering prompt",
        }
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/rendering_456.png"
        }

        # Act
        result = await service.generate_3d_rendering(design_id, design_data)

        # Assert
        assert result["rendering_url"] == "https://cdn.example.com/rendering_456.png"
        assert result["generation_cost"] == 0.04

        # Verify LLM was called with rendering-specific prompt
        service.llm_client.generate_image.assert_called_once()
        call_args = service.llm_client.generate_image.call_args
        assert call_args[1]["image_type"] == "rendering"
        assert "photorealistic" in call_args[1]["prompt"].lower()


class TestGenerate3DModel:
    """Test 3D model generation functionality."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_generate_3d_model_success(self, service):
        """Test successful 3D model generation."""
        # Arrange
        design_id = "test-design-789"
        design_data = {
            "building_type": "industrial",
            "description": "Warehouse facility",
        }

        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_model_data",
            "generation_cost": 0.04,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced 3D model prompt",
        }
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/model_789.png"
        }

        # Act
        result = await service.generate_3d_model(design_id, design_data)

        # Assert
        assert result["model_3d_url"] == "https://cdn.example.com/model_789.png"

        # Verify LLM was called with 3D model-specific prompt
        service.llm_client.generate_image.assert_called_once()
        call_args = service.llm_client.generate_image.call_args
        assert call_args[1]["image_type"] == "3d_model"
        assert "3d" in call_args[1]["prompt"].lower()


class TestGenerateAllVisuals:
    """Test batch generation of all visual types."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_generate_all_visuals_success(self, service):
        """Test successful generation of all visual types."""
        # Arrange
        design_id = "test-design-all"
        design_data = {"building_type": "residential"}

        # Mock successful responses for all visual types
        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_data",
            "generation_cost": 0.04,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced prompt",
        }
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/visual.png"
        }

        # Act
        result = await service.generate_all_visuals(design_id, design_data)

        # Assert
        assert result["design_id"] == design_id
        assert "results" in result
        assert len(result["generated_types"]) == 3  # All types generated
        assert len(result["failed_types"]) == 0
        assert result["total_cost"] == 0.12  # 3 * 0.04

        # Verify all visual types were generated
        assert "floor_plan" in result["results"]
        assert "rendering" in result["results"]
        assert "3d_model" in result["results"]

    @pytest.mark.asyncio
    async def test_generate_all_visuals_partial_failure(self, service):
        """Test generation when some visual types fail."""
        # Arrange
        design_id = "test-design-partial"
        design_data = {"building_type": "residential"}

        # Mock: first call succeeds, second fails, third succeeds
        service.llm_client.generate_image.side_effect = [
            {
                "image_data": b"fake_data",
                "generation_cost": 0.04,
                "model_version": "dall-e-3",
                "revised_prompt": "Enhanced prompt",
            },
            Exception("LLM API error"),
            {
                "image_data": b"fake_data",
                "generation_cost": 0.04,
                "model_version": "dall-e-3",
                "revised_prompt": "Enhanced prompt",
            },
        ]
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/visual.png"
        }

        # Act
        result = await service.generate_all_visuals(design_id, design_data)

        # Assert
        assert len(result["generated_types"]) == 2  # 2 succeeded
        assert len(result["failed_types"]) == 1  # 1 failed
        assert result["total_cost"] == 0.08  # 2 * 0.04


class TestRetryMechanism:
    """Test retry logic for failed generations."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_retry_on_temporary_failure(self, service):
        """Test that service retries on temporary failures."""
        # Arrange
        design_id = "test-design-retry"
        design_data = {"building_type": "residential"}

        # Mock: first call fails, second succeeds
        service.llm_client.generate_image.side_effect = [
            Exception("Temporary API error"),
            {
                "image_data": b"fake_data",
                "generation_cost": 0.04,
                "model_version": "dall-e-3",
                "revised_prompt": "Enhanced prompt",
            },
        ]
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/floor_plan.png"
        }

        # Act
        result = await service.generate_floor_plan(design_id, design_data)

        # Assert
        assert result["floor_plan_url"] == "https://cdn.example.com/floor_plan.png"
        assert service.llm_client.generate_image.call_count == 2  # Retried once

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, service):
        """Test that service fails after max retries exceeded."""
        # Arrange
        design_id = "test-design-max-retry"
        design_data = {"building_type": "residential"}

        # Mock: all calls fail
        service.llm_client.generate_image.side_effect = Exception(
            "Persistent API error"
        )

        # Act & Assert
        with pytest.raises(VisualGenerationError):
            await service.generate_floor_plan(design_id, design_data)

        # Verify max retries were attempted
        assert service.llm_client.generate_image.call_count == service.max_retries


class TestPromptGeneration:
    """Test prompt generation for different visual types."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    def test_create_floor_plan_prompt_basic(self, service):
        """Test basic floor plan prompt generation."""
        design_data = {
            "building_type": "residential",
            "description": "Modern family home",
        }

        prompt = service._create_floor_plan_prompt(design_data)

        assert "residential" in prompt
        assert "Modern family home" in prompt
        assert "floor plan" in prompt.lower()
        assert "architectural" in prompt.lower()

    def test_create_floor_plan_prompt_with_requirements(self, service):
        """Test floor plan prompt with specific requirements."""
        design_data = {
            "building_type": "commercial",
            "description": "Office building",
            "requirements": {"bedrooms": 0, "bathrooms": 4, "square_footage": 5000},
            "style": "modern",
        }

        prompt = service._create_floor_plan_prompt(design_data)

        assert "commercial" in prompt
        assert "4 bathrooms" in prompt
        assert "5000 square feet" in prompt
        assert "modern style" in prompt

    def test_create_rendering_prompt_basic(self, service):
        """Test basic rendering prompt generation."""
        design_data = {
            "building_type": "industrial",
            "description": "Warehouse facility",
        }

        prompt = service._create_rendering_prompt(design_data)

        assert "industrial" in prompt
        assert "Warehouse facility" in prompt
        assert "photorealistic" in prompt.lower()
        assert "3D" in prompt

    def test_create_rendering_prompt_with_materials(self, service):
        """Test rendering prompt with materials."""
        design_data = {
            "building_type": "residential",
            "description": "Luxury home",
            "style": "contemporary",
            "materials": ["glass", "steel", "concrete"],
        }

        prompt = service._create_rendering_prompt(design_data)

        assert "contemporary" in prompt
        assert "glass, steel, concrete" in prompt
        assert "materials" in prompt

    def test_create_3d_model_prompt_basic(self, service):
        """Test basic 3D model prompt generation."""
        design_data = {"building_type": "educational", "description": "School building"}

        prompt = service._create_3d_model_prompt(design_data)

        assert "educational" in prompt
        assert "School building" in prompt
        assert "3D" in prompt
        assert "isometric" in prompt.lower()


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        return VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_generate_floor_plan_design_update_failure(self, service):
        """Test floor plan generation when design update fails."""
        design_id = "test-design-update-fail"
        design_data = {"building_type": "residential"}

        service.llm_client.generate_image.return_value = {
            "image_data": b"fake_data",
            "generation_cost": 0.04,
            "model_version": "dall-e-3",
            "revised_prompt": "Enhanced prompt",
        }
        service.storage_client.upload_file.return_value = {
            "url": "https://cdn.example.com/floor_plan.png"
        }

        # Make the first update_design call (for floor_plan_url) fail
        service.design_repository.update_design.side_effect = [
            Exception("Database error"),  # First call fails
            None,  # Second call (error handler) succeeds
        ]

        with pytest.raises(VisualGenerationError, match="Floor plan generation failed"):
            await service.generate_floor_plan(design_id, design_data)

        # Verify that update_design was called twice (once for URL, once for error status)
        assert service.design_repository.update_design.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_all_visuals_empty_visual_types(self, service):
        """Test generate_all_visuals with empty visual types list."""
        design_id = "test-design-empty"
        design_data = {"building_type": "residential"}

        result = await service.generate_all_visuals(
            design_id, design_data, visual_types=[]
        )

        assert result["design_id"] == design_id
        assert len(result["generated_types"]) == 0
        assert len(result["failed_types"]) == 0
        assert result["total_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_generate_all_visuals_invalid_visual_type(self, service):
        """Test generate_all_visuals with invalid visual type."""
        design_id = "test-design-invalid"
        design_data = {"building_type": "residential"}

        # This should not crash, just skip unknown types
        result = await service.generate_all_visuals(
            design_id, design_data, visual_types=["invalid_type"]
        )

        assert result["design_id"] == design_id
        assert len(result["generated_types"]) == 0


class TestConfigurationAndEdgeCases:
    """Test service configuration and edge cases."""

    def test_service_initialization_custom_retry_config(self):
        """Test service initialization with custom retry configuration."""
        mock_llm_client = MagicMock()
        mock_storage_client = MagicMock()
        mock_design_repository = MagicMock()

        service = VisualGenerationService(
            llm_client=mock_llm_client,
            storage_client=mock_storage_client,
            design_repository=mock_design_repository,
            max_retries=5,
            retry_delay=1.5,
        )

        assert service.max_retries == 5
        assert service.retry_delay == 1.5

    @pytest.mark.asyncio
    async def test_generate_with_retries_exponential_backoff(self):
        """Test that retry mechanism uses exponential backoff."""
        service = VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
            max_retries=3,
            retry_delay=1.0,
        )

        # Mock all calls to fail
        service.llm_client.generate_image.side_effect = Exception("API error")

        with patch("asyncio.sleep") as mock_sleep:
            with pytest.raises(VisualGenerationError):
                await service._generate_with_retries(
                    prompt="test prompt",
                    image_type="floor_plan",
                    size="1024x1024",
                    quality="standard",
                )

            # Verify exponential backoff: 1.0, 2.0 seconds
            expected_calls = [
                ((1.0,),),  # First retry: delay * 1
                ((2.0,),),  # Second retry: delay * 2
            ]
            assert mock_sleep.call_args_list == expected_calls

    @pytest.mark.asyncio
    async def test_update_design_visual_field_success(self):
        """Test successful design visual field update."""
        service = VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

        await service._update_design_visual_field(
            design_id="test-123",
            field="floor_plan_url",
            value="https://example.com/floor_plan.png",
        )

        service.design_repository.update_design.assert_called_once_with(
            design_id="test-123",
            updates={"floor_plan_url": "https://example.com/floor_plan.png"},
        )

    @pytest.mark.asyncio
    async def test_update_design_visual_field_failure(self):
        """Test design visual field update failure."""
        service = VisualGenerationService(
            llm_client=AsyncMock(),
            storage_client=AsyncMock(),
            design_repository=AsyncMock(),
        )

        service.design_repository.update_design.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(Exception, match="Database error"):
            await service._update_design_visual_field(
                design_id="test-123",
                field="floor_plan_url",
                value="https://example.com/floor_plan.png",
            )
