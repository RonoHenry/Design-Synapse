"""
Property-based tests for service test execution.

Feature: system-wide-fixes
Property 4: Test collection succeeds
Validates: Requirements 3.1, 3.2
"""

import subprocess
import sys
from pathlib import Path
from typing import List

import pytest


class TestServiceTestExecution:
    """Property-based tests for service test execution."""

    def test_test_collection_succeeds_from_workspace_root(self):
        """
        Property 4: Test collection succeeds
        For any pytest execution from the workspace root,
        test collection should complete without syntax errors

        **Feature: system-wide-fixes, Property 4: Test collection succeeds**
        **Validates: Requirements 3.1, 3.2**
        """
        workspace_root = Path(__file__).parent.parent.parent

        # Test that pytest can collect tests from workspace root without errors
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check that collection succeeded (exit code 0 or 5 for no tests collected)
        assert result.returncode in [0, 5], (
            f"Test collection failed with exit code {result.returncode}. "
            f"Stdout: {result.stdout}. Stderr: {result.stderr}"
        )

        # Check that there are no syntax errors in stderr
        stderr_lower = result.stderr.lower()
        syntax_error_indicators = [
            "syntaxerror",
            "indentationerror",
            "invalid syntax",
            "unexpected indent",
            "unindent does not match",
        ]

        for indicator in syntax_error_indicators:
            assert (
                indicator not in stderr_lower
            ), f"Syntax error detected in test collection: {result.stderr}"

    @pytest.mark.parametrize("service_dir", ["apps/user-service", "apps/labor-service"])
    def test_service_test_collection_succeeds(self, service_dir: str):
        """
        Property test: Each service can collect its tests without errors.
        For any service directory with tests, pytest collection should succeed.
        """
        workspace_root = Path(__file__).parent.parent.parent
        service_path = workspace_root / service_dir

        # Skip if service doesn't exist
        if not service_path.exists():
            pytest.skip(f"Service directory {service_dir} does not exist")

        # Skip if service has no tests directory
        tests_path = service_path / "tests"
        if not tests_path.exists():
            pytest.skip(f"Service {service_dir} has no tests directory")

        # Test that pytest can collect tests from service directory
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=service_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check that collection succeeded (exit code 0 or 5 for no tests collected)
        assert result.returncode in [0, 5], (
            f"Test collection failed for {service_dir} with exit code {result.returncode}. "
            f"Stdout: {result.stdout}. Stderr: {result.stderr}"
        )

        # Check for syntax errors
        stderr_lower = result.stderr.lower()
        syntax_error_indicators = [
            "syntaxerror",
            "indentationerror",
            "invalid syntax",
            "unexpected indent",
            "unindent does not match",
        ]

        for indicator in syntax_error_indicators:
            assert (
                indicator not in stderr_lower
            ), f"Syntax error detected in {service_dir} test collection: {result.stderr}"

    def test_pytest_configuration_is_valid(self):
        """
        Test that pytest configuration files are valid and don't cause collection errors.
        """
        workspace_root = Path(__file__).parent.parent.parent

        # Test workspace root pytest.ini
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert (
            result.returncode == 0
        ), f"Pytest configuration invalid at workspace root. Stderr: {result.stderr}"

        # Check that no configuration errors are reported
        stderr_lower = result.stderr.lower()
        config_error_indicators = [
            "configuration error",
            "invalid configuration",
            "unknown option",
            "bad config",
        ]

        for indicator in config_error_indicators:
            assert (
                indicator not in stderr_lower
            ), f"Configuration error detected: {result.stderr}"

    def test_python_path_accessible_from_services(self):
        """
        Property test: Services can access workspace packages through Python path.
        For any service, it should be able to import packages.common modules.
        """
        workspace_root = Path(__file__).parent.parent.parent

        # Test script that tries to import common packages with explicit path setup
        test_script = """
import sys
from pathlib import Path

# Add workspace root to Python path (relative to service directory)
workspace_root = Path("../..")
sys.path.insert(0, str(workspace_root))

try:
    import packages.common.config
    import packages.common.errors
    print("SUCCESS: All imports successful")
    sys.exit(0)
except ImportError as e:
    print(f"IMPORT_ERROR: {e}")
    print(f"Python path: {sys.path}")
    sys.exit(1)
except Exception as e:
    print(f"OTHER_ERROR: {e}")
    sys.exit(2)
"""

        service_dirs = ["apps/user-service", "apps/labor-service"]

        for service_dir in service_dirs:
            service_path = workspace_root / service_dir

            # Skip if service doesn't exist
            if not service_path.exists():
                continue

            # Run the import test from the service directory
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, (
                f"Import test failed for {service_dir}. "
                f"Exit code: {result.returncode}. "
                f"Stdout: {result.stdout}. Stderr: {result.stderr}"
            )

            assert (
                "SUCCESS" in result.stdout
            ), f"Import test did not report success for {service_dir}. Output: {result.stdout}"

    def test_no_module_not_found_errors_in_collection(self):
        """
        Property test: Test collection should not produce ModuleNotFoundError.
        For any test collection, there should be no module import failures.
        """
        workspace_root = Path(__file__).parent.parent.parent

        # Collect tests and check for ModuleNotFoundError
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-v"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Check stderr for ModuleNotFoundError
        stderr_content = result.stderr.lower()
        stdout_content = result.stdout.lower()

        module_error_indicators = [
            "modulenotfounderror",
            "no module named",
            "importerror",
        ]

        for indicator in module_error_indicators:
            assert (
                indicator not in stderr_content
            ), f"Module import error detected in stderr: {result.stderr}"
            assert (
                indicator not in stdout_content
            ), f"Module import error detected in stdout: {result.stdout}"
