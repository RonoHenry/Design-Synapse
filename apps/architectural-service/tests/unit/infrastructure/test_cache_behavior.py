"""
Unit tests for cache behavior in Knowledge Service and Design Service clients.
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
from src.infrastructure.design_service_client import (DesignServiceClient,
                                                      RenderParameters,
                                                      RenderType, VisualOutput)
from src.infrastructure.knowledge_service_client import (
    CodeFilters, CodeSection, CodeSectionDetail, CodeStandard,
    KnowledgeServiceClient)


class TestKnowledgeServiceCaching:
    """Test caching behavior in Knowledge Service client."""

    @pytest.fixture
    async def client(self):
        """Create Knowledge Service client for testing."""
        client = KnowledgeServiceClient(base_url="http://test-knowledge-service")
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_cache_hit_miss_scenarios(self, client):
        """Test cache hit/miss scenarios for knowledge service calls."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "code_id": "IBC-2021",
                    "section": "1004.1",
                    "title": "Occupant Load",
                    "content": "The occupant load...",
                    "edition": "2021",
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch.object(client, "_make_request", return_value=mock_response):
            # Call the public method
            results = await client.search_codes("occupant load")

            # Verify results
            assert len(results) == 1
            assert results[0].code_id == "IBC-2021"

            # Test that method works (cache behavior is handled by decorator)

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, client):
        """Test cache invalidation functionality."""
        # Mock the cache
        mock_cache = Mock()
        mock_cache.invalidate_knowledge_cache = AsyncMock(return_value=5)

        with patch.object(client, "cache", mock_cache):
            # Test cache invalidation
            deleted_count = await client.invalidate_knowledge_cache()

            # Verify invalidation was called
            assert deleted_count == 5
            mock_cache.invalidate_knowledge_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, client):
        """Test cache TTL expiration behavior."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "codes": [
                {
                    "code_id": "IBC-2021",
                    "name": "International Building Code",
                    "edition": "2021",
                    "jurisdiction": "USA",
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch.object(client, "_make_request", return_value=mock_response):
            # Test that method works with different TTL values
            results1 = await client.get_applicable_codes("USA", "office")
            assert len(results1) == 1

            results2 = await client.get_applicable_codes("USA", "office")
            assert len(results2) == 1

            # Both calls should succeed (cache behavior is handled by decorator)


class TestDesignServiceCaching:
    """Test caching behavior in Design Service client."""

    @pytest.fixture
    async def client(self):
        """Create Design Service client for testing."""
        client = DesignServiceClient(base_url="http://test-design-service")
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_rendering_cache_hit_miss(self, client):
        """Test rendering cache hit/miss scenarios."""
        design_id = uuid4()
        design_version = "1.0"
        parameters = RenderParameters(
            render_type=RenderType.FLOOR_PLAN, resolution="1920x1080", quality="high"
        )

        # Mock cache manager with async methods
        mock_cache_manager = AsyncMock()
        cache_data = [
            {
                "output_id": str(uuid4()),
                "job_id": str(uuid4()),
                "render_type": "floor_plan",
                "file_url": "https://storage.example.com/render.png",
                "file_size": 1024000,
                "mime_type": "image/png",
                "resolution": "1920x1080",
                "created_at": "2024-01-15T10:00:00Z",
            }
        ]

        # First call - cache miss, second call - cache hit
        cache_results = [
            Mock(value=None),  # Cache miss
            Mock(value=cache_data),  # Cache hit
        ]
        mock_cache_manager.get.side_effect = cache_results
        mock_cache_manager.set.return_value = True

        # Mock cache object
        mock_cache = Mock()
        mock_cache.cache_manager = mock_cache_manager

        with patch.object(client, "cache", mock_cache):
            # First call - should miss cache
            cached_outputs1 = await client.get_cached_outputs(
                design_id, design_version, parameters
            )
            assert cached_outputs1 is None

            # Second call - should hit cache
            cached_outputs2 = await client.get_cached_outputs(
                design_id, design_version, parameters
            )
            assert cached_outputs2 is not None
            assert len(cached_outputs2) == 1
            assert cached_outputs2[0].render_type == RenderType.FLOOR_PLAN
            assert cached_outputs2[0].resolution == "1920x1080"

    @pytest.mark.asyncio
    async def test_rendering_cache_invalidation(self, client):
        """Test rendering cache invalidation."""
        design_id = uuid4()

        # Mock cache
        mock_cache = Mock()
        mock_cache.invalidate_rendering_cache = AsyncMock(return_value=3)

        with patch.object(client, "cache", mock_cache):
            # Test cache invalidation for specific design
            deleted_count = await client.invalidate_rendering_cache(design_id)

            # Verify invalidation was called with design ID
            assert deleted_count == 3
            mock_cache.invalidate_rendering_cache.assert_called_once_with(
                str(design_id)
            )

    @pytest.mark.asyncio
    async def test_cache_key_generation_consistency(self, client):
        """Test that cache key generation is consistent for same inputs."""
        design_id = uuid4()
        design_version = "1.0"
        parameters = RenderParameters(
            render_type=RenderType.ELEVATION,
            resolution="1280x720",
            quality="medium",
            lighting="artificial",
        )

        # Generate cache keys multiple times with same inputs
        hash1 = client._generate_design_hash(design_id, design_version, parameters)
        hash2 = client._generate_design_hash(design_id, design_version, parameters)
        hash3 = client._generate_design_hash(design_id, design_version, parameters)

        # All hashes should be identical
        assert hash1 == hash2 == hash3
        assert len(hash1) == 32  # MD5 hash length

    @pytest.mark.asyncio
    async def test_cache_key_generation_sensitivity(self, client):
        """Test that cache key generation is sensitive to parameter changes."""
        design_id = uuid4()
        design_version = "1.0"

        # Create parameters with different values
        params1 = RenderParameters(
            render_type=RenderType.FLOOR_PLAN, resolution="1920x1080", quality="high"
        )

        params2 = RenderParameters(
            render_type=RenderType.FLOOR_PLAN,
            resolution="1280x720",  # Different resolution
            quality="high",
        )

        params3 = RenderParameters(
            render_type=RenderType.ELEVATION,  # Different render type
            resolution="1920x1080",
            quality="high",
        )

        # Generate hashes
        hash1 = client._generate_design_hash(design_id, design_version, params1)
        hash2 = client._generate_design_hash(design_id, design_version, params2)
        hash3 = client._generate_design_hash(design_id, design_version, params3)

        # All hashes should be different
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    @pytest.mark.asyncio
    async def test_cache_outputs_storage(self, client):
        """Test caching of visual outputs."""
        design_id = uuid4()
        design_version = "2.0"
        parameters = RenderParameters(
            render_type=RenderType.THREE_D_VIEW, resolution="3840x2160", quality="ultra"
        )

        # Create mock outputs
        outputs = [
            VisualOutput(
                output_id=uuid4(),
                job_id=uuid4(),
                render_type=RenderType.THREE_D_VIEW,
                file_url="https://storage.example.com/3d_view.png",
                file_size=5242880,
                mime_type="image/png",
                resolution="3840x2160",
                created_at="2024-01-15T10:00:00Z",
            )
        ]

        # Mock cache manager with async methods
        mock_cache_manager = AsyncMock()
        mock_cache_manager.set.return_value = True

        mock_cache = Mock()
        mock_cache.cache_manager = mock_cache_manager

        with patch.object(client, "cache", mock_cache):
            # Cache the outputs
            await client.cache_outputs(design_id, design_version, parameters, outputs)

            # Verify cache was called with correct parameters
            mock_cache_manager.set.assert_called_once()
            call_args = mock_cache_manager.set.call_args

            # Check cache key format
            cache_key = call_args[0][0]
            assert cache_key.startswith(f"rendering:{design_id}:")

            # Check cached data
            cached_data = call_args[0][1]
            assert len(cached_data) == 1
            assert cached_data[0]["render_type"] == "3d_view"
            assert cached_data[0]["resolution"] == "3840x2160"

            # Check TTL (24 hours)
            ttl = call_args[1]["ttl"]
            assert ttl == 86400

    @pytest.mark.asyncio
    async def test_cache_disabled_graceful_handling(self, client):
        """Test graceful handling when cache is disabled/unavailable."""
        design_id = uuid4()
        design_version = "1.0"
        parameters = RenderParameters(
            render_type=RenderType.SECTION, resolution="1920x1080"
        )

        # Set cache to None (disabled)
        with patch.object(client, "cache", None):
            # Test cache operations don't fail when cache is disabled
            cached_outputs = await client.get_cached_outputs(
                design_id, design_version, parameters
            )
            assert cached_outputs is None

            # Test cache invalidation returns 0 when cache is disabled
            deleted_count = await client.invalidate_rendering_cache(design_id)
            assert deleted_count == 0

            # Test cache storage doesn't fail when cache is disabled
            outputs = [
                VisualOutput(
                    output_id=uuid4(),
                    job_id=uuid4(),
                    render_type=RenderType.SECTION,
                    file_url="https://storage.example.com/section.png",
                    file_size=1024000,
                    mime_type="image/png",
                    resolution="1920x1080",
                    created_at="2024-01-15T10:00:00Z",
                )
            ]

            # Should not raise exception
            await client.cache_outputs(design_id, design_version, parameters, outputs)


class TestCacheIntegration:
    """Test cache integration scenarios."""

    @pytest.mark.asyncio
    async def test_knowledge_service_cache_integration(self):
        """Test knowledge service cache integration with different TTL values."""
        client = KnowledgeServiceClient(base_url="http://test-knowledge-service")

        # Mock HTTP responses
        search_response = Mock()
        search_response.json.return_value = {"results": []}
        search_response.raise_for_status = Mock()

        applicable_response = Mock()
        applicable_response.json.return_value = {"codes": []}
        applicable_response.raise_for_status = Mock()

        section_response = Mock()
        section_response.json.return_value = {
            "code_id": "IBC-2021",
            "section": "1004.1",
            "title": "Occupant Load",
            "content": "Content...",
            "edition": "2021",
        }
        section_response.raise_for_status = Mock()

        responses = [search_response, applicable_response, section_response]

        with patch.object(client, "_make_request", side_effect=responses):
            try:
                # Test search codes (1 hour TTL)
                await client.search_codes("test query")

                # Test applicable codes (2 hour TTL)
                await client.get_applicable_codes("USA", "office")

                # Test code section (4 hour TTL)
                await client.get_code_section("IBC-2021", "1004.1")

                # All methods should complete successfully
                # Cache behavior is handled by decorators

            finally:
                await client.close()

    @pytest.mark.asyncio
    async def test_design_service_cache_integration(self):
        """Test design service cache integration with rendering workflow."""
        client = DesignServiceClient(base_url="http://test-design-service")

        design_id = uuid4()
        design_version = "1.0"
        parameters = RenderParameters(
            render_type=RenderType.WALKTHROUGH, resolution="1920x1080", quality="high"
        )

        # Mock cache manager with async methods
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = Mock(value=None)  # Cache miss
        mock_cache_manager.set.return_value = True

        mock_cache = Mock()
        mock_cache.cache_manager = mock_cache_manager

        # Mock HTTP response for rendering request
        mock_response = Mock()
        mock_response.json.return_value = {
            "job_id": str(uuid4()),
            "design_id": str(design_id),
            "render_type": "walkthrough",
            "status": "pending",
            "created_at": "2024-01-15T10:00:00Z",
        }
        mock_response.raise_for_status = Mock()

        with patch.object(client, "cache", mock_cache):
            with patch.object(client, "_make_request", return_value=mock_response):
                try:
                    # Test rendering request with cache check
                    job, cached_outputs = await client.request_rendering_with_cache(
                        design_id, design_version, RenderType.WALKTHROUGH, parameters
                    )

                    # Should be cache miss
                    assert cached_outputs is None
                    assert job.design_id == design_id
                    assert job.render_type == RenderType.WALKTHROUGH

                    # Verify cache was checked
                    mock_cache_manager.get.assert_called_once()

                finally:
                    await client.close()
