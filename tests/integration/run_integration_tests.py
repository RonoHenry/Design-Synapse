#!/usr/bin/env python3
"""Integration test runner script.

This script provides a comprehensive way to run integration tests with proper setup,
teardown, and reporting. It follows TDD approach - written to fail initially.
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

# Add packages to path
packages_path = Path(__file__).parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.config.database import DatabaseConfig
from common.testing.database import create_test_engine


@dataclass
class TestRunConfig:
    """Configuration for test runs."""

    test_pattern: str = "test_*.py"
    parallel: bool = False
    verbose: bool = True
    coverage: bool = False
    timeout: int = 300
    database_setup: bool = True
    external_services: bool = False
    markers: Optional[str] = None
    output_format: str = "detailed"


class IntegrationTestRunner:
    """Manages integration test execution with proper setup and teardown."""

    def __init__(self, config: TestRunConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.test_db_engine = None
        self.services_started: List[str] = []

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for test runner."""
        logging.basicConfig(
            level=logging.INFO if self.config.verbose else logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return logging.getLogger(__name__)

    async def setup_test_environment(self) -> bool:
        """Setup test environment including database and external services.

        This should FAIL initially - test environment setup not implemented.
        """
        self.logger.info("Setting up integration test environment...")

        try:
            # Setup test database if required
            if self.config.database_setup:
                await self._setup_test_database()

            # Setup external service mocks if required
            if self.config.external_services:
                await self._setup_external_services()

            # Validate environment
            await self._validate_test_environment()

            self.logger.info("Test environment setup completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {e}")
            return False

    async def _setup_test_database(self):
        """Setup test database infrastructure.

        This should FAIL initially - database setup not implemented.
        """
        self.logger.info("Setting up test database...")

        # Create test database engine
        test_db_url = os.getenv("DATABASE_URL", "sqlite:///test_integration.db")
        self.test_db_engine = create_test_engine(test_db_url)

        # Validate database connectivity
        try:
            with self.test_db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            raise RuntimeError(f"Test database connection failed: {e}")

        self.logger.info("Test database setup completed")

    async def _setup_external_services(self):
        """Setup external service mocks.

        This should FAIL initially - external service mocking not implemented.
        """
        self.logger.info("Setting up external service mocks...")

        # Mock Pinecone
        os.environ["VECTOR_PINECONE_API_KEY"] = "test-pinecone-key"
        os.environ["VECTOR_PINECONE_ENVIRONMENT"] = "test-environment"

        # Mock OpenAI
        os.environ["LLM_OPENAI_API_KEY"] = "test-openai-key"

        # This should fail - proper mocking infrastructure not implemented
        from unittest.mock import patch

        # These patches should be applied globally for integration tests
        self.pinecone_patch = patch("pinecone.init")
        self.openai_patch = patch("openai.ChatCompletion.create")

        self.pinecone_patch.start()
        self.openai_patch.start()

        self.logger.info("External service mocks setup completed")

    async def _validate_test_environment(self):
        """Validate test environment is ready.

        This should FAIL initially - validation not implemented.
        """
        self.logger.info("Validating test environment...")

        # Check required environment variables
        required_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "ENVIRONMENT"]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise RuntimeError(
                f"Missing required environment variables: {missing_vars}"
            )

        # Validate database connectivity
        if self.config.database_setup and self.test_db_manager:
            if not await self.test_db_manager.is_healthy():
                raise RuntimeError("Test database validation failed")

        # Validate Python path includes packages
        if str(packages_path) not in sys.path:
            raise RuntimeError("Packages path not in Python path")

        self.logger.info("Test environment validation completed")

    async def run_tests(self) -> Tuple[bool, Dict[str, any]]:
        """Run integration tests and return results.

        This should FAIL initially - test execution not fully implemented.
        """
        self.logger.info("Starting integration test execution...")

        # Build pytest command
        cmd = self._build_pytest_command()

        # Execute tests
        start_time = time.time()
        result = await self._execute_pytest(cmd)
        end_time = time.time()

        # Process results
        test_results = {
            "success": result.returncode == 0,
            "duration": end_time - start_time,
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

        # Log results
        if test_results["success"]:
            self.logger.info(
                f"Tests completed successfully in {test_results['duration']:.2f}s"
            )
        else:
            self.logger.error(f"Tests failed after {test_results['duration']:.2f}s")
            self.logger.error(f"Error output: {result.stderr}")

        return test_results["success"], test_results

    def _build_pytest_command(self) -> List[str]:
        """Build pytest command with appropriate options."""
        cmd = ["python", "-m", "pytest"]

        # Add test directory
        cmd.append("tests/integration")

        # Add pattern
        if self.config.test_pattern != "test_*.py":
            cmd.extend(["-k", self.config.test_pattern])

        # Add markers
        if self.config.markers:
            cmd.extend(["-m", self.config.markers])

        # Add verbosity
        if self.config.verbose:
            cmd.append("-v")

        # Add parallel execution
        if self.config.parallel:
            cmd.extend(["-n", "auto"])

        # Add coverage
        if self.config.coverage:
            cmd.extend(
                [
                    "--cov=packages",
                    "--cov=apps",
                    "--cov-report=html",
                    "--cov-report=term-missing",
                ]
            )

        # Add timeout
        cmd.extend(["--timeout", str(self.config.timeout)])

        # Add output format
        if self.config.output_format == "junit":
            cmd.extend(["--junit-xml=test-results.xml"])

        return cmd

    async def _execute_pytest(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute pytest command asynchronously."""
        self.logger.info(f"Executing: {' '.join(cmd)}")

        # Run pytest
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent.parent,
        )

        stdout, stderr = await process.communicate()

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout.decode() if stdout else "",
            stderr=stderr.decode() if stderr else "",
        )

    async def teardown_test_environment(self):
        """Teardown test environment and cleanup resources."""
        self.logger.info("Tearing down test environment...")

        try:
            # Stop external service mocks
            if hasattr(self, "pinecone_patch"):
                self.pinecone_patch.stop()
            if hasattr(self, "openai_patch"):
                self.openai_patch.stop()

            # Cleanup test database
            if self.test_db_engine:
                self.test_db_engine.dispose()

            self.logger.info("Test environment teardown completed")

        except Exception as e:
            self.logger.error(f"Error during teardown: {e}")

    async def run_health_checks(self) -> Dict[str, bool]:
        """Run health checks on test infrastructure.

        This should FAIL initially - health checks not implemented.
        """
        self.logger.info("Running infrastructure health checks...")

        health_results = {}

        # Check database health
        if self.test_db_engine:
            try:
                with self.test_db_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                health_results["database"] = True
            except Exception:
                health_results["database"] = False
        else:
            health_results["database"] = False

        # Check Python environment
        try:
            import asyncio

            import pytest
            import sqlalchemy

            health_results["python_environment"] = True
        except ImportError as e:
            self.logger.error(f"Missing Python dependencies: {e}")
            health_results["python_environment"] = False

        # Check file system permissions
        try:
            test_file = Path("/tmp/integration_test_write_check")
            test_file.write_text("test")
            test_file.unlink()
            health_results["filesystem"] = True
        except Exception as e:
            self.logger.error(f"Filesystem check failed: {e}")
            health_results["filesystem"] = False

        # Log results
        for component, healthy in health_results.items():
            status = "HEALTHY" if healthy else "UNHEALTHY"
            self.logger.info(f"{component}: {status}")

        return health_results


async def main():
    """Main entry point for integration test runner."""
    parser = argparse.ArgumentParser(description="Integration Test Runner")
    parser.add_argument("--pattern", default="test_*.py", help="Test pattern to run")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--no-verbose", action="store_true", help="Reduce verbosity")
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Test timeout in seconds"
    )
    parser.add_argument(
        "--no-database", action="store_true", help="Skip database setup"
    )
    parser.add_argument(
        "--external-services", action="store_true", help="Setup external service mocks"
    )
    parser.add_argument("--markers", help="Pytest markers to filter tests")
    parser.add_argument(
        "--output-format", choices=["detailed", "junit"], default="detailed"
    )
    parser.add_argument(
        "--health-check-only", action="store_true", help="Only run health checks"
    )

    args = parser.parse_args()

    # Create configuration
    config = TestRunConfig(
        test_pattern=args.pattern,
        parallel=args.parallel,
        verbose=not args.no_verbose,
        coverage=args.coverage,
        timeout=args.timeout,
        database_setup=not args.no_database,
        external_services=args.external_services,
        markers=args.markers,
        output_format=args.output_format,
    )

    # Create test runner
    runner = IntegrationTestRunner(config)

    try:
        # Setup environment
        if not await runner.setup_test_environment():
            print("Failed to setup test environment", file=sys.stderr)
            return 1

        # Run health checks
        health_results = await runner.run_health_checks()
        if not all(health_results.values()):
            print("Health checks failed", file=sys.stderr)
            return 1

        # Run health check only if requested
        if args.health_check_only:
            print("Health checks passed")
            return 0

        # Run tests
        success, results = await runner.run_tests()

        # Print results
        print(f"\nTest Results:")
        print(f"Success: {success}")
        print(f"Duration: {results['duration']:.2f}s")
        print(f"Command: {results['command']}")

        if not success:
            print(f"Error Output:\n{results['stderr']}")

        return 0 if success else 1

    except Exception as e:
        print(f"Test runner failed: {e}", file=sys.stderr)
        return 1

    finally:
        # Always cleanup
        await runner.teardown_test_environment()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
