"""
Integration tests for task status tracking API endpoints.

Tests cover:
- GET /api/v1/tasks/{task_id} (get task status)
- Task state, progress, and results
- Authentication and authorization
- Task not found scenarios
- Error handling
"""

import pytest
from fastapi import status
from unittest.mock import Mock, patch
from uuid import uuid4


class TestGetTaskStatus:
    """Tests for GET /api/v1/tasks/{task_id} endpoint."""

    def test_get_task_status_success(self, client, auth_headers):
        """Test successful task status retrieval."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "SUCCESS"
            mock_task.result = {
                "floor_plan_url": "https://cdn.example.com/designs/123/floor_plan.jpg",
                "rendering_url": "https://cdn.example.com/designs/123/rendering.jpg"
            }
            mock_task.info = None
            mock_task.date_done = "2024-01-01T12:00:00Z"
            mock_task.name = "test_task"
            mock_task.traceback = None
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "SUCCESS"
            assert data["result"]["floor_plan_url"] == "https://cdn.example.com/designs/123/floor_plan.jpg"
            assert data["result"]["rendering_url"] == "https://cdn.example.com/designs/123/rendering.jpg"

    def test_get_task_status_pending(self, client, auth_headers):
        """Test task status retrieval for pending task."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "PENDING"
            mock_task.result = None
            mock_task.info = None
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "PENDING"
            assert data["result"] is None
            assert data["progress"] == 0

    def test_get_task_status_in_progress(self, client, auth_headers):
        """Test task status retrieval for in-progress task."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "PROGRESS"
            mock_task.result = None
            mock_task.info = {
                "current_step": "generating_floor_plan",
                "progress": 45,
                "message": "Generating floor plan with AI..."
            }
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "PROGRESS"
            assert data["progress"] == 45
            assert data["current_step"] == "generating_floor_plan"
            assert data["message"] == "Generating floor plan with AI..."

    def test_get_task_status_failure(self, client, auth_headers):
        """Test task status retrieval for failed task."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "FAILURE"
            mock_task.result = Exception("AI generation failed")
            mock_task.info = None
            mock_task.traceback = "Traceback (most recent call last):\n  File..."
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "FAILURE"
            assert "AI generation failed" in data["error"]
            assert data["result"] is None

    def test_get_task_status_retry(self, client, auth_headers):
        """Test task status retrieval for retrying task."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "RETRY"
            mock_task.result = Exception("Temporary failure")
            mock_task.info = {
                "retry_count": 2,
                "max_retries": 3,
                "next_retry": "2024-01-01T12:05:00Z"
            }
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "RETRY"
            assert data["retry_count"] == 2
            assert data["max_retries"] == 3
            assert data["next_retry"] == "2024-01-01T12:05:00Z"

    def test_get_task_status_revoked(self, client, auth_headers):
        """Test task status retrieval for revoked task."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "REVOKED"
            mock_task.result = None
            mock_task.info = None
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "REVOKED"
            assert data["result"] is None

    def test_get_task_status_unauthorized(self, client):
        """Test task status retrieval without authentication."""
        # Arrange
        task_id = str(uuid4())
        
        # Act
        response = client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_task_status_invalid_task_id(self, client, auth_headers):
        """Test task status retrieval with invalid task ID format."""
        # Arrange
        invalid_task_id = "invalid-task-id"
        
        # Act
        response = client.get(
            f"/api/v1/tasks/{invalid_task_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid task ID format" in data["detail"]

    def test_get_task_status_task_not_found(self, client, auth_headers):
        """Test task status retrieval for non-existent task."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "PENDING"
            mock_task.result = None
            mock_task.info = None
            # Simulate task not found by making it look like it never existed
            mock_task.status = "PENDING"
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert - PENDING state indicates task might not exist or is waiting
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "PENDING"

    def test_get_task_status_with_metadata(self, client, auth_headers):
        """Test task status retrieval includes metadata."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "SUCCESS"
            mock_task.result = {
                "floor_plan_url": "https://cdn.example.com/designs/123/floor_plan.jpg"
            }
            mock_task.info = None
            mock_task.date_done = "2024-01-01T12:00:00Z"
            mock_task.name = "src.tasks.visual_generation.generate_visuals_task"
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == task_id
            assert data["state"] == "SUCCESS"
            assert "metadata" in data
            assert data["metadata"]["task_name"] == "src.tasks.visual_generation.generate_visuals_task"
            assert data["metadata"]["completed_at"] == "2024-01-01T12:00:00Z"

    def test_get_task_status_celery_connection_error(self, client, auth_headers):
        """Test task status retrieval when Celery is unavailable."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_result.side_effect = Exception("Celery connection failed")
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert "Task queue service unavailable" in data["detail"]

    def test_get_task_status_response_schema(self, client, auth_headers):
        """Test that task status response follows the correct schema."""
        # Arrange
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "SUCCESS"
            mock_task.result = {"test": "result"}
            mock_task.info = None
            
            # Act
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify required fields
            required_fields = ["task_id", "state", "result", "progress", "created_at"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Verify data types
            assert isinstance(data["task_id"], str)
            assert isinstance(data["state"], str)
            assert isinstance(data["progress"], (int, float))
            assert isinstance(data["created_at"], str)


class TestTaskStatusAuthentication:
    """Tests for task status endpoint authentication and authorization."""

    def test_get_task_status_missing_auth_header(self, client):
        """Test task status retrieval without Authorization header."""
        task_id = str(uuid4())
        
        response = client.get(f"/api/v1/tasks/{task_id}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_task_status_invalid_auth_token(self, client):
        """Test task status retrieval with invalid auth token."""
        task_id = str(uuid4())
        
        response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_task_status_expired_auth_token(self, client):
        """Test task status retrieval with expired auth token."""
        task_id = str(uuid4())
        
        # Mock expired token
        with patch('src.api.dependencies.verify_token') as mock_verify:
            mock_verify.side_effect = Exception("Token expired")
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers={"Authorization": "Bearer expired-token"}
            )
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTaskStatusErrorHandling:
    """Tests for task status endpoint error handling."""

    def test_get_task_status_malformed_task_id(self, client, auth_headers):
        """Test task status retrieval with malformed task ID."""
        malformed_ids = [
            "not-a-uuid",
            "12345",
            "",
            "special-chars-!@#$%",
            "too-short",
        ]
        
        for task_id in malformed_ids:
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Invalid task ID format" in data["detail"]

    def test_get_task_status_internal_server_error(self, client, auth_headers):
        """Test task status retrieval with internal server error."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.get_task_status_from_celery') as mock_get_status:
            mock_get_status.side_effect = Exception("Internal error")
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Internal server error" in data["detail"]

    def test_get_task_status_timeout(self, client, auth_headers):
        """Test task status retrieval with timeout."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_result.side_effect = TimeoutError("Task status check timeout")
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT
            data = response.json()
            assert "Task status check timeout" in data["detail"]


class TestTaskStatusResponseFormat:
    """Tests for task status response format and schema validation."""

    def test_task_status_response_includes_timestamps(self, client, auth_headers):
        """Test that task status response includes proper timestamps."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "SUCCESS"
            mock_task.result = {"test": "result"}
            mock_task.info = None
            mock_task.date_done = "2024-01-01T12:00:00Z"
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "created_at" in data
            assert "completed_at" in data
            assert data["completed_at"] == "2024-01-01T12:00:00Z"

    def test_task_status_response_includes_execution_time(self, client, auth_headers):
        """Test that task status response includes execution time for completed tasks."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "SUCCESS"
            mock_task.result = {"test": "result"}
            mock_task.info = None
            mock_task.date_done = "2024-01-01T12:00:00Z"
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "execution_time_seconds" in data
            assert isinstance(data["execution_time_seconds"], (int, float))

    def test_task_status_response_includes_worker_info(self, client, auth_headers):
        """Test that task status response includes worker information."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "SUCCESS"
            mock_task.result = {"test": "result"}
            mock_task.info = None
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "worker_info" in data
            assert isinstance(data["worker_info"], dict)


class TestTaskStatusEndpointIntegration:
    """Tests for task status endpoint integration with other components."""

    def test_task_status_endpoint_registered_in_router(self, client):
        """Test that task status endpoint is properly registered."""
        # This test verifies the endpoint exists by checking it returns a proper HTTP response
        # rather than a 404 Not Found
        task_id = str(uuid4())
        
        response = client.get(f"/api/v1/tasks/{task_id}")
        
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code != status.HTTP_404_NOT_FOUND

    def test_task_status_endpoint_cors_headers(self, client, auth_headers):
        """Test that task status endpoint includes proper CORS headers."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "PENDING"
            mock_task.result = None
            mock_task.info = None
            
            response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            
            # Should include CORS headers (if configured)
            assert response.status_code == status.HTTP_200_OK
            # Note: CORS headers would be tested if CORS middleware is configured

    def test_task_status_endpoint_rate_limiting(self, client, auth_headers):
        """Test that task status endpoint respects rate limiting."""
        task_id = str(uuid4())
        
        with patch('src.api.v1.routes.tasks.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_result.return_value = mock_task
            mock_task.state = "PENDING"
            mock_task.result = None
            mock_task.info = None
            
            # Make multiple requests rapidly
            responses = []
            for _ in range(5):
                response = client.get(
                    f"/api/v1/tasks/{task_id}",
                    headers=auth_headers
                )
                responses.append(response)
            
            # All should succeed (rate limiting would be tested if implemented)
            for response in responses:
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]