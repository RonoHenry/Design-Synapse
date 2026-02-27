"""
Test configuration and fixtures for monitoring tests.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from ..health import HealthAggregator
from ..log_aggregator import LogAggregator, StructuredLogger
from ..metrics import MetricsCollector
from ..models import LogEntry, LogLevel, ServiceHealth

try:
    from packages.common.service_registry.models import HealthStatus
except ImportError:
    # Fallback for when running tests
    from ....service_registry.models import HealthStatus


@pytest.fixture
def log_aggregator():
    """Create a fresh log aggregator for testing."""
    return LogAggregator()


@pytest.fixture
def structured_logger():
    """Create a structured logger for testing."""
    return StructuredLogger("test-service")


@pytest.fixture
def metrics_collector():
    """Create a fresh metrics collector for testing."""
    return MetricsCollector()


@pytest.fixture
def health_aggregator():
    """Create a health aggregator with mocked health checker."""
    mock_health_checker = AsyncMock()
    return HealthAggregator(health_checker=mock_health_checker)


@pytest.fixture
def sample_log_entry():
    """Create a sample log entry for testing."""
    return LogEntry(
        timestamp=datetime.utcnow(),
        level=LogLevel.INFO,
        service="test-service",
        message="Test message",
        request_id="req-123",
        user_id="user-456",
        correlation_id="corr-789",
        metadata={"key": "value"},
    )


@pytest.fixture
def sample_service_health():
    """Create a sample service health for testing."""
    return ServiceHealth(
        service_name="test-service",
        status=HealthStatus.HEALTHY,
        message="Service is healthy",
        timestamp=datetime.utcnow(),
        response_time_ms=150.0,
        metadata={"version": "1.0.0"},
    )
