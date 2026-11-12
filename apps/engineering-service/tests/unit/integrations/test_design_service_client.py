"""Unit tests for DesignServiceClient."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from src.integrations.design_service_client import DesignServiceClient


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
    """Create DesignServiceClient instance."""
    return DesignServiceClient(
        base_url="http://localhost:8001",
        timeout=30.0,
        max_retries=3,
        redis_client=mock_redis,
    )


@pytest.mark.asyncio
async def test_update_technical_requirements_success(client, mock_redis):
    """Test successful technical requirements update."""
    design_id = uuid4()
    requirements = {
        "structural_loads": {"dead_load": 100, "live_load": 50},
        "mep_requirements": {"hvac": "central", "electrical": "3-phase"},
    }
    expected_data = {
        "id": str(design_id),
        "requirements": requirements,
        "updated_at": "2024-01-01T00:00:00Z",
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.put = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.update_technical_requirements(design_id, requirements)

        assert result == expected_data
        mock_http_client.put.assert_called_once_with(
            f"/api/v1/designs/{design_id}/requirements",
            json=requirements,
        )
        # Verify cache invalidation
        mock_redis.scan_iter.assert_called_once()


@pytest.mark.asyncio
async def test_get_drawings_success(client):
    """Test successful drawings retrieval."""
    project_id = uuid4()
    expected_data = [
        {
            "id": "1",
            "name": "Floor Plan",
            "type": "architectural",
        },
        {
            "id": "2",
            "name": "Electrical Plan",
            "type": "electrical",
        },
    ]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.get_drawings(project_id, use_cache=False)

        assert result == expected_data
        assert len(result) == 2
        mock_http_client.get.assert_called_once_with(
            f"/api/v1/projects/{project_id}/drawings"
        )


@pytest.mark.asyncio
async def test_get_drawings_with_cache(client, mock_redis):
    """Test drawings retrieval with cache hit."""
    project_id = uuid4()
    cached_data = [
        {"id": "1", "name": "Cached Drawing"},
    ]

    mock_redis.get = AsyncMock(return_value=json.dumps(cached_data).encode())

    result = await client.get_drawings(project_id, use_cache=True)

    assert result == cached_data
    mock_redis.get.assert_called_once()


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
async def test_create_technical_specification_success(client):
    """Test successful technical specification creation."""
    design_id = uuid4()
    spec_data = {
        "title": "Structural Specifications",
        "sections": [{"number": "03 30 00", "title": "Cast-in-Place Concrete"}],
    }
    expected_data = {
        "id": "spec-123",
        "design_id": str(design_id),
        **spec_data,
    }

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        result = await client.create_technical_specification(design_id, spec_data)

        assert result == expected_data
        mock_http_client.post.assert_called_once_with(
            f"/api/v1/designs/{design_id}/specifications",
            json=spec_data,
        )


@pytest.mark.asyncio
async def test_update_requirements_http_error(client):
    """Test requirements update with HTTP error."""
    design_id = uuid4()
    requirements = {"test": "data"}

    with patch.object(client, "_get_client") as mock_get_client:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("Server error")

        mock_http_client = AsyncMock()
        mock_http_client.put = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_http_client

        with pytest.raises(httpx.HTTPError):
            await client.update_technical_requirements(design_id, requirements)


@pytest.mark.asyncio
async def test_context_manager(mock_redis):
    """Test async context manager."""
    async with DesignServiceClient(
        base_url="http://localhost:8001",
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
    pattern = "design:*"
    keys_to_delete = [b"design:1", b"design:2"]

    async def async_gen():
        for key in keys_to_delete:
            yield key

    mock_redis.scan_iter = MagicMock(return_value=async_gen())

    await client._invalidate_cache(pattern)
    mock_redis.delete.assert_called_once_with(*keys_to_delete)


@pytest.mark.asyncio
async def test_cache_failure_graceful_handling(client, mock_redis):
    """Test graceful handling when cache operations fail."""
    design_id = uuid4()
    expected_data = {"id": str(design_id), "name": "Test"}

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
        result = await client.get_design(design_id, use_cache=True)
        assert result == expected_data
