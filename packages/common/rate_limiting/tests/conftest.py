"""Test configuration and fixtures for rate limiting tests."""

from datetime import datetime, timedelta

import pytest

from ..models import ClientQuota, RateLimitConfig, RateLimitStrategy
from ..storage import InMemoryStorage


@pytest.fixture
def sliding_window_config():
    """Sliding window rate limit configuration."""
    return RateLimitConfig(
        requests_per_window=10,
        window_size_seconds=60,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    )


@pytest.fixture
def token_bucket_config():
    """Token bucket rate limit configuration."""
    return RateLimitConfig(
        requests_per_window=10,
        window_size_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        burst_capacity=15,
        refill_rate=0.2,  # 0.2 tokens per second
    )


@pytest.fixture
def memory_storage():
    """In-memory storage for testing."""
    return InMemoryStorage()


@pytest.fixture
def sample_quota():
    """Sample client quota for testing."""
    return ClientQuota(
        client_id="test_client",
        requests_made=5,
        window_start=datetime.utcnow() - timedelta(seconds=30),
        last_request=datetime.utcnow(),
        tokens=10.0,
        last_refill=datetime.utcnow(),
    )
