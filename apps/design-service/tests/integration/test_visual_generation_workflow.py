"""
End-to-end integration tests for visual generation workflows.

Tests cover complete workflows:
- Design creation → visual generation → status tracking → completion
- Error scenarios and recovery mechanisms
- Concurrent generation requests
- Full system integration with Redis/Celery infrastructure
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from src.models.design import Design

from tests.factories import DesignFactory


class TestCompleteVisualGenerationWorkflow:
    """Tests for complete visual generation workflow from start to finish."""

    @patch.dict(
        os.environ,
        {
            "LLM_OPENAI_API_KEY": "test-api-key",
            "LLM_OPENAI_MODEL": "gpt-4",
            "STORAGE_S3_BUCKET": "test-bucket",
            "STORAGE_S3_REGION": "us-east-1",
            "REDIS_URL": "redis://localhost:6379/0",
        },
    )
    @patch("src.api.v1.routes.designs.generate_visuals_task")
    @patch("src.services.design_generator.DesignGeneratorService.generate_design")
    def test_complete_workflow_design_creation_to_completion(
        self,
        mock_generate_design,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test complete workflow: design creation → visual generation → completion."""
        # Step 1: Create design with visual generation enabled
        design = DesignFactory.create(
            project_id=1,
            name="Complete Workflow Test",
            description="A modern residential building for workflow testing",
            building_type="residential",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()
        mock_generate_design.return_value = design

        # Setup visual task mock
        task_id = str(uuid4())
        mock_task = AsyncMock()
        mock_task.id = task_id
        mock_visual_task.delay.return_value = mock_task

        # Step 1: Create design with visual generation
        create_response = client.post(
            "/api/v1/designs",
            json={
                "project_id": 1,
                "name": "Complete Workflow Test",
                "description": "A modern residential building for workflow testing",
                "building_type": "residential",
                "requirements": {"num_floors": 2, "total_area": 200.0},
                "generate_visuals": True,
            },
            headers=auth_headers,
        )

        # Verify design creation
        assert create_response.status_code == status.HTTP_201_CREATED
        design_data = create_response.json()
        design_id = design_data["id"]
        assert design_data["name"] == "Complete Workflow Test"

        # Verify visual generation task was triggered
        mock_visual_task.delay.assert_called_once()
        call_args = mock_visual_task.delay.call_args
        assert call_args[1]["design_id"] == str(design_id)
        assert call_args[1]["visual_types"] == ["floor_plan", "rendering", "3d_model"]

        # Step 2: Check initial visual status (should be pending)
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "PENDING"
            mock_task_status.result = None
            mock_task_status.info = None

            status_response = client.get(
                f"/api/v1/designs/{design_id}/visual-status",
                headers=auth_headers,
            )

            assert status_response.status_code == status.HTTP_200_OK
            status_data = status_response.json()
            assert status_data["status"] in ["pending", "not_requested"]

        # Step 3: Simulate task progress
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "PROGRESS"
            mock_task_status.result = None
            mock_task_status.info = {
                "current_step": "generating_floor_plan",
                "progress": 33,
                "message": "Generating floor plan...",
                "completed_visuals": ["floor_plan"],
            }

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "PROGRESS"
            assert task_data["progress"] == 33
            assert task_data["current_step"] == "generating_floor_plan"

        # Step 4: Simulate task completion
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "SUCCESS"
            mock_task_status.result = {
                "floor_plan_url": "https://cdn.example.com/designs/123/floor_plan.jpg",
                "rendering_url": "https://cdn.example.com/designs/123/rendering.jpg",
                "model_file_url": "https://cdn.example.com/designs/123/model.obj",
                "generation_cost": 0.15,
                "total_time": 45.2,
            }
            mock_task_status.info = None
            mock_task_status.date_done = datetime.now(timezone.utc).isoformat()

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "SUCCESS"
            assert "floor_plan_url" in task_data["result"]
            assert "rendering_url" in task_data["result"]
            assert "model_file_url" in task_data["result"]

        # Step 5: Verify final design state with completed visuals
        # Update design in database to simulate completion
        db_session.query(Design).filter_by(id=design_id).update(
            {
                "visual_generation_status": "completed",
                "floor_plan_url": "https://cdn.example.com/designs/123/floor_plan.jpg",
                "rendering_url": "https://cdn.example.com/designs/123/rendering.jpg",
                "model_file_url": "https://cdn.example.com/designs/123/model.obj",
                "visual_generated_at": datetime.now(timezone.utc),
            }
        )
        db_session.commit()

        final_status_response = client.get(
            f"/api/v1/designs/{design_id}/visual-status",
            headers=auth_headers,
        )

        assert final_status_response.status_code == status.HTTP_200_OK
        final_status_data = final_status_response.json()
        assert final_status_data["status"] == "completed"
        assert final_status_data["visuals"]["floor_plan"]["available"] is True
        assert final_status_data["visuals"]["rendering"]["available"] is True
        assert final_status_data["visuals"]["model_3d"]["available"] is True
        assert final_status_data["progress"]["percentage"] == 100.0

        # Step 6: Verify design retrieval includes visual URLs
        design_response = client.get(
            f"/api/v1/designs/{design_id}",
            headers=auth_headers,
        )

        assert design_response.status_code == status.HTTP_200_OK
        design_data = design_response.json()
        assert (
            design_data["floor_plan_url"]
            == "https://cdn.example.com/designs/123/floor_plan.jpg"
        )
        assert (
            design_data["rendering_url"]
            == "https://cdn.example.com/designs/123/rendering.jpg"
        )
        assert (
            design_data["model_file_url"]
            == "https://cdn.example.com/designs/123/model.obj"
        )

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_on_demand_visual_generation_workflow(
        self,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test on-demand visual generation workflow for existing design."""
        # Step 1: Create design without initial visual generation
        design = DesignFactory.create(
            project_id=1,
            name="On-Demand Test Design",
            description="A commercial building for on-demand testing",
            building_type="commercial",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Step 2: Request on-demand visual generation
        task_id = str(uuid4())
        mock_task = AsyncMock()
        mock_task.id = task_id
        mock_visual_task.delay.return_value = mock_task

        generate_response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={
                "visual_types": ["floor_plan", "rendering"],
                "size": "1024x1024",
                "quality": "standard",
                "priority": "normal",
            },
            headers=auth_headers,
        )

        # Verify generation request accepted
        assert generate_response.status_code == status.HTTP_202_ACCEPTED
        generate_data = generate_response.json()
        assert generate_data["task_id"] == task_id
        assert generate_data["visual_types"] == ["floor_plan", "rendering"]
        assert generate_data["status"] == "pending"

        # Step 3: Track task progress
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "PROGRESS"
            mock_task_status.result = None
            mock_task_status.info = {
                "current_step": "generating_rendering",
                "progress": 75,
                "message": "Generating 3D rendering...",
            }

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "PROGRESS"
            assert task_data["progress"] == 75

        # Step 4: Verify completion
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "SUCCESS"
            mock_task_status.result = {
                "floor_plan_url": "https://cdn.example.com/designs/456/floor_plan.jpg",
                "rendering_url": "https://cdn.example.com/designs/456/rendering.jpg",
            }
            mock_task_status.info = None

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "SUCCESS"
            assert len(task_data["result"]) == 2  # Only 2 visuals requested


class TestVisualGenerationErrorScenarios:
    """Tests for error scenarios and recovery mechanisms in visual generation."""

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_task_failure_and_retry_workflow(
        self,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test workflow when visual generation task fails and is retried."""
        # Create design
        design = DesignFactory.create(
            project_id=1,
            name="Failure Test Design",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Setup task mock
        task_id = str(uuid4())
        mock_task = AsyncMock()
        mock_task.id = task_id
        mock_visual_task.delay.return_value = mock_task

        # Request visual generation
        generate_response = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        assert generate_response.status_code == status.HTTP_202_ACCEPTED

        # Step 1: Simulate task failure
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "FAILURE"
            mock_task_status.result = Exception("OpenAI API rate limit exceeded")
            mock_task_status.info = None
            mock_task_status.traceback = "Traceback..."

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "FAILURE"
            assert "rate limit" in task_data["error"]

        # Step 2: Simulate retry state
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "RETRY"
            mock_task_status.result = Exception("Temporary failure")
            mock_task_status.info = {
                "retry_count": 1,
                "max_retries": 3,
                "next_retry": "2024-01-01T12:05:00Z",
            }

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "RETRY"
            assert task_data["retry_count"] == 1
            assert task_data["max_retries"] == 3

        # Step 3: Simulate eventual success after retry
        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task_status = Mock()
            mock_result.return_value = mock_task_status
            mock_task_status.state = "SUCCESS"
            mock_task_status.result = {
                "floor_plan_url": "https://cdn.example.com/designs/retry/floor_plan.jpg",
                "rendering_url": "https://cdn.example.com/designs/retry/rendering.jpg",
                "model_file_url": "https://cdn.example.com/designs/retry/model.obj",
            }
            mock_task_status.info = None

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_200_OK
            task_data = task_response.json()
            assert task_data["state"] == "SUCCESS"
            assert len(task_data["result"]) == 3

    def test_partial_failure_workflow(
        self,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test workflow when some visuals succeed and others fail."""
        # Create design with partial visual completion
        design = DesignFactory.create(
            project_id=1,
            name="Partial Failure Test",
            created_by=test_user_id,
            visual_generation_status="processing",
            floor_plan_url="https://cdn.example.com/designs/partial/floor_plan.jpg",
            rendering_url="https://cdn.example.com/designs/partial/rendering.jpg",
            model_file_url=None,  # Failed to generate
            visual_generation_error="3D model generation failed: insufficient detail",
        )
        db_session.commit()

        # Check visual status shows partial completion
        status_response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert status_data["status"] == "processing"
        assert status_data["visuals"]["floor_plan"]["available"] is True
        assert status_data["visuals"]["rendering"]["available"] is True
        assert status_data["visuals"]["model_3d"]["available"] is False
        assert status_data["progress"]["completed_count"] == 2
        assert status_data["progress"]["total_count"] == 3
        assert status_data["progress"]["percentage"] == 66.7

    def test_celery_connection_failure_workflow(
        self,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test workflow when Celery/Redis is unavailable."""
        # Create design
        design = DesignFactory.create(
            project_id=1,
            name="Celery Failure Test",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Simulate Celery connection failure
        with patch("src.api.v1.routes.designs.generate_visuals_task") as mock_task:
            mock_task.delay.side_effect = Exception("Redis connection failed")

            generate_response = client.post(
                f"/api/v1/designs/{design.id}/generate-visuals",
                json={},
                headers=auth_headers,
            )

            # Should return server error
            assert (
                generate_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            error_data = generate_response.json()
            assert "Failed to start visual generation" in error_data["detail"]

        # Verify design status shows failure (since task creation failed)
        status_response = client.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )

        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        # Status could be "failed" if the task creation failure was recorded
        assert status_data["status"] in ["not_requested", "failed"]

    def test_task_status_service_unavailable(
        self,
        client,
        auth_headers,
    ):
        """Test task status endpoint when Celery service is unavailable."""
        task_id = str(uuid4())

        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_result.side_effect = Exception("Celery connection failed")

            task_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers,
            )

            assert task_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            error_data = task_response.json()
            assert "Task queue service unavailable" in error_data["detail"]


class TestConcurrentVisualGeneration:
    """Tests for concurrent visual generation requests and race conditions."""

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_concurrent_generation_requests_same_design(
        self,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test concurrent visual generation requests for the same design."""
        # Create design
        design = DesignFactory.create(
            project_id=1,
            name="Concurrent Test Design",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Setup task mock
        task_id = str(uuid4())
        mock_task = AsyncMock()
        mock_task.id = task_id
        mock_visual_task.delay.return_value = mock_task

        # First request should succeed
        response1 = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        assert response1.status_code == status.HTTP_202_ACCEPTED

        # Update design status to processing to simulate first request
        db_session.query(Design).filter_by(id=design.id).update(
            {"visual_generation_status": "processing"}
        )
        db_session.commit()

        # Second concurrent request should be rejected
        response2 = client.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        assert response2.status_code == status.HTTP_409_CONFLICT
        error_data = response2.json()
        assert "already in progress" in error_data["detail"].lower()

    @patch("src.api.v1.routes.designs.generate_visuals_task")
    def test_concurrent_generation_different_designs(
        self,
        mock_visual_task,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test concurrent visual generation for different designs."""
        # Create multiple designs
        design1 = DesignFactory.create(
            project_id=1,
            name="Concurrent Design 1",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        design2 = DesignFactory.create(
            project_id=1,
            name="Concurrent Design 2",
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Setup task mocks
        task_id1 = str(uuid4())
        task_id2 = str(uuid4())
        mock_task1 = AsyncMock()
        mock_task1.id = task_id1
        mock_task2 = AsyncMock()
        mock_task2.id = task_id2
        mock_visual_task.delay.side_effect = [mock_task1, mock_task2]

        # Both requests should succeed
        response1 = client.post(
            f"/api/v1/designs/{design1.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        response2 = client.post(
            f"/api/v1/designs/{design2.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )

        assert response1.status_code == status.HTTP_202_ACCEPTED
        assert response2.status_code == status.HTTP_202_ACCEPTED

        # Verify different task IDs
        data1 = response1.json()
        data2 = response2.json()
        assert data1["task_id"] != data2["task_id"]

        # Verify both tasks were created
        assert mock_visual_task.delay.call_count == 2


class TestVisualGenerationSystemIntegration:
    """Tests for integration with external systems and infrastructure."""

    def test_storage_integration_workflow(
        self,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test integration with storage system for visual URLs."""
        # Create design with completed visuals
        design = DesignFactory.create(
            project_id=1,
            name="Storage Integration Test",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/designs/storage/floor_plan.jpg",
            rendering_url="https://cdn.example.com/designs/storage/rendering.jpg",
            model_file_url="https://cdn.example.com/designs/storage/model.obj",
        )
        db_session.commit()

        # Verify URLs are accessible through API
        design_response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert design_response.status_code == status.HTTP_200_OK
        design_data = design_response.json()

        # Verify URL format and accessibility
        assert design_data["floor_plan_url"].startswith("https://")
        assert design_data["rendering_url"].startswith("https://")
        assert design_data["model_file_url"].startswith("https://")

        # Verify URLs contain expected path structure
        assert "/designs/" in design_data["floor_plan_url"]
        assert "/designs/" in design_data["rendering_url"]
        assert "/designs/" in design_data["model_file_url"]

    def test_authentication_integration_workflow(
        self,
        client_no_auth,
        db_session,
        test_user_id,
    ):
        """Test authentication integration across visual generation workflow."""
        # Create design
        design = DesignFactory.create(
            project_id=1,
            name="Auth Integration Test",
            created_by=test_user_id,
            visual_generation_status="completed",
        )
        db_session.commit()

        # Test without authentication
        response = client_no_auth.get(f"/api/v1/designs/{design.id}/visual-status")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = client_no_auth.post(
            f"/api/v1/designs/{design.id}/generate-visuals", json={}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        task_id = str(uuid4())
        response = client_no_auth.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_project_access_integration_workflow(
        self,
        client_no_project_access,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test project access control integration across workflow."""
        # Create design for different project but owned by different user
        # Note: visual-status endpoint currently only checks design ownership, not project access
        design = DesignFactory.create(
            project_id=999,  # Different project
            name="Access Control Test",
            created_by=999,  # Different user (this will trigger 403)
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # visual-status endpoint checks design ownership, not project access
        response = client_no_project_access.get(
            f"/api/v1/designs/{design.id}/visual-status",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # generate-visuals endpoint does check project access
        response = client_no_project_access.post(
            f"/api/v1/designs/{design.id}/generate-visuals",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestVisualGenerationPerformance:
    """Tests for performance aspects of visual generation workflow."""

    def test_large_batch_visual_generation(
        self,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test performance with large batch of visual generation requests."""
        # Create multiple designs
        designs = DesignFactory.create_batch(
            10,
            project_id=1,
            created_by=test_user_id,
            visual_generation_status="not_requested",
        )
        db_session.commit()

        # Track response times
        response_times = []

        with patch("src.api.v1.routes.designs.generate_visuals_task") as mock_task:
            mock_task.delay.return_value = AsyncMock(id=str(uuid4()))

            for design in designs:
                start_time = time.time()

                response = client.post(
                    f"/api/v1/designs/{design.id}/generate-visuals",
                    json={},
                    headers=auth_headers,
                )

                end_time = time.time()
                response_times.append(end_time - start_time)

                assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify reasonable response times (should be under 1 second each)
        assert all(rt < 1.0 for rt in response_times)
        assert len(response_times) == 10

    def test_task_status_polling_performance(
        self,
        client,
        auth_headers,
    ):
        """Test performance of rapid task status polling."""
        task_id = str(uuid4())

        with patch("src.api.v1.routes.tasks.AsyncResult") as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "PROGRESS"
            mock_task.result = None
            mock_task.info = {"progress": 50}

            # Simulate rapid polling
            response_times = []
            for _ in range(20):
                start_time = time.time()

                response = client.get(
                    f"/api/v1/tasks/{task_id}",
                    headers=auth_headers,
                )

                end_time = time.time()
                response_times.append(end_time - start_time)

                assert response.status_code == status.HTTP_200_OK

        # Verify consistent performance under load
        assert all(rt < 0.5 for rt in response_times)  # Under 500ms each
        assert len(response_times) == 20


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing functionality."""

    def test_existing_designs_without_visual_fields(
        self,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test that existing designs without visual fields work correctly."""
        # Create design without visual fields (simulating old data)
        design = DesignFactory.create(
            project_id=1,
            name="Legacy Design",
            created_by=test_user_id,
            visual_generation_status="not_requested",
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
        )
        db_session.commit()

        # Should be able to retrieve design
        response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Legacy Design"
        assert data.get("visual_generation_status") == "not_requested"

        # Should be able to request visual generation
        with patch("src.api.v1.routes.designs.generate_visuals_task") as mock_task:
            mock_task.delay.return_value = AsyncMock(id=str(uuid4()))

            generate_response = client.post(
                f"/api/v1/designs/{design.id}/generate-visuals",
                json={},
                headers=auth_headers,
            )

            assert generate_response.status_code == status.HTTP_202_ACCEPTED

    def test_design_crud_operations_with_visuals(
        self,
        client,
        db_session,
        auth_headers,
        test_user_id,
    ):
        """Test that standard CRUD operations work with visual fields."""
        # Create design with visuals
        design = DesignFactory.create(
            project_id=1,
            name="CRUD Test Design",
            created_by=test_user_id,
            visual_generation_status="completed",
            floor_plan_url="https://cdn.example.com/floor_plan.jpg",
        )
        db_session.commit()

        # Update design (should preserve visual fields)
        update_response = client.put(
            f"/api/v1/designs/{design.id}",
            json={"name": "Updated CRUD Design"},
            headers=auth_headers,
        )

        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()
        assert data["name"] == "Updated CRUD Design"
        assert data["floor_plan_url"] == "https://cdn.example.com/floor_plan.jpg"

        # Delete design (soft delete should work)
        delete_response = client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify design is archived
        get_response = client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert get_response.status_code == status.HTTP_404_NOT_FOUND
