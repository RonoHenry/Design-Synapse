"""Unit tests for Redis cache service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.cache import CacheService, close_redis, get_redis_client


@pytest.mark.unit
class TestCacheService:
    """Test cache service operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.scan_iter = AsyncMock(return_value=iter([]))
        mock.ping = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def cache_service(self, mock_redis):
        """Create a cache service with mock Redis."""
        return CacheService(mock_redis)

    @pytest.mark.asyncio
    async def test_get_returns_none_when_key_not_found(self, cache_service, mock_redis):
        """Test that get returns None when key is not found."""
        mock_redis.get.return_value = None

        result = await cache_service.get("test_key")

        assert result is None
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_returns_deserialized_value(self, cache_service, mock_redis):
        """Test that get returns deserialized value."""
        test_data = {"foo": "bar", "num": 42}
        mock_redis.get.return_value = json.dumps(test_data)

        result = await cache_service.get("test_key")

        assert result == test_data
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(self, cache_service, mock_redis):
        """Test that get returns None on error."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await cache_service.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_stores_serialized_value(self, cache_service, mock_redis):
        """Test that set stores serialized value."""
        test_data = {"foo": "bar", "num": 42}

        result = await cache_service.set("test_key", test_data, ttl=300)

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[0][1] == 300
        assert json.loads(call_args[0][2]) == test_data

    @pytest.mark.asyncio
    async def test_set_uses_default_ttl(self, cache_service, mock_redis):
        """Test that set uses default TTL from settings."""
        test_data = {"foo": "bar"}

        result = await cache_service.set("test_key", test_data)

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_returns_false_on_error(self, cache_service, mock_redis):
        """Test that set returns False on error."""
        mock_redis.setex.side_effect = Exception("Redis error")

        result = await cache_service.set("test_key", {"foo": "bar"})

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, cache_service, mock_redis):
        """Test that delete removes key."""
        result = await cache_service.delete("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(self, cache_service, mock_redis):
        """Test that delete returns False on error."""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await cache_service.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_key_exists(self, cache_service, mock_redis):
        """Test that exists returns True when key exists."""
        mock_redis.exists.return_value = 1

        result = await cache_service.exists("test_key")

        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_key_not_found(
        self, cache_service, mock_redis
    ):
        """Test that exists returns False when key not found."""
        mock_redis.exists.return_value = 0

        result = await cache_service.exists("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_pattern_deletes_matching_keys(self, cache_service, mock_redis):
        """Test that clear_pattern deletes matching keys."""
        # Mock scan_iter to return some keys
        keys = ["calc:1", "calc:2", "calc:3"]

        async def mock_scan():
            for key in keys:
                yield key

        mock_redis.scan_iter = MagicMock(return_value=mock_scan())
        mock_redis.delete.return_value = 3

        result = await cache_service.clear_pattern("calc:*")

        assert result == 3
        mock_redis.scan_iter.assert_called_once_with(match="calc:*")
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_pattern_returns_zero_when_no_keys(
        self, cache_service, mock_redis
    ):
        """Test that clear_pattern returns 0 when no keys match."""

        async def mock_scan():
            return
            yield  # Make it a generator

        mock_redis.scan_iter.return_value = mock_scan()

        result = await cache_service.clear_pattern("calc:*")

        assert result == 0

    @pytest.mark.asyncio
    async def test_ping_returns_true_when_redis_available(
        self, cache_service, mock_redis
    ):
        """Test that ping returns True when Redis is available."""
        mock_redis.ping.return_value = True

        result = await cache_service.ping()

        assert result is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_returns_false_on_error(self, cache_service, mock_redis):
        """Test that ping returns False on error."""
        mock_redis.ping.side_effect = Exception("Connection error")

        result = await cache_service.ping()

        assert result is False


@pytest.mark.unit
class TestRedisClientManagement:
    """Test Redis client management functions."""

    @pytest.mark.asyncio
    async def test_get_redis_client_returns_client(self):
        """Test that get_redis_client returns a client."""
        with patch("src.core.cache.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            client = await get_redis_client()

            assert client is mock_client
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_redis_closes_client(self):
        """Test that close_redis closes the client."""
        # Need to reset the global client first
        import src.core.cache as cache_module

        cache_module._redis_client = None

        with patch("src.core.cache.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            # Get client first
            await get_redis_client()

            # Close it
            await close_redis()

            mock_client.close.assert_called_once()

            # Reset for other tests
            cache_module._redis_client = None
