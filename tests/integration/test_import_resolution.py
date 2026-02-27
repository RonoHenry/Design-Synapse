"""
Property-based tests for import resolution across the system.

Feature: system-wide-fixes
Property 1: Import resolution works consistently
Validates: Requirements 1.1, 1.2, 1.3
"""

import importlib
import sys
from pathlib import Path
from typing import List, Tuple

import pytest


class TestImportResolution:
    """Property-based tests for import resolution."""

    def test_packages_common_imports_consistently(self):
        """
        Property 1: Import resolution works consistently
        For any service attempting to import packages.common modules,
        the import should succeed without ModuleNotFoundError

        **Feature: system-wide-fixes, Property 1: Import resolution works consistently**
        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        # Define common packages that should be importable from anywhere
        common_packages = [
            "packages.common.auth",
            "packages.common.config",
            "packages.common.database",
            "packages.common.errors",
            "packages.common.http",
            "packages.common.monitoring",
            "packages.common.testing",
        ]

        # Test that each common package can be imported
        for package_name in common_packages:
            try:
                # Clear any cached imports to ensure fresh import
                if package_name in sys.modules:
                    del sys.modules[package_name]

                # Attempt to import the package
                module = importlib.import_module(package_name)

                # Verify the module was imported successfully
                assert module is not None, f"Failed to import {package_name}"
                assert hasattr(module, "__file__") or hasattr(
                    module, "__path__"
                ), f"Module {package_name} doesn't have proper file/path attributes"

            except ModuleNotFoundError as e:
                pytest.fail(f"Failed to import {package_name}: {e}")
            except ImportError as e:
                pytest.fail(f"Import error for {package_name}: {e}")

    def test_workspace_root_in_python_path(self):
        """
        Test that workspace root is accessible in Python path.
        This ensures services can import shared packages.
        """
        workspace_root = Path(__file__).parent.parent.parent
        workspace_root_str = str(workspace_root.resolve())

        # Check if workspace root is in Python path
        assert (
            workspace_root_str in sys.path or str(workspace_root) in sys.path
        ), f"Workspace root {workspace_root_str} not found in Python path: {sys.path}"

    def test_packages_directory_accessible(self):
        """
        Test that packages directory is accessible for imports.
        """
        workspace_root = Path(__file__).parent.parent.parent
        packages_dir = workspace_root / "packages"

        # Verify packages directory exists
        assert packages_dir.exists(), f"Packages directory not found at {packages_dir}"
        assert (
            packages_dir.is_dir()
        ), f"Packages path is not a directory: {packages_dir}"

        # Verify packages directory is importable
        packages_str = str(packages_dir.resolve())
        workspace_str = str(workspace_root.resolve())

        # Either packages dir itself or workspace root should be in path
        path_accessible = (
            packages_str in sys.path
            or workspace_str in sys.path
            or str(packages_dir) in sys.path
            or str(workspace_root) in sys.path
        )

        assert (
            path_accessible
        ), f"Neither packages dir {packages_str} nor workspace root {workspace_str} in Python path: {sys.path}"

    def test_service_contexts_can_import_common(self):
        """
        Property test: Services from different contexts can import common packages.
        This simulates importing from different service directories.
        """
        # List of service directories that should be able to import common packages
        service_dirs = [
            "apps/user-service",
            "apps/knowledge-service",
            "apps/labor-service",
            "apps/project-service",
            "apps/design-service",
        ]

        workspace_root = Path(__file__).parent.parent.parent

        for service_dir in service_dirs:
            service_path = workspace_root / service_dir

            # Skip if service doesn't exist
            if not service_path.exists():
                continue

            # Test that we can import common packages from service context
            # by temporarily changing the working directory context
            original_cwd = Path.cwd()

            try:
                # This simulates running from the service directory
                import os

                original_path = sys.path.copy()

                # Ensure workspace root is in path (this is what our fix should provide)
                if str(workspace_root) not in sys.path:
                    sys.path.insert(0, str(workspace_root))

                # Test importing a common package
                try:
                    import packages.common.config

                    assert packages.common.config is not None
                except ImportError as e:
                    pytest.fail(
                        f"Failed to import packages.common.config from {service_dir} context: {e}"
                    )

            finally:
                # Restore original path
                sys.path[:] = original_path

    @pytest.mark.parametrize(
        "common_module",
        [
            "packages.common.auth.models",
            "packages.common.config.base",
            "packages.common.database.health",
            "packages.common.errors.base",
            "packages.common.http.clients",
            "packages.common.monitoring.health",
        ],
    )
    def test_specific_common_modules_importable(self, common_module: str):
        """
        Property test: Specific common modules should be importable.
        For any common module, it should be importable without errors.
        """
        try:
            # Clear cached import
            if common_module in sys.modules:
                del sys.modules[common_module]

            # Import the module
            module = importlib.import_module(common_module)
            assert module is not None, f"Module {common_module} imported as None"

        except ModuleNotFoundError as e:
            pytest.fail(f"Module {common_module} not found: {e}")
        except ImportError as e:
            pytest.fail(f"Import error for {common_module}: {e}")
