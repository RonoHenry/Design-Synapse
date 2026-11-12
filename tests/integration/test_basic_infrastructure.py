"""
Basic infrastructure tests to verify TDD approach.

These tests should fail initially, demonstrating that we need to implement
the infrastructure to make them pass.
"""
import pytest


class TestBasicInfrastructure:
    """Basic tests to verify our TDD infrastructure setup."""

    def test_pytest_is_working(self):
        """Test that pytest is working correctly."""
        assert True, "Pytest should be working"

    def test_test_directory_structure_exists(self):
        """Test that our test directory structure is in place."""
        import os
        from pathlib import Path

        test_dir = Path(__file__).parent.parent

        # Check that key directories exist
        assert (
            test_dir / "integration"
        ).exists(), "Integration test directory should exist"
        assert (test_dir / "mocks").exists(), "Mocks directory should exist"
        assert (test_dir / "scripts").exists(), "Scripts directory should exist"

        # Check that key files exist
        assert (
            test_dir / "docker-compose.integration.yml"
        ).exists(), "Docker compose file should exist"
        assert (test_dir / "pytest.ini").exists(), "Pytest config should exist"
        assert (
            test_dir / "requirements.txt"
        ).exists(), "Requirements file should exist"

    @pytest.mark.integration
    def test_integration_marker_works(self):
        """Test that integration marker is working."""
        assert True, "Integration marker should work"

    def test_async_support_works(self):
        """Test that async test support is working."""
        import asyncio

        async def async_function():
            await asyncio.sleep(0.001)
            return "async works"

        # This should work with pytest-asyncio
        result = asyncio.run(async_function())
        assert result == "async works"
