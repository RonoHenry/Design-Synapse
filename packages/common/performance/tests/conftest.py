"""
Test configuration and fixtures for performance optimization tests.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.asyncio as redis

from ..models import CacheConfig, CDNConfig, PoolConfig


@pytest.fixture
def cache_config():
    """Test cache configuration."""
    return CacheConfig(
        redis_url="redis://localhost:6379/1",  # Use test database
        default_ttl=300,  # 5 minutes for tests
        max_memory="10mb",
        key_prefix="test_cache:",
        compression_enabled=False,  # Disable for easier testing
    )


@pytest.fixture
def pool_config():
    """Test database pool configuration."""
    return PoolConfig(
        min_connections=2,
        max_connections=5,
        max_idle_time=60,
        connection_timeout=10,
        retry_attempts=2,
    )


@pytest.fixture
def cdn_config():
    """Test CDN configuration."""
    return CDNConfig(
        provider="test",
        base_url="https://test-cdn.example.com",
        api_key="test-key",
        cache_ttl=3600,
        compression_enabled=False,
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.setex.return_value = True
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = 0
    mock_client.ttl.return_value = -1
    mock_client.keys.return_value = []
    mock_client.flushdb.return_value = True
    mock_client.info.return_value = {
        "used_memory": 1024,
        "used_memory_human": "1K",
        "keyspace_hits": 100,
        "keyspace_misses": 50,
    }
    return mock_client


@pytest.fixture
async def real_redis():
    """Real Redis client for integration tests."""
    try:
        client = redis.Redis.from_url("redis://localhost:6379/1", decode_responses=True)
        await client.ping()
        yield client
        await client.flushdb()  # Clean up after tests
        await client.close()
    except Exception:
        pytest.skip("Redis not available for integration tests")


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value = MagicMock()
    mock_conn.close.return_value = None
    mock_conn.is_valid.return_value = True
    return mock_conn


@pytest.fixture
def sample_cache_data():
    """Sample data for cache testing."""
    return {
        "user:123": {"id": 123, "name": "John Doe", "email": "john@example.com"},
        "project:456": {"id": 456, "title": "Test Project", "status": "active"},
        "config:app": {"debug": False, "version": "1.0.0"},
    }


@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing."""
    return {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}  # Create larger values


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
