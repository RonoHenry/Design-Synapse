"""Unit tests for project membership verification."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest
from src.integrations.project_service_client import ProjectServiceClient


class TestProjectMembershipVerification:
    """Tests for verify_project_membership method."""

    @pytest.fixture
    def client(self):
        """Create ProjectServiceClient instance."""
        return ProjectServiceClient(
            base_url="http://test-project-service",
            timeout=10.0,
        )

    @pytest.mark.asyncio
    async def test_verify_membership_user_is_member(self, client):
        """Test verifying membership when user is a member."""
        project_id = uuid4()
        user_id = uuid4()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"is_member": True}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.verify_project_membership(
                project_id=project_id,
                user_id=user_id,
                use_cache=False,
            )

            assert result is True
            mock_http_client.get.assert_called_once_with(
                f"/api/v1/projects/{project_id}/members/{user_id}"
            )

    @pytest.mark.asyncio
    async def test_verify_membership_user_not_member(self, client):
        """Test verifying membership when user is not a member."""
        project_id = uuid4()
        user_id = uuid4()

        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.verify_project_membership(
                project_id=project_id,
                user_id=user_id,
                use_cache=False,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_verify_membership_with_cache_hit(self, client):
        """Test verifying membership with cache hit."""
        project_id = uuid4()
        user_id = uuid4()

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"is_member": true}'
        client.redis_client = mock_redis

        result = await client.verify_project_membership(
            project_id=project_id,
            user_id=user_id,
            use_cache=True,
        )

        assert result is True
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_membership_caches_result(self, client):
        """Test that membership verification caches the result."""
        project_id = uuid4()
        user_id = uuid4()

        mock_response = Mock()
        mock_response.status_code = 200

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Cache miss
        client.redis_client = mock_redis

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.verify_project_membership(
                project_id=project_id,
                user_id=user_id,
                use_cache=True,
            )

            assert result is True
            # Verify cache was set
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 300  # 5 minute TTL for members

    @pytest.mark.asyncio
    async def test_verify_membership_handles_http_error(self, client):
        """Test handling HTTP errors during membership verification."""
        project_id = uuid4()
        user_id = uuid4()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.side_effect = httpx.HTTPError("Connection failed")
            mock_get_client.return_value = mock_http_client

            result = await client.verify_project_membership(
                project_id=project_id,
                user_id=user_id,
                use_cache=False,
            )

            # Should default to False on error for security
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_membership_handles_status_error(self, client):
        """Test handling HTTP status errors during membership verification."""
        project_id = uuid4()
        user_id = uuid4()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(httpx.HTTPStatusError):
                await client.verify_project_membership(
                    project_id=project_id,
                    user_id=user_id,
                    use_cache=False,
                )

    @pytest.mark.asyncio
    async def test_verify_membership_404_returns_false(self, client):
        """Test that 404 status returns False without raising exception."""
        project_id = uuid4()
        user_id = uuid4()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=Mock(),
            response=Mock(status_code=404),
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.side_effect = mock_response.raise_for_status
            mock_get_client.return_value = mock_http_client

            result = await client.verify_project_membership(
                project_id=project_id,
                user_id=user_id,
                use_cache=False,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_verify_membership_different_cache_ttl(self, client):
        """Test that non-members have shorter cache TTL."""
        project_id = uuid4()
        user_id = uuid4()

        mock_response = Mock()
        mock_response.status_code = 404

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Cache miss
        client.redis_client = mock_redis

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.verify_project_membership(
                project_id=project_id,
                user_id=user_id,
                use_cache=True,
            )

            assert result is False
            # Verify cache was set with shorter TTL
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 60  # 1 minute TTL for non-members
