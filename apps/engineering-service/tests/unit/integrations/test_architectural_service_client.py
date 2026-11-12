"""Unit tests for ArchitecturalServiceClient."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from src.integrations.architectural_service_client import \
    ArchitecturalServiceClient


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
    """Create ArchitecturalServiceClient instance."""
    return ArchitecturalServiceClient(
        base_url="http://localhost:8005",
        timeout=30.0,
        max_retries=3,
        redis_client=mock_redis,
    )


@pytest.mark.asyncio
async def test_get_design_success(client):
    """Test successful design retrieval."""
    design_id = uuid4()
    expected_data = {
        "id": str(design_id),
        "name": "Test Design",
        "status": "active",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_design(design_id, use_cache=False)

        assert result == expected_data
        mock_http_client.get.assert_called_once_with(f"/api/v1/designs/{design_id}")


@pytest.mark.asyncio
async def test_get_design_with_cache_hit(client, mock_redis):
    """Test design retrieval with cache hit."""
    design_id = uuid4()
    cached_data = {
        "id": str(design_id),
        "name": "Cached Design",
        "status": "active",
    }

    mock_redis.get = AsyncMock(return_value=json.dumps(cached_data).encode())

    result = await client.get_design(design_id, use_cache=True)

    assert result == cached_data
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_design_http_error(client):
    """Test design retrieval with HTTP error."""
    design_id = uuid4()

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Not found")

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        with pytest.raises(httpx.HTTPError):
            await client.get_design(design_id, use_cache=False)


@pytest.mark.asyncio
async def test_get_space_requirements_success(client):
    """Test successful space requirements retrieval."""
    project_id = uuid4()
    expected_data = [
        {"space_id": "1", "name": "Office", "area": 1000},
        {"space_id": "2", "name": "Conference", "area": 500},
    ]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_space_requirements(project_id, use_cache=False)

        assert result == expected_data
        assert len(result) == 2


@pytest.mark.asyncio
async def test_get_design_version_success(client):
    """Test successful design version retrieval."""
    design_id = uuid4()
    version = 2
    expected_data = {
        "id": str(design_id),
        "version": version,
        "name": "Test Design v2",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_design_version(design_id, version)

        assert result == expected_data
        assert result["version"] == version
        mock_http_client.get.assert_called_once_with(
            f"/api/v1/designs/{design_id}/versions/{version}"
        )


@pytest.mark.asyncio
async def test_subscribe_to_design_changes(client, mock_redis):
    """Test subscribing to design changes."""
    design_id = uuid4()

    # Mock scan_iter to return some keys
    mock_redis.scan_iter = AsyncMock(
        return_value=iter([b"arch_design:123", b"arch_design:456"])
    )

    await client.subscribe_to_design_changes(design_id, lambda x: None)

    # Verify cache invalidation was attempted
    mock_redis.scan_iter.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set_and_get(client, mock_redis):
    """Test cache set and get operations."""
    key = "test_key"
    value = {"test": "data"}

    # Test set cache
    await client._set_cache(key, value, ttl=300)
    mock_redis.setex.assert_called_once_with(key, 300, json.dumps(value))

    # Test get cache
    mock_redis.get = AsyncMock(return_value=json.dumps(value).encode())
    result = await client._get_cached(key)
    assert result == value


@pytest.mark.asyncio
async def test_cache_invalidation(client, mock_redis):
    """Test cache invalidation."""
    pattern = "arch_design:*"
    keys_to_delete = [b"arch_design:1", b"arch_design:2"]

    async def async_gen():
        for key in keys_to_delete:
            yield key

    mock_redis.scan_iter = MagicMock(return_value=async_gen())

    await client._invalidate_cache(pattern)

    mock_redis.scan_iter.assert_called_once_with(match=pattern)
    mock_redis.delete.assert_called_once_with(*keys_to_delete)


@pytest.mark.asyncio
async def test_context_manager(mock_redis):
    """Test async context manager."""
    async with ArchitecturalServiceClient(
        base_url="http://localhost:8005",
        redis_client=mock_redis,
    ) as client:
        assert client._client is not None

    # Client should be closed after exiting context
    assert client._client is None or client._client.is_closed


@pytest.mark.asyncio
async def test_close(client):
    """Test client close method."""
    # Create a client instance
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    client._client = mock_client

    await client.close()

    mock_client.aclose.assert_called_once()
    assert client._client is None


@pytest.mark.asyncio
async def test_cache_failure_handling(client, mock_redis):
    """Test graceful handling of cache failures."""
    design_id = uuid4()
    expected_data = {"id": str(design_id), "name": "Test"}

    # Make cache operations fail
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
        result = await client.get_design(design_id, use_cache=True)
        assert result == expected_data
