"""Unit tests for ProjectServiceClient."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from src.integrations.project_service_client import ProjectServiceClient


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.scan_iter = AsyncMock(return_value=iter([]))
    return redis_mock


@pytest.fixture
def client(mock_redis):
    """Create ProjectServiceClient instance."""
    return ProjectServiceClient(
        base_url="http://localhost:8003",
        timeout=30.0,
        max_retries=3,
        redis_client=mock_redis,
    )


@pytest.mark.asyncio
async def test_get_project_info_success(client):
    """Test successful project info retrieval."""
    project_id = uuid4()
    expected_data = {
        "id": str(project_id),
        "name": "Test Project",
        "status": "active",
        "start_date": "2024-01-01",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_project_info(project_id, use_cache=False)

        assert result == expected_data
        mock_http_client.get.assert_called_once_with(f"/api/v1/projects/{project_id}")


@pytest.mark.asyncio
async def test_get_project_info_with_cache(client, mock_redis):
    """Test project info retrieval with cache hit."""
    project_id = uuid4()
    cached_data = {
        "id": str(project_id),
        "name": "Cached Project",
    }

    mock_redis.get = AsyncMock(return_value=json.dumps(cached_data).encode())

    result = await client.get_project_info(project_id, use_cache=True)

    assert result == cached_data
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_update_milestone_success(client, mock_redis):
    """Test successful milestone update."""
    project_id = uuid4()
    milestone_data = {
        "milestone_id": str(uuid4()),
        "status": "completed",
        "completion_date": "2024-01-15",
        "notes": "Engineering calculations completed",
    }
    expected_data = {
        **milestone_data,
        "updated_at": "2024-01-15T10:00:00Z",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.put = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.update_milestone(project_id, milestone_data)

        assert result == expected_data
        mock_http_client.put.assert_called_once_with(
            f"/api/v1/projects/{project_id}/milestones",
            json=milestone_data,
        )
        # Verify cache invalidation
        mock_redis.scan_iter.assert_called_once()


@pytest.mark.asyncio
async def test_get_milestones_success(client):
    """Test successful milestones retrieval."""
    project_id = uuid4()
    expected_data = [
        {
            "id": "1",
            "name": "Design Phase",
            "status": "completed",
        },
        {
            "id": "2",
            "name": "Engineering Phase",
            "status": "in_progress",
        },
    ]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_milestones(project_id, use_cache=False)

        assert result == expected_data
        assert len(result) == 2
        mock_http_client.get.assert_called_once_with(
            f"/api/v1/projects/{project_id}/milestones"
        )


@pytest.mark.asyncio
async def test_create_milestone_success(client, mock_redis):
    """Test successful milestone creation."""
    project_id = uuid4()
    milestone_data = {
        "name": "Structural Analysis Complete",
        "description": "Complete all structural calculations",
        "due_date": "2024-02-01",
        "milestone_type": "engineering",
    }
    expected_data = {
        "id": str(uuid4()),
        **milestone_data,
        "created_at": "2024-01-15T10:00:00Z",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.create_milestone(project_id, milestone_data)

        assert result == expected_data
        mock_http_client.post.assert_called_once_with(
            f"/api/v1/projects/{project_id}/milestones",
            json=milestone_data,
        )
        # Verify cache invalidation
        mock_redis.scan_iter.assert_called_once()


@pytest.mark.asyncio
async def test_get_project_team_success(client):
    """Test successful project team retrieval."""
    project_id = uuid4()
    expected_data = [
        {
            "user_id": "1",
            "name": "John Doe",
            "role": "structural_engineer",
        },
        {
            "user_id": "2",
            "name": "Jane Smith",
            "role": "mep_engineer",
        },
    ]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_project_team(project_id, use_cache=False)

        assert result == expected_data
        assert len(result) == 2
        mock_http_client.get.assert_called_once_with(
            f"/api/v1/projects/{project_id}/team"
        )


@pytest.mark.asyncio
async def test_get_project_info_http_error(client):
    """Test project info retrieval with HTTP error."""
    project_id = uuid4()

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Not found")

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        with pytest.raises(httpx.HTTPError):
            await client.get_project_info(project_id, use_cache=False)


@pytest.mark.asyncio
async def test_update_milestone_http_error(client):
    """Test milestone update with HTTP error."""
    project_id = uuid4()
    milestone_data = {"status": "completed"}

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Server error")

        mock_http_client = AsyncMock()
        mock_http_client.put = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        with pytest.raises(httpx.HTTPError):
            await client.update_milestone(project_id, milestone_data)


@pytest.mark.asyncio
async def test_context_manager(mock_redis):
    """Test async context manager."""
    async with ProjectServiceClient(
        base_url="http://localhost:8003",
        redis_client=mock_redis,
    ) as client:
        assert client._client is not None

    # Client should be closed after exiting context
    assert client._client is None or client._client.is_closed


@pytest.mark.asyncio
async def test_close(client):
    """Test client close method."""
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    client._client = mock_client

    await client.close()

    mock_client.aclose.assert_called_once()
    assert client._client is None


@pytest.mark.asyncio
async def test_cache_operations(client, mock_redis):
    """Test cache set, get, and invalidate operations."""
    key = "test_key"
    value = {"test": "data"}

    # Test set cache
    await client._set_cache(key, value, ttl=300)
    mock_redis.setex.assert_called_once_with(key, 300, json.dumps(value))

    # Test get cache
    mock_redis.get = AsyncMock(return_value=json.dumps(value).encode())
    result = await client._get_cached(key)
    assert result == value

    # Test invalidate cache
    pattern = "project:*"
    keys_to_delete = [b"project:1", b"project:2"]

    async def async_gen():
        for key in keys_to_delete:
            yield key

    mock_redis.scan_iter = MagicMock(return_value=async_gen())

    await client._invalidate_cache(pattern)
    mock_redis.delete.assert_called_once_with(*keys_to_delete)


@pytest.mark.asyncio
async def test_cache_failure_graceful_handling(client, mock_redis):
    """Test graceful handling when cache operations fail."""
    project_id = uuid4()
    expected_data = {"id": str(project_id), "name": "Test"}

    # Make cache fail
    mock_redis.get.side_effect = Exception("Redis error")
    mock_redis.setex.side_effect = Exception("Redis error")

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        # Should still work despite cache failures
        result = await client.get_project_info(project_id, use_cache=True)
        assert result == expected_data
