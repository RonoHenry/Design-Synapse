"""Tests for rate limiting storage backends."""

from datetime import datetime, timedelta

import pytest

from ..models import ClientQuota
from ..storage import InMemoryStorage


class TestInMemoryStorage:
    """Test in-memory storage backend."""

    @pytest.mark.asyncio
    async def test_get_quota_nonexistent(self, memory_storage):
        """Test getting non-existent quota returns None."""
        quota = await memory_storage.get_quota("nonexistent")
        assert quota is None

    @pytest.mark.asyncio
    async def test_set_and_get_quota(self, memory_storage, sample_quota):
        """Test setting and getting quota."""
        key = "test_key"
        await memory_storage.set_quota(key, sample_quota, 3600)

        retrieved_quota = await memory_storage.get_quota(key)
        assert retrieved_quota is not None
        assert retrieved_quota.client_id == sample_quota.client_id
        assert retrieved_quota.requests_made == sample_quota.requests_made
        assert retrieved_quota.tokens == sample_quota.tokens

    @pytest.mark.asyncio
    async def test_quota_expiry(self, memory_storage, sample_quota):
        """Test quota expiry functionality."""
        key = "test_key"
        # Set quota with 1 second TTL
        await memory_storage.set_quota(key, sample_quota, 1)

        # Should exist immediately
        quota = await memory_storage.get_quota(key)
        assert quota is not None

        # Manually expire by setting past expiry time
        memory_storage._expiry[key] = datetime.utcnow() - timedelta(seconds=1)

        # Should be None after expiry
        quota = await memory_storage.get_quota(key)
        assert quota is None

    @pytest.mark.asyncio
    async def test_increment_requests_new_key(self, memory_storage):
        """Test incrementing requests for new key."""
        key = "new_key"
        result = await memory_storage.increment_requests(key, 3)
        assert result == 3

    @pytest.mark.asyncio
    async def test_increment_requests_existing_key(self, memory_storage, sample_quota):
        """Test incrementing requests for existing key."""
        key = "test_key"
        await memory_storage.set_quota(key, sample_quota, 3600)

        result = await memory_storage.increment_requests(key, 2)
        assert result == sample_quota.requests_made + 2

        # Verify quota was updated
        quota = await memory_storage.get_quota(key)
        assert quota.requests_made == sample_quota.requests_made + 2

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, memory_storage, sample_quota):
        """Test cleanup of expired quotas."""
        key1 = "key1"
        key2 = "key2"

        # Set two quotas
        await memory_storage.set_quota(key1, sample_quota, 3600)
        await memory_storage.set_quota(key2, sample_quota, 3600)

        # Manually expire one
        memory_storage._expiry[key1] = datetime.utcnow() - timedelta(seconds=1)

        # Run cleanup
        await memory_storage.cleanup_expired()

        # Expired quota should be gone
        assert await memory_storage.get_quota(key1) is None
        # Non-expired quota should remain
        assert await memory_storage.get_quota(key2) is not None
