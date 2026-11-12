"""
Property-based tests for rendering cache reuse.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

# Add workspace root to path for common packages
workspace_root = Path(__file__).parent.parent.parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.infrastructure.design_service_client import (DesignServiceClient,
                                                      RenderJob,
                                                      RenderParameters,
                                                      RenderStatus, RenderType,
                                                      VisualOutput)


# Mock cache result class
class MockCacheResult:
    def __init__(self, value=None):
        self.value = value


# Mock cache manager
class MockCacheManager:
    def __init__(self):
        self._cache = {}

    async def get(self, key):
        return MockCacheResult(self._cache.get(key))

    async def set(self, key, value, ttl=None):
        self._cache[key] = value
        return True


# Feature: architectural-service, Property 34: Rendering cache reuse
@pytest.mark.asyncio
@given(
    design_id=st.uuids(),
    design_version=st.text(min_size=3, max_size=10, alphabet="0123456789."),
    render_type=st.sampled_from(
        [
            RenderType.FLOOR_PLAN,
            RenderType.ELEVATION,
            RenderType.SECTION,
            RenderType.THREE_D_VIEW,
        ]
    ),
    resolution=st.sampled_from(["1920x1080", "1280x720", "3840x2160"]),
    quality=st.sampled_from(["low", "medium", "high"]),
)
@settings(max_examples=10, deadline=None)
async def test_property_rendering_cache_reuse(
    design_id, design_version, render_type, resolution, quality
):
    """
    Property 34: Rendering cache reuse

    For any design document and rendering parameters, if the same rendering
    request is made multiple times without changes to the design or parameters,
    the service should return cached results instead of requesting new rendering.

    **Validates: Requirements 8.6**
    """
    # Create client
    client = DesignServiceClient(base_url="http://test-design-service", timeout=30.0)

    # Mock the cache manager
    mock_cache_manager = MockCacheManager()

    # Create render parameters
    parameters = RenderParameters(
        render_type=render_type,
        resolution=resolution,
        quality=quality,
        lighting="natural",
        materials=True,
    )

    # Mock visual outputs
    mock_outputs = [
        VisualOutput(
            output_id=uuid4(),
            job_id=uuid4(),
            render_type=render_type,
            file_url=f"https://storage.example.com/renders/{uuid4()}.png",
            file_size=1024000,
            mime_type="image/png",
            resolution=resolution,
            created_at="2024-01-15T10:00:00Z",
        )
    ]

    # Track HTTP requests
    request_count = 0

    # Mock the HTTP client
    async def mock_request(*args, **kwargs):
        nonlocal request_count
        request_count += 1

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

    # Mock the cache manager in the client
    with patch.object(client, "cache") as mock_cache:
        mock_cache.cache_manager = mock_cache_manager

        try:
            # First request - should miss cache and make HTTP request
            job1, cached_outputs1 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters
            )

            # Verify first request made HTTP call
            assert request_count == 1
            assert cached_outputs1 is None  # No cache hit
            assert job1.design_id == design_id
            assert job1.render_type == render_type

            # Simulate caching the outputs after rendering completes
            await client.cache_outputs(
                design_id, design_version, parameters, mock_outputs
            )

            # Second identical request - should hit cache and NOT make HTTP request
            job2, cached_outputs2 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters
            )

            # Verify second request used cache
            assert request_count == 1  # No additional HTTP requests
            assert cached_outputs2 is not None  # Cache hit
            assert len(cached_outputs2) == len(mock_outputs)
            assert cached_outputs2[0].render_type == render_type
            assert cached_outputs2[0].resolution == resolution
            assert job2.status == RenderStatus.COMPLETED  # Mock job shows completed

            # Third identical request - should also hit cache
            job3, cached_outputs3 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters
            )

            # Verify third request also used cache
            assert request_count == 1  # Still no additional HTTP requests
            assert cached_outputs3 is not None  # Cache hit
            assert len(cached_outputs3) == len(mock_outputs)

            # Verify cache consistency - all cached results should be identical
            assert cached_outputs2[0].output_id == cached_outputs3[0].output_id
            assert cached_outputs2[0].file_url == cached_outputs3[0].file_url
            assert cached_outputs2[0].file_size == cached_outputs3[0].file_size

        finally:
            await client.close()


@pytest.mark.asyncio
@given(
    design_id=st.uuids(),
    design_version=st.text(min_size=3, max_size=10, alphabet="0123456789."),
    render_type=st.sampled_from([RenderType.FLOOR_PLAN, RenderType.ELEVATION]),
    resolution1=st.sampled_from(["1920x1080", "1280x720"]),
    resolution2=st.sampled_from(["3840x2160", "2560x1440"]),
)
@settings(max_examples=10, deadline=None)
async def test_property_rendering_cache_parameter_sensitivity(
    design_id, design_version, render_type, resolution1, resolution2
):
    """
    Property: Rendering cache is sensitive to parameter changes

    For any design document, if rendering parameters change (resolution, quality, etc.),
    the service should NOT reuse cached results and should request new rendering.

    **Validates: Requirements 8.6**
    """
    # Ensure resolutions are different
    if resolution1 == resolution2:
        return

    # Create client
    client = DesignServiceClient(base_url="http://test-design-service", timeout=30.0)

    # Mock the cache manager
    mock_cache_manager = MockCacheManager()

    # Create different render parameters
    parameters1 = RenderParameters(
        render_type=render_type, resolution=resolution1, quality="high"
    )

    parameters2 = RenderParameters(
        render_type=render_type,
        resolution=resolution2,  # Different resolution
        quality="high",
    )

    # Mock visual outputs
    mock_outputs1 = [
        VisualOutput(
            output_id=uuid4(),
            job_id=uuid4(),
            render_type=render_type,
            file_url=f"https://storage.example.com/renders/{uuid4()}.png",
            file_size=1024000,
            mime_type="image/png",
            resolution=resolution1,
            created_at="2024-01-15T10:00:00Z",
        )
    ]

    mock_outputs2 = [
        VisualOutput(
            output_id=uuid4(),
            job_id=uuid4(),
            render_type=render_type,
            file_url=f"https://storage.example.com/renders/{uuid4()}.png",
            file_size=2048000,  # Different size for different resolution
            mime_type="image/png",
            resolution=resolution2,
            created_at="2024-01-15T10:00:00Z",
        )
    ]

    # Track HTTP requests
    request_count = 0

    # Mock the HTTP client
    async def mock_request(*args, **kwargs):
        nonlocal request_count
        request_count += 1

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

    # Mock the cache manager in the client
    with patch.object(client, "cache") as mock_cache:
        mock_cache.cache_manager = mock_cache_manager

        try:
            # First request with parameters1
            job1, cached_outputs1 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters1
            )

            # Verify first request made HTTP call
            assert request_count == 1
            assert cached_outputs1 is None  # No cache hit

            # Cache the first outputs
            await client.cache_outputs(
                design_id, design_version, parameters1, mock_outputs1
            )

            # Second request with different parameters (parameters2)
            job2, cached_outputs2 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters2
            )

            # Verify second request made new HTTP call (cache miss due to different parameters)
            assert request_count == 2  # New HTTP request made
            assert cached_outputs2 is None  # No cache hit for different parameters

            # Cache the second outputs
            await client.cache_outputs(
                design_id, design_version, parameters2, mock_outputs2
            )

            # Third request with original parameters1 - should hit cache
            job3, cached_outputs3 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters1
            )

            # Verify third request used cache for parameters1
            assert request_count == 2  # No additional HTTP requests
            assert cached_outputs3 is not None  # Cache hit
            assert cached_outputs3[0].resolution == resolution1

            # Fourth request with parameters2 - should also hit cache
            job4, cached_outputs4 = await client.request_rendering_with_cache(
                design_id, design_version, render_type, parameters2
            )

            # Verify fourth request used cache for parameters2
            assert request_count == 2  # Still no additional HTTP requests
            assert cached_outputs4 is not None  # Cache hit
            assert cached_outputs4[0].resolution == resolution2

            # Verify different cached results for different parameters
            assert cached_outputs3[0].resolution != cached_outputs4[0].resolution
            assert cached_outputs3[0].file_size != cached_outputs4[0].file_size

        finally:
            await client.close()


@pytest.mark.asyncio
@given(
    design_id=st.uuids(),
    design_version1=st.text(min_size=3, max_size=10, alphabet="0123456789."),
    design_version2=st.text(min_size=3, max_size=10, alphabet="0123456789."),
    render_type=st.sampled_from([RenderType.FLOOR_PLAN, RenderType.THREE_D_VIEW]),
)
@settings(max_examples=10, deadline=None)
async def test_property_rendering_cache_version_sensitivity(
    design_id, design_version1, design_version2, render_type
):
    """
    Property: Rendering cache is sensitive to design version changes

    For any design document, if the design version changes, the service should
    NOT reuse cached results and should request new rendering.

    **Validates: Requirements 8.6**
    """
    # Ensure versions are different
    if design_version1 == design_version2:
        return

    # Create client
    client = DesignServiceClient(base_url="http://test-design-service", timeout=30.0)

    # Mock the cache manager
    mock_cache_manager = MockCacheManager()

    # Create render parameters (same for both versions)
    parameters = RenderParameters(
        render_type=render_type, resolution="1920x1080", quality="high"
    )

    # Track HTTP requests
    request_count = 0

    # Mock the HTTP client
    async def mock_request(*args, **kwargs):
        nonlocal request_count
        request_count += 1

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

    # Mock outputs for different versions
    mock_outputs1 = [
        VisualOutput(
            output_id=uuid4(),
            job_id=uuid4(),
            render_type=render_type,
            file_url=f"https://storage.example.com/renders/v1/{uuid4()}.png",
            file_size=1024000,
            mime_type="image/png",
            resolution="1920x1080",
            created_at="2024-01-15T10:00:00Z",
        )
    ]

    mock_outputs2 = [
        VisualOutput(
            output_id=uuid4(),
            job_id=uuid4(),
            render_type=render_type,
            file_url=f"https://storage.example.com/renders/v2/{uuid4()}.png",
            file_size=1024000,
            mime_type="image/png",
            resolution="1920x1080",
            created_at="2024-01-15T10:00:00Z",
        )
    ]

    # Mock the cache manager in the client
    with patch.object(client, "cache") as mock_cache:
        mock_cache.cache_manager = mock_cache_manager

        try:
            # First request with design_version1
            job1, cached_outputs1 = await client.request_rendering_with_cache(
                design_id, design_version1, render_type, parameters
            )

            # Verify first request made HTTP call
            assert request_count == 1
            assert cached_outputs1 is None  # No cache hit

            # Cache the first outputs
            await client.cache_outputs(
                design_id, design_version1, parameters, mock_outputs1
            )

            # Second request with different design version
            job2, cached_outputs2 = await client.request_rendering_with_cache(
                design_id, design_version2, render_type, parameters
            )

            # Verify second request made new HTTP call (cache miss due to different version)
            assert request_count == 2  # New HTTP request made
            assert cached_outputs2 is None  # No cache hit for different version

            # Cache the second outputs
            await client.cache_outputs(
                design_id, design_version2, parameters, mock_outputs2
            )

            # Third request with original version - should hit cache
            job3, cached_outputs3 = await client.request_rendering_with_cache(
                design_id, design_version1, render_type, parameters
            )

            # Verify third request used cache for version1
            assert request_count == 2  # No additional HTTP requests
            assert cached_outputs3 is not None  # Cache hit
            assert cached_outputs3[0].file_url == mock_outputs1[0].file_url

            # Fourth request with version2 - should also hit cache
            job4, cached_outputs4 = await client.request_rendering_with_cache(
                design_id, design_version2, render_type, parameters
            )

            # Verify fourth request used cache for version2
            assert request_count == 2  # Still no additional HTTP requests
            assert cached_outputs4 is not None  # Cache hit
            assert cached_outputs4[0].file_url == mock_outputs2[0].file_url

            # Verify different cached results for different versions
            assert cached_outputs3[0].file_url != cached_outputs4[0].file_url
            assert cached_outputs3[0].output_id != cached_outputs4[0].output_id

        finally:
            await client.close()
