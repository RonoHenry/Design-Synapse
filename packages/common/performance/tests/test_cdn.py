"""
Tests for CDN integration for static asset delivery.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Optimize and improve code quality
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ..cdn import AssetInfo, CDNManager
from ..models import CDNConfig, CDNStats


class TestCDNManager:
    """Test CDN manager functionality."""

    @pytest.mark.asyncio
    async def test_cdn_manager_initialization(self, cdn_config):
        """Test CDN manager initialization."""
        # This test will fail until we implement CDNManager
        cdn_manager = CDNManager(cdn_config)
        assert cdn_manager.config == cdn_config
        assert cdn_manager.provider == cdn_config.provider

    @pytest.mark.asyncio
    async def test_cdn_asset_upload(self, cdn_config):
        """Test uploading asset to CDN."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "url": "https://cdn.example.com/asset.js",
            }
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            asset_data = b"console.log('test');"
            result = await cdn_manager.upload_asset(
                "test.js", asset_data, "application/javascript"
            )

            assert result.success is True
            assert result.cdn_url.startswith("https://")

    @pytest.mark.asyncio
    async def test_cdn_asset_invalidation(self, cdn_config):
        """Test invalidating cached assets on CDN."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"success": True}
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            result = await cdn_manager.invalidate_cache(["test.js", "test.css"])
            assert result is True

    @pytest.mark.asyncio
    async def test_cdn_asset_compression(self, cdn_config):
        """Test asset compression before CDN upload."""
        cdn_config.compression_enabled = True

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "url": "https://cdn.example.com/asset.js",
            }
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            # Large asset that should be compressed
            large_asset = b"console.log('test');" * 1000
            result = await cdn_manager.upload_asset(
                "large.js", large_asset, "application/javascript"
            )

            assert result.success is True
            assert result.compressed_size < len(large_asset)

    @pytest.mark.asyncio
    async def test_cdn_asset_minification(self, cdn_config):
        """Test asset minification for supported formats."""
        cdn_config.minification_enabled = True

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "url": "https://cdn.example.com/asset.js",
            }
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            # JavaScript with whitespace and comments
            js_code = b"""
            // This is a comment
            function test() {
                console.log('hello world');
            }
            """

            result = await cdn_manager.upload_asset(
                "test.js", js_code, "application/javascript"
            )
            assert result.success is True
            assert result.minified is True

    @pytest.mark.asyncio
    async def test_cdn_cache_headers(self, cdn_config):
        """Test CDN cache header configuration."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {
                "Cache-Control": f"public, max-age={cdn_config.cache_ttl}",
                "ETag": '"abc123"',
            }
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            headers = await cdn_manager.get_cache_headers("test.js")
            assert "Cache-Control" in headers
            assert str(cdn_config.cache_ttl) in headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_cdn_supported_formats(self, cdn_config):
        """Test CDN support for different asset formats."""
        cdn_manager = CDNManager(cdn_config)

        # Test supported formats
        for format_ext in cdn_config.supported_formats:
            is_supported = cdn_manager.is_format_supported(f"test.{format_ext}")
            assert is_supported is True

        # Test unsupported format
        is_supported = cdn_manager.is_format_supported("test.xyz")
        assert is_supported is False

    @pytest.mark.asyncio
    async def test_cdn_statistics_tracking(self, cdn_config):
        """Test CDN statistics collection."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "analytics": {
                    "requests": 1000,
                    "cache_hits": 800,
                    "cache_misses": 200,
                    "bandwidth_saved": 50.5,
                }
            }
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            stats = await cdn_manager.get_statistics()
            assert isinstance(stats, CDNStats)
            assert stats.total_requests == 1000
            assert stats.cache_hits == 800
            assert stats.hit_ratio == 0.8

    @pytest.mark.asyncio
    async def test_cdn_error_handling(self, cdn_config):
        """Test CDN error handling for failed operations."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            asset_data = b"test data"
            result = await cdn_manager.upload_asset(
                "test.js", asset_data, "application/javascript"
            )

            assert result.success is False
            assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_cdn_batch_operations(self, cdn_config):
        """Test CDN batch upload operations."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "results": [
                    {"file": "test1.js", "url": "https://cdn.example.com/test1.js"},
                    {"file": "test2.css", "url": "https://cdn.example.com/test2.css"},
                ],
            }
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            assets = [
                ("test1.js", b"console.log('test1');", "application/javascript"),
                ("test2.css", b"body { color: red; }", "text/css"),
            ]

            results = await cdn_manager.upload_assets_batch(assets)
            assert len(results) == 2
            assert all(result.success for result in results)


class TestAssetInfo:
    """Test asset information model."""

    def test_asset_info_creation(self):
        """Test asset info creation and properties."""
        asset_info = AssetInfo(
            filename="test.js",
            content_type="application/javascript",
            size_bytes=1024,
            cdn_url="https://cdn.example.com/test.js",
        )

        assert asset_info.filename == "test.js"
        assert asset_info.content_type == "application/javascript"
        assert asset_info.size_bytes == 1024
        assert asset_info.cdn_url.startswith("https://")

    def test_asset_info_compression_ratio(self):
        """Test asset compression ratio calculation."""
        asset_info = AssetInfo(
            filename="test.js",
            content_type="application/javascript",
            size_bytes=1000,
            compressed_size=500,
            cdn_url="https://cdn.example.com/test.js",
        )

        compression_ratio = asset_info.get_compression_ratio()
        assert compression_ratio == 0.5  # 50% compression


class TestCDNProviders:
    """Test different CDN provider implementations."""

    @pytest.mark.asyncio
    async def test_cloudflare_provider(self, cdn_config):
        """Test Cloudflare CDN provider."""
        cdn_config.provider = "cloudflare"

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"success": True}
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            result = await cdn_manager.purge_cache(["test.js"])
            assert result is True

    @pytest.mark.asyncio
    async def test_aws_cloudfront_provider(self, cdn_config):
        """Test AWS CloudFront CDN provider."""
        cdn_config.provider = "aws"

        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_client.create_invalidation.return_value = {
                "Invalidation": {"Id": "test123"}
            }
            mock_boto.return_value = mock_client

            cdn_manager = CDNManager(cdn_config)

            result = await cdn_manager.purge_cache(["test.js"])
            assert result is True


class TestCDNPerformance:
    """Test CDN performance characteristics."""

    @pytest.mark.asyncio
    async def test_cdn_upload_performance(self, cdn_config):
        """Test CDN upload performance measurement."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "url": "https://cdn.example.com/test.js",
            }
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            asset_data = b"console.log('test');" * 100

            start_time = time.time()
            result = await cdn_manager.upload_asset(
                "test.js", asset_data, "application/javascript"
            )
            end_time = time.time()

            upload_time = (end_time - start_time) * 1000  # Convert to ms

            assert result.success is True
            assert result.upload_time_ms >= 0
            assert upload_time < 5000  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_cdn_bandwidth_savings(self, cdn_config):
        """Test CDN bandwidth savings calculation."""
        cdn_config.compression_enabled = True

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "analytics": {"bandwidth_saved": 75.5, "compression_ratio": 0.6}  # MB
            }
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            stats = await cdn_manager.get_statistics()
            assert stats.bandwidth_saved_mb == 75.5

    @pytest.mark.asyncio
    async def test_cdn_concurrent_uploads(self, cdn_config):
        """Test CDN performance under concurrent uploads."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "success": True,
                "url": "https://cdn.example.com/test.js",
            }
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            cdn_manager = CDNManager(cdn_config)

            async def upload_asset(index):
                asset_data = f"console.log('test{index}');".encode()
                return await cdn_manager.upload_asset(
                    f"test{index}.js", asset_data, "application/javascript"
                )

            # Test concurrent uploads
            start_time = time.time()
            tasks = [upload_asset(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # All uploads should succeed
            assert all(result.success for result in results)

            # Should complete within reasonable time
            total_time = end_time - start_time
            assert total_time < 10.0  # 10 seconds max for 10 concurrent uploads


# Import asyncio for concurrent tests
import asyncio
