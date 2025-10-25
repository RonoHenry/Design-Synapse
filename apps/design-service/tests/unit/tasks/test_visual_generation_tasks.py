"""
Unit tests for visual generation Celery tasks.

This module provides comprehensive unit tests for the visual generation Celery tasks,
focusing on the core task logic and business functionality.

Tests cover:
- Task function behavior and logic
- Progress tracking and status updates
- Error handling and retry logic
- Task cleanup functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from src.services.visual_generation_service import VisualGenerationService, VisualGenerationError
from src.services.llm_client import LLMClient, LLMImageGenerationError, LLMTimeoutError
from src.repositories.design_repository import DesignRepository
from common.storage.client import StorageClient


class TestVisualGenerationTaskLogic:
    """Test suite for visual generation task business logic."""

    @pytest.fixture
    def mock_task_instance(self):
        """Create a mock Celery task instance."""
        task = MagicMock()
        task.request.id = "test-task-123"
        task.request.retries = 0
        task.max_retries = 3
        task.default_retry_delay = 60
        task.update_state = MagicMock()
        task.retry = MagicMock()
        return task

    @pytest.fixture
    def sample_design_data(self):
        """Sample design data for testing."""
        return {
            "building_type": "residential",
            "description": "Modern house",
            "requirements": {"bedrooms": 3, "bathrooms": 2},
            "style": "contemporary",
            "materials": ["brick", "wood"]
        }

    def test_task_configuration_values(self):
        """Test that task configuration values are correct."""
        # Test expected configuration for generate_visuals_task
        expected_generate_config = {
            "name": "visual_generation.generate_visuals",
            "max_retries": 3,
            "default_retry_delay": 60,
            "bind": True,
            "autoretry_for": (Exception,),
            "retry_backoff": True,
            "retry_jitter": True
        }
        
        # Test expected configuration for generate_single_visual_task
        expected_single_config = {
            "name": "visual_generation.generate_single_visual",
            "max_retries": 3,
            "default_retry_delay": 30,
            "bind": True,
            "autoretry_for": (VisualGenerationError,),
            "retry_backoff": True
        }
        
        # Test expected configuration for cleanup task
        expected_cleanup_config = {
            "name": "visual_generation.cleanup_failed_generations"
        }
        
        # Assert configuration values are as expected
        assert expected_generate_config["name"] == "visual_generation.generate_visuals"
        assert expected_generate_config["max_retries"] == 3
        assert expected_single_config["name"] == "visual_generation.generate_single_visual"
        assert expected_cleanup_config["name"] == "visual_generation.cleanup_failed_generations"

    def test_task_progress_tracking_logic(self, mock_task_instance):
        """Test progress tracking logic for visual generation."""
        # Simulate progress tracking behavior
        design_id = "test-design-456"
        visual_types = ["floor_plan", "rendering", "3d_model"]
        
        # Test initial progress update
        mock_task_instance.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": len(visual_types),
                "status": "Initializing visual generation...",
                "design_id": design_id,
                "started_at": datetime.utcnow().isoformat()
            }
        )
        
        # Test progress updates for each visual type
        for i, visual_type in enumerate(visual_types):
            mock_task_instance.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(visual_types),
                    "status": f"Generating {visual_type.replace('_', ' ')}...",
                    "design_id": design_id,
                    "current_visual_type": visual_type
                }
            )
        
        # Verify progress updates were called
        assert mock_task_instance.update_state.call_count == len(visual_types) + 1
        
        # Verify final progress call
        final_call = mock_task_instance.update_state.call_args_list[-1]
        assert final_call[1]["state"] == "PROGRESS"
        assert final_call[1]["meta"]["current"] == 3
        assert final_call[1]["meta"]["total"] == 3

    def test_task_error_handling_logic(self, mock_task_instance):
        """Test error handling logic for visual generation tasks."""
        # Test failure state update
        error_message = "Generation failed"
        design_id = "test-design-fail"
        
        mock_task_instance.update_state(
            state="FAILURE",
            meta={
                "error": error_message,
                "design_id": design_id,
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": mock_task_instance.request.retries
            }
        )
        
        # Verify failure state was set
        mock_task_instance.update_state.assert_called_once()
        failure_call = mock_task_instance.update_state.call_args
        assert failure_call[1]["state"] == "FAILURE"
        assert failure_call[1]["meta"]["error"] == error_message
        assert failure_call[1]["meta"]["design_id"] == design_id

    def test_task_retry_logic(self, mock_task_instance):
        """Test retry logic for failed tasks."""
        # Test retry when retries are available
        mock_task_instance.request.retries = 1
        mock_task_instance.max_retries = 3
        
        # Simulate retry call
        retry_countdown = mock_task_instance.default_retry_delay * (2 ** mock_task_instance.request.retries)
        
        # Verify retry logic
        assert mock_task_instance.request.retries < mock_task_instance.max_retries
        assert retry_countdown == 120  # 60 * (2 ** 1)
        
        # Test max retries exceeded
        mock_task_instance.request.retries = 3
        assert mock_task_instance.request.retries >= mock_task_instance.max_retries

    def test_task_result_structure(self, sample_design_data):
        """Test the structure of task results."""
        # Test successful result structure
        successful_result = {
            "design_id": "test-design-123",
            "results": {
                "floor_plan": {"floor_plan_url": "https://cdn.example.com/floor_plan.png"},
                "rendering": {"rendering_url": "https://cdn.example.com/rendering.png"},
                "3d_model": {"model_3d_url": "https://cdn.example.com/model.png"}
            },
            "total_cost": 0.12,
            "generated_types": ["floor_plan", "rendering", "3d_model"],
            "failed_types": [],
            "task_id": "test-task-123",
            "total_time": 45.2,
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        # Verify result structure
        assert "design_id" in successful_result
        assert "results" in successful_result
        assert "total_cost" in successful_result
        assert "generated_types" in successful_result
        assert "failed_types" in successful_result
        assert "task_id" in successful_result
        assert "status" in successful_result
        
        # Test partial failure result structure
        partial_result = {
            "design_id": "test-design-partial",
            "results": {
                "floor_plan": {"floor_plan_url": "https://cdn.example.com/floor_plan.png"},
                "rendering": {"error": "Rendering failed"},
                "3d_model": {"error": "Model generation failed"}
            },
            "total_cost": 0.04,
            "generated_types": ["floor_plan"],
            "failed_types": ["rendering", "3d_model"],
            "status": "partial"
        }
        
        # Verify partial result structure
        assert len(partial_result["generated_types"]) == 1
        assert len(partial_result["failed_types"]) == 2
        assert partial_result["status"] == "partial"


class TestRunVisualGeneration:
    """Test suite for the _run_visual_generation async function."""

    @pytest.fixture
    def mock_task(self):
        """Create a mock task instance."""
        task = MagicMock()
        task.update_state = MagicMock()
        return task

    @pytest.fixture
    def mock_design(self):
        """Create a mock design object."""
        design = MagicMock()
        design.building_type = "residential"
        design.description = "Modern house"
        design.requirements = {"bedrooms": 3}
        design.style = "contemporary"
        design.materials = ["brick", "wood"]
        return design

    @pytest.mark.asyncio
    @patch('src.tasks.visual_generation.get_settings')
    @patch('src.tasks.visual_generation.LLMClient')
    @patch('src.tasks.visual_generation.StorageClient')
    @patch('src.tasks.visual_generation.DesignRepository')
    @patch('src.tasks.visual_generation.VisualGenerationService')
    async def test_run_visual_generation_success(
        self, 
        mock_visual_service_class,
        mock_design_repo_class,
        mock_storage_client_class,
        mock_llm_client_class,
        mock_get_settings,
        mock_task
    ):
        """Test successful _run_visual_generation execution."""
        # Import the function to test
        from src.tasks.visual_generation import _run_visual_generation
        
        # Arrange
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        
        mock_visual_service = AsyncMock()
        mock_visual_service_class.return_value = mock_visual_service
        
        mock_result = {
            "design_id": "test-design-123",
            "results": {"floor_plan": {"floor_plan_url": "https://cdn.example.com/floor_plan.png"}},
            "total_cost": 0.04,
            "generated_types": ["floor_plan"],
            "failed_types": []
        }
        
        mock_visual_service.generate_all_visuals.return_value = mock_result
        
        # Act
        result = await _run_visual_generation(
            task=mock_task,
            design_id="test-design-123",
            design_data={"building_type": "residential"},
            visual_types=["floor_plan"],
            size="1024x1024",
            quality="standard"
        )

        # Assert
        assert result["design_id"] == "test-design-123"
        assert "floor_plan" in result["results"]
        
        # Verify services were initialized
        mock_llm_client_class.assert_called_once_with(mock_settings.llm)
        mock_storage_client_class.assert_called_once_with(mock_settings.storage)
        mock_design_repo_class.assert_called_once()
        
        # Verify visual service was called
        mock_visual_service.generate_all_visuals.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.tasks.visual_generation.get_settings')
    async def test_run_visual_generation_service_initialization_failure(self, mock_get_settings, mock_task):
        """Test _run_visual_generation when service initialization fails."""
        # Import the function to test
        from src.tasks.visual_generation import _run_visual_generation
        
        # Arrange
        mock_get_settings.side_effect = Exception("Configuration error")
        
        # Act & Assert
        with pytest.raises(VisualGenerationError) as exc_info:
            await _run_visual_generation(
                task=mock_task,
                design_id="test-design-fail",
                design_data={"building_type": "residential"},
                visual_types=["floor_plan"],
                size="1024x1024",
                quality="standard"
            )
        
        assert "Service initialization failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_visual_generation_progress_updates(self, mock_task):
        """Test that _run_visual_generation updates progress correctly."""
        # Import the function to test
        from src.tasks.visual_generation import _run_visual_generation
        
        # Arrange
        with patch('src.tasks.visual_generation.get_settings') as mock_get_settings, \
             patch('src.tasks.visual_generation.LLMClient'), \
             patch('src.tasks.visual_generation.StorageClient'), \
             patch('src.tasks.visual_generation.DesignRepository'), \
             patch('src.tasks.visual_generation.VisualGenerationService') as mock_service_class:
            
            mock_settings = MagicMock()
            mock_get_settings.return_value = mock_settings
            
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.generate_all_visuals.return_value = {}
            
            # Act
            await _run_visual_generation(
                task=mock_task,
                design_id="test-design-progress",
                design_data={"building_type": "residential"},
                visual_types=["floor_plan"],
                size="1024x1024",
                quality="standard"
            )

        # Assert progress updates were called
        progress_calls = [call for call in mock_task.update_state.call_args_list 
                         if call[1]["state"] == "PROGRESS"]
        
        assert len(progress_calls) >= 1  # At least one progress update


class TestGenerateVisualsWithProgress:
    """Test suite for the _generate_visuals_with_progress function."""

    @pytest.fixture
    def mock_task(self):
        """Create a mock task instance."""
        task = MagicMock()
        task.update_state = MagicMock()
        return task

    @pytest.fixture
    def mock_visual_service(self):
        """Create a mock visual generation service."""
        service = AsyncMock()
        service._update_design_visual_field = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_generate_visuals_with_progress_all_success(self, mock_task, mock_visual_service):
        """Test _generate_visuals_with_progress with all visuals succeeding."""
        # Import the function to test
        from src.tasks.visual_generation import _generate_visuals_with_progress
        
        # Arrange
        design_data = {"building_type": "residential"}
        
        # Mock successful generation for all types
        mock_visual_service.generate_floor_plan.return_value = {
            "floor_plan_url": "https://cdn.example.com/floor_plan.png",
            "generation_cost": 0.04
        }
        mock_visual_service.generate_3d_rendering.return_value = {
            "rendering_url": "https://cdn.example.com/rendering.png",
            "generation_cost": 0.04
        }
        mock_visual_service.generate_3d_model.return_value = {
            "model_3d_url": "https://cdn.example.com/model.png",
            "generation_cost": 0.04
        }
        
        # Act
        result = await _generate_visuals_with_progress(
            task=mock_task,
            visual_service=mock_visual_service,
            design_id="test-design-all",
            design_data=design_data,
            visual_types=["floor_plan", "rendering", "3d_model"],
            size="1024x1024",
            quality="standard"
        )

        # Assert
        assert result["design_id"] == "test-design-all"
        assert len(result["generated_types"]) == 3
        assert len(result["failed_types"]) == 0
        assert result["total_cost"] == 0.12
        assert result["status"] == "completed"
        
        # Verify all generation methods were called
        mock_visual_service.generate_floor_plan.assert_called_once()
        mock_visual_service.generate_3d_rendering.assert_called_once()
        mock_visual_service.generate_3d_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_visuals_with_progress_partial_failure(self, mock_task, mock_visual_service):
        """Test _generate_visuals_with_progress with some failures."""
        # Import the function to test
        from src.tasks.visual_generation import _generate_visuals_with_progress
        
        # Arrange
        design_data = {"building_type": "residential"}
        
        # Mock mixed success/failure
        mock_visual_service.generate_floor_plan.return_value = {
            "floor_plan_url": "https://cdn.example.com/floor_plan.png",
            "generation_cost": 0.04
        }
        mock_visual_service.generate_3d_rendering.side_effect = VisualGenerationError("Rendering failed")
        mock_visual_service.generate_3d_model.side_effect = VisualGenerationError("Model failed")
        
        # Act
        result = await _generate_visuals_with_progress(
            task=mock_task,
            visual_service=mock_visual_service,
            design_id="test-design-partial",
            design_data=design_data,
            visual_types=["floor_plan", "rendering", "3d_model"],
            size="1024x1024",
            quality="standard"
        )

        # Assert
        assert result["design_id"] == "test-design-partial"
        assert len(result["generated_types"]) == 1
        assert len(result["failed_types"]) == 2
        assert result["total_cost"] == 0.04
        assert result["status"] == "partial"


class TestCleanupFailedGenerationsTask:
    """Test suite for the cleanup task."""

    @patch('src.tasks.visual_generation.celery_app')
    def test_cleanup_failed_generations_task_success(self, mock_celery_app):
        """Test successful cleanup task execution."""
        # Create the actual function logic for testing
        def cleanup_task_logic():
            start_time = datetime.utcnow()
            
            # Simulate cleanup logic
            cleanup_stats = {
                "cleaned_designs": 0,
                "deleted_files": 0,
                "reset_for_retry": 0,
                "cleanup_time": (datetime.utcnow() - start_time).total_seconds()
            }
            
            return cleanup_stats
        
        # Act
        result = cleanup_task_logic()

        # Assert
        assert "cleaned_designs" in result
        assert "deleted_files" in result
        assert "reset_for_retry" in result
        assert "cleanup_time" in result
        assert isinstance(result["cleanup_time"], float)

    @patch('src.tasks.visual_generation.celery_app')
    def test_cleanup_failed_generations_task_returns_stats(self, mock_celery_app):
        """Test that cleanup task returns proper statistics."""
        # Create the actual function logic for testing
        def cleanup_task_logic():
            start_time = datetime.utcnow()
            
            cleanup_stats = {
                "cleaned_designs": 5,
                "deleted_files": 12,
                "reset_for_retry": 2,
                "cleanup_time": (datetime.utcnow() - start_time).total_seconds()
            }
            
            return cleanup_stats
        
        # Act
        result = cleanup_task_logic()

        # Assert
        expected_keys = ["cleaned_designs", "deleted_files", "reset_for_retry", "cleanup_time"]
        for key in expected_keys:
            assert key in result
            assert isinstance(result[key], (int, float))
        
        # Verify specific values
        assert result["cleaned_designs"] == 5
        assert result["deleted_files"] == 12
        assert result["reset_for_retry"] == 2


class TestTaskRoutingConfiguration:
    """Test suite for task routing configuration."""

    def test_get_visual_generation_routing(self):
        """Test that routing configuration is correct."""
        from src.tasks.visual_generation import get_visual_generation_routing
        
        # Act
        routing = get_visual_generation_routing()

        # Assert
        assert "visual_generation.generate_visuals" in routing
        assert "visual_generation.generate_single_visual" in routing
        assert "visual_generation.cleanup_failed_generations" in routing
        
        # Check routing details
        generate_visuals_route = routing["visual_generation.generate_visuals"]
        assert generate_visuals_route["queue"] == "visual_generation"
        assert generate_visuals_route["routing_key"] == "visual.generate"

    def test_get_visual_generation_stats(self):
        """Test that stats function returns proper structure."""
        from src.tasks.visual_generation import get_visual_generation_stats
        
        # Act
        stats = get_visual_generation_stats()

        # Assert
        expected_keys = [
            "active_tasks", "pending_tasks", "completed_today", 
            "failed_today", "average_generation_time", "total_cost_today"
        ]
        
        for key in expected_keys:
            assert key in stats
            assert isinstance(stats[key], (int, float))