"""
Unit tests for circuit breaker behavior in external service clients.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

# Add workspace root to path for common packages
workspace_root = Path(__file__).parent.parent.parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

import httpx
import pytest
from src.infrastructure.design_service_client import (DesignServiceClient,
                                                      RenderParameters,
                                                      RenderType)
from src.infrastructure.knowledge_service_client import KnowledgeServiceClient
from src.infrastructure.project_service_client import ProjectServiceClient

from packages.common.resilience.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenException,
    CircuitBreakerState)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """
    Test that circuit breaker opens after threshold failures.

    **Validates: Requirements 8.4**
    """
    from packages.common.resilience.retry import RetryConfig

    # Create client with low failure threshold and no retries
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=3, recovery_timeout=60, success_threshold=2
    )

    retry_config = RetryConfig(
        max_attempts=1, base_delay=0.1, max_delay=1.0  # No retries
    )

    client = ProjectServiceClient(
        base_url="http://test-project-service",
        timeout=5.0,
        circuit_breaker_config=circuit_breaker_config,
        retry_config=retry_config,
    )

    # Mock the HTTP client to always fail
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("Connection failed")

    client._client.request = mock_request

    try:
        # Make requests until circuit breaker opens
        project_id = uuid4()
        user_id = uuid4()

        # First 3 attempts should fail with ConnectError
        for i in range(3):
            with pytest.raises(httpx.ConnectError):
                await client.validate_project(project_id, user_id)

        # Verify circuit breaker is now open
        assert client.circuit_breaker.state == CircuitBreakerState.OPEN

        # Next attempt should fail with CircuitBreakerOpenException
        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            await client.validate_project(project_id, user_id)

        assert "project-service" in str(exc_info.value)

        # Verify no additional HTTP requests were made after circuit opened
        assert call_count == 3

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """
    Test that circuit breaker transitions to half-open state after recovery timeout.

    **Validates: Requirements 8.4**
    """
    from packages.common.resilience.retry import RetryConfig

    # Create client with short recovery timeout and no retries
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=2, recovery_timeout=1, success_threshold=2  # 1 second
    )

    retry_config = RetryConfig(
        max_attempts=1, base_delay=0.1, max_delay=1.0  # No retries
    )

    client = KnowledgeServiceClient(
        base_url="http://test-knowledge-service",
        timeout=5.0,
        circuit_breaker_config=circuit_breaker_config,
        retry_config=retry_config,
    )

    # Mock the HTTP client to fail initially, then succeed
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count <= 2:
            # First 2 calls fail
            raise httpx.TimeoutException("Timeout")
        else:
            # Subsequent calls succeed
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = Mock()
            return mock_response

    client._client.request = mock_request

    try:
        # Make 2 failed requests to open circuit
        for i in range(2):
            with pytest.raises(httpx.TimeoutException):
                await client.search_codes("test query")

        # Verify circuit is open
        assert client.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.5)

        # Next request should transition to half-open and succeed
        results = await client.search_codes("test query")

        # Verify circuit is in half-open state
        assert client.circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Verify request succeeded
        assert results == []
        assert call_count == 3

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_successes():
    """
    Test that circuit breaker closes after success threshold in half-open state.

    **Validates: Requirements 8.4**
    """
    from packages.common.resilience.retry import RetryConfig

    # Create client with low thresholds and no retries
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=1,  # 1 second
        success_threshold=2,  # Need 2 successes to close
    )

    retry_config = RetryConfig(
        max_attempts=1, base_delay=0.1, max_delay=1.0  # No retries
    )

    client = DesignServiceClient(
        base_url="http://test-design-service",
        timeout=5.0,
        circuit_breaker_config=circuit_breaker_config,
        retry_config=retry_config,
    )

    # Mock the HTTP client
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count <= 2:
            # First 2 calls fail to open circuit
            raise httpx.ConnectError("Connection failed")
        else:
            # Subsequent calls succeed
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "job_id": str(uuid4()),
                "design_id": str(uuid4()),
                "render_type": "floor_plan",
                "status": "pending",
                "created_at": "2024-01-15T10:00:00Z",
            }
            mock_response.raise_for_status = Mock()
            return mock_response

    client._client.request = mock_request

    try:
        # Make 2 failed requests to open circuit
        design_id = uuid4()
        parameters = RenderParameters(render_type=RenderType.FLOOR_PLAN)

        for i in range(2):
            with pytest.raises(httpx.ConnectError):
                await client.request_rendering(
                    design_id, RenderType.FLOOR_PLAN, parameters
                )

        # Verify circuit is open
        assert client.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.5)

        # Make first successful request (transitions to half-open)
        job1 = await client.request_rendering(
            design_id, RenderType.FLOOR_PLAN, parameters
        )
        assert job1 is not None
        assert client.circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Make second successful request (should close circuit)
        job2 = await client.request_rendering(
            design_id, RenderType.FLOOR_PLAN, parameters
        )
        assert job2 is not None
        assert client.circuit_breaker.state == CircuitBreakerState.CLOSED

        # Verify total calls
        assert call_count == 4  # 2 failures + 2 successes

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_circuit_breaker_reopens_on_half_open_failure():
    """
    Test that circuit breaker reopens if request fails in half-open state.

    **Validates: Requirements 8.4**
    """
    from packages.common.resilience.retry import RetryConfig

    # Create client with no retries
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=2, recovery_timeout=1, success_threshold=2
    )

    retry_config = RetryConfig(
        max_attempts=1, base_delay=0.1, max_delay=1.0  # No retries
    )

    client = ProjectServiceClient(
        base_url="http://test-project-service",
        timeout=5.0,
        circuit_breaker_config=circuit_breaker_config,
        retry_config=retry_config,
    )

    # Mock the HTTP client
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # All calls fail
        raise httpx.TimeoutException("Timeout")

    client._client.request = mock_request

    try:
        # Make 2 failed requests to open circuit
        project_id = uuid4()
        user_id = uuid4()

        for i in range(2):
            with pytest.raises(httpx.TimeoutException):
                await client.validate_project(project_id, user_id)

        # Verify circuit is open
        assert client.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.5)

        # Next request should transition to half-open but fail
        with pytest.raises(httpx.TimeoutException):
            await client.validate_project(project_id, user_id)

        # Verify circuit is back to open
        assert client.circuit_breaker.state == CircuitBreakerState.OPEN

        # Verify total calls
        assert call_count == 3  # 2 to open + 1 in half-open

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_circuit_breaker_resets_failure_count_on_success():
    """
    Test that circuit breaker resets failure count after successful request in closed state.

    **Validates: Requirements 8.4**
    """
    # Test circuit breaker directly without client wrapper
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=3, recovery_timeout=60, success_threshold=2
    )

    breaker = CircuitBreaker("test-service", circuit_breaker_config)

    # Simulate 2 failures
    for i in range(2):
        try:
            raise httpx.TimeoutException("Timeout")
        except Exception as e:
            breaker._record_failure(e)

    # Circuit should still be closed (threshold is 3)
    assert breaker.state == CircuitBreakerState.CLOSED

    # Simulate success (should reset failure count)
    breaker._record_success()
    assert breaker.state == CircuitBreakerState.CLOSED

    # Simulate 2 more failures
    for i in range(2):
        try:
            raise httpx.TimeoutException("Timeout")
        except Exception as e:
            breaker._record_failure(e)

    # Circuit should still be closed because failure count was reset
    assert breaker.state == CircuitBreakerState.CLOSED
