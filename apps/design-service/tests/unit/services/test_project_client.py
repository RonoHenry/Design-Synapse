"""Tests for ProjectClient service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.services.project_client import ProjectClient, ProjectAccessDeniedError


@pytest.fixture
def project_client():
    """Create a ProjectClient instance for testing."""
    return ProjectClient(base_url="http://localhost:8003/api/v1")


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    mock_client = MagicMock()
    mock_client.request = AsyncMock()
    return mock_client


class TestVerifyProjectAccess:
    """Tests for verify_project_access method."""

    @pytest.mark.asyncio
    async def test_verify_project_access_user_is_member(self, project_client, mock_httpx_client):
        """Test verify_project_access when user is a project member."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # Mock successful response (200 OK means user is a member)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "project_id": project_id,
            "user_id": user_id,
            "role": "member",
            "is_member": True
        }
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act
        result = await project_client.verify_project_access(project_id, user_id)
        
        # Assert
        assert result is True
        mock_httpx_client.request.assert_called_once_with(
            "GET",
            f"http://localhost:8003/api/v1/projects/{project_id}/members/{user_id}",
            timeout=30.0
        )

    @pytest.mark.asyncio
    async def test_verify_project_access_user_not_member_404(self, project_client, mock_httpx_client):
        """Test verify_project_access when user is not a member (404 response)."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # Mock 404 response (user not found in project members)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(ProjectAccessDeniedError) as exc_info:
            await project_client.verify_project_access(project_id, user_id)
        
        assert "not a member" in str(exc_info.value).lower()
        assert str(project_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_project_access_user_not_member_403(self, project_client, mock_httpx_client):
        """Test verify_project_access when user is forbidden (403 response)."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # Mock 403 response (user forbidden from accessing project)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(ProjectAccessDeniedError) as exc_info:
            await project_client.verify_project_access(project_id, user_id)
        
        assert "access denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_verify_project_access_project_not_found(self, project_client, mock_httpx_client):
        """Test verify_project_access when project doesn't exist."""
        # Arrange
        project_id = 999
        user_id = 10
        
        # Mock 404 response for non-existent project
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Project not found",
            request=MagicMock(),
            response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(ProjectAccessDeniedError):
            await project_client.verify_project_access(project_id, user_id)


class TestGetProjectDetails:
    """Tests for get_project_details method."""

    @pytest.mark.asyncio
    async def test_get_project_details_success(self, project_client, mock_httpx_client):
        """Test get_project_details returns project data successfully."""
        # Arrange
        project_id = 1
        expected_project = {
            "id": project_id,
            "name": "Test Project",
            "description": "A test project",
            "owner_id": 5,
            "status": "active",
            "created_at": "2025-01-01T00:00:00Z"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_project
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act
        result = await project_client.get_project_details(project_id)
        
        # Assert
        assert result == expected_project
        mock_httpx_client.request.assert_called_once_with(
            "GET",
            f"http://localhost:8003/api/v1/projects/{project_id}",
            timeout=30.0
        )

    @pytest.mark.asyncio
    async def test_get_project_details_not_found(self, project_client, mock_httpx_client):
        """Test get_project_details when project doesn't exist."""
        # Arrange
        project_id = 999
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await project_client.get_project_details(project_id)


class TestHTTPErrorHandling:
    """Tests for HTTP error handling and retries."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, project_client, mock_httpx_client):
        """Test that client retries on timeout errors."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # First two attempts timeout, third succeeds
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"is_member": True}
        
        mock_httpx_client.request.side_effect = [
            httpx.TimeoutException("Request timeout"),
            httpx.TimeoutException("Request timeout"),
            mock_response_success
        ]
        
        project_client._client = mock_httpx_client
        
        # Act
        result = await project_client.verify_project_access(project_id, user_id)
        
        # Assert
        assert result is True
        assert mock_httpx_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, project_client, mock_httpx_client):
        """Test that client retries on connection errors."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # First attempt fails with connection error, second succeeds
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"is_member": True}
        
        mock_httpx_client.request.side_effect = [
            httpx.ConnectError("Connection failed"),
            mock_response_success
        ]
        
        project_client._client = mock_httpx_client
        
        # Act
        result = await project_client.verify_project_access(project_id, user_id)
        
        # Assert
        assert result is True
        assert mock_httpx_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_http_error(self, project_client, mock_httpx_client):
        """Test that client does not retry on HTTP errors (4xx, 5xx)."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # Mock 500 error - should not retry
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            await project_client.verify_project_access(project_id, user_id)
        
        # Should only be called once (no retries for HTTP errors)
        assert mock_httpx_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, project_client, mock_httpx_client):
        """Test that retry uses exponential backoff."""
        # Arrange
        project_id = 1
        user_id = 10
        
        # All attempts timeout
        mock_httpx_client.request.side_effect = httpx.TimeoutException("Timeout")
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await project_client.verify_project_access(project_id, user_id)
        
        # Should retry max_retries times
        assert mock_httpx_client.request.call_count == project_client.max_retries
        assert "failed after" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handle_500_error(self, project_client, mock_httpx_client):
        """Test handling of 500 Internal Server Error."""
        # Arrange
        project_id = 1
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        project_client._client = mock_httpx_client
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await project_client.get_project_details(project_id)
        
        assert exc_info.value.response.status_code == 500
