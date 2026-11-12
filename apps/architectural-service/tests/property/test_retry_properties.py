"""
Property-based tests for retry logic with exponential backoff.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

# Add workspace root to path for common packages
workspace_root = Path(__file__).parent.parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

import httpx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.infrastructure.design_service_client import (DesignServiceClient,
                                                      RenderJob,
                                                      RenderParameters,
                                                      RenderStatus, RenderType)

from packages.common.resilience.retry import RetryConfig


# Feature: architectural-service, Property 33: Rendering retry with exponential backoff
@pytest.mark.asyncio
@given(
    design_id=st.uuids(),
    render_type=st.sampled_from(
        [RenderType.FLOOR_PLAN, RenderType.ELEVATION, RenderType.SECTION]
    ),
    failure_count=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=5, deadline=None)
async def test_property_rendering_retry_exponential_backoff(
    design_id, render_type, failure_count
):
    """
    Property 33: Rendering retry with exponential backoff

    For any rendering request that fails, the service should retry with
    exponentially increasing delays (e.g., 1s, 2s, 4s, 8s) up to a maximum
    number of attempts.

    **Validates: Requirements 8.4**
    """
    # Create client with custom retry config
    retry_config = RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=16.0,
        exponential_base=2.0,
        retryable_exceptions=[httpx.TimeoutException, httpx.ConnectError],
        retryable_status_codes=[502, 503, 504],
    )

    client = DesignServiceClient(
        base_url="http://test-design-service", timeout=30.0, retry_config=retry_config
    )

    # Track retry attempts and delays
    attempt_times = []

    # Mock the HTTP client to fail N times then succeed
    original_request = client._client.request
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        attempt_times.append(asyncio.get_event_loop().time())

        if call_count <= failure_count:
            # Fail with retryable error
            raise httpx.TimeoutException("Timeout")
        else:
            # Succeed
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "job_id": str(uuid4()),
                "design_id": str(design_id),
                "render_type": render_type.value,
                "status": RenderStatus.PENDING.value,
                "created_at": "2024-01-15T10:00:00Z",
            }
            mock_response.raise_for_status = Mock()
            return mock_response

    client._client.request = mock_request

    try:
        # Make request
        parameters = RenderParameters(render_type=render_type)
        job = await client.request_rendering(design_id, render_type, parameters)

        # Verify request eventually succeeded
        assert job is not None
        assert job.design_id == design_id
        assert job.render_type == render_type

        # Verify retry attempts
        assert call_count == failure_count + 1  # N failures + 1 success

        # Verify exponential backoff delays
        if len(attempt_times) > 1:
            for i in range(1, len(attempt_times)):
                delay = attempt_times[i] - attempt_times[i - 1]

                # Expected delay: base_delay * (exponential_base ** (i-1))
                # With jitter, allow 25% variance
                expected_delay = retry_config.base_delay * (
                    retry_config.exponential_base ** (i - 1)
                )
                expected_delay = min(expected_delay, retry_config.max_delay)

                # Allow for jitter (up to 25% variance) and timing imprecision
                min_delay = expected_delay * 0.7
                max_delay = expected_delay * 1.3

                assert min_delay <= delay <= max_delay, (
                    f"Delay {delay}s not in expected range [{min_delay}, {max_delay}] "
                    f"for attempt {i}"
                )

    finally:
        await client.close()


@pytest.mark.asyncio
@given(
    design_id=st.uuids(),
    render_type=st.sampled_from([RenderType.FLOOR_PLAN, RenderType.THREE_D_VIEW]),
)
@settings(max_examples=5, deadline=None)
async def test_property_rendering_retry_max_attempts(design_id, render_type):
    """
    Property: Rendering retry respects max attempts

    For any rendering request that continuously fails, the service should
    stop retrying after reaching the maximum number of attempts.

    **Validates: Requirements 8.4**
    """
    # Create client with custom retry config
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.1,  # Short delays for testing
        max_delay=1.0,
        exponential_base=2.0,
        retryable_exceptions=[httpx.TimeoutException],
        retryable_status_codes=[502, 503, 504],
    )

    client = DesignServiceClient(
        base_url="http://test-design-service", timeout=30.0, retry_config=retry_config
    )

    # Track retry attempts
    call_count = 0

    # Mock the HTTP client to always fail
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("Timeout")

    client._client.request = mock_request

    try:
        # Make request - should fail after max attempts
        parameters = RenderParameters(render_type=render_type)

        with pytest.raises(httpx.TimeoutException):
            await client.request_rendering(design_id, render_type, parameters)

        # Verify max attempts was respected
        assert call_count == retry_config.max_attempts

    finally:
        await client.close()


@pytest.mark.asyncio
@given(
    design_id=st.uuids(),
    render_type=st.sampled_from([RenderType.ELEVATION, RenderType.SECTION]),
)
@settings(max_examples=5, deadline=None)
async def test_property_rendering_no_retry_on_non_retryable_error(
    design_id, render_type
):
    """
    Property: Rendering does not retry on non-retryable errors

    For any rendering request that fails with a non-retryable error (e.g., 400, 404),
    the service should not retry and should immediately raise the error.

    **Validates: Requirements 8.4**
    """
    client = DesignServiceClient(base_url="http://test-design-service", timeout=30.0)

    # Track retry attempts
    call_count = 0

    # Mock the HTTP client to fail with non-retryable error
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Create 400 Bad Request error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        def raise_for_status():
            raise httpx.HTTPStatusError(
                "Bad Request", request=Mock(), response=mock_response
            )

        mock_response.raise_for_status = raise_for_status
        return mock_response

    client._client.request = mock_request

    try:
        # Make request - should fail immediately without retries
        parameters = RenderParameters(render_type=render_type)

        with pytest.raises(httpx.HTTPStatusError):
            await client.request_rendering(design_id, render_type, parameters)

        # Verify no retries occurred (only 1 attempt)
        assert call_count == 1

    finally:
        await client.close()
