#!/usr/bin/env python3
"""
Integration test runner script.

This script sets up the integration test environment and runs the tests.
Following TDD methodology - this defines the expected test execution flow.
"""
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import docker
import psutil


class IntegrationTestRunner:
    """
    Runner for integration tests with proper setup and teardown.

    This runner should:
    - Start test infrastructure (databases, services)
    - Wait for services to be ready
    - Run integration tests
    - Clean up infrastructure
    - Report results
    """

    def __init__(self):
        self.docker_client = None
        self.compose_project = "integration-tests"
        self.test_dir = Path(__file__).parent
        self.workspace_root = self.test_dir.parent
        self.services_started = False

    def setup_environment(self):
        """Set up environment variables for testing."""
        os.environ.update(
            {
                "ENVIRONMENT": "testing",
                "COMPOSE_PROJECT_NAME": self.compose_project,
                "PYTHONPATH": str(self.workspace_root),
            }
        )

    def start_infrastructure(self) -> bool:
        """
        Start the test infrastructure using Docker Compose.

        Expected behavior:
        - Should start PostgreSQL database
        - Should start all service containers
        - Should wait for services to be healthy
        - Should return True if successful, False otherwise
        """
        print("🚀 Starting integration test infrastructure...")

        try:
            # This will fail initially - we need proper Docker setup
            compose_file = self.test_dir / "docker-compose.integration.yml"

            # Start services
            result = subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    str(compose_file),
                    "-p",
                    self.compose_project,
                    "up",
                    "-d",
                    "--build",
                ],
                capture_output=True,
                text=True,
                cwd=self.test_dir,
            )

            if result.returncode != 0:
                print(f"❌ Failed to start infrastructure: {result.stderr}")
                return False

            # Wait for services to be healthy
            if not self.wait_for_services_healthy():
                print("❌ Services did not become healthy in time")
                return False

            self.services_started = True
            print("✅ Integration test infrastructure started successfully")
            return True

        except Exception as e:
            print(f"❌ Error starting infrastructure: {e}")
            return False

    def wait_for_services_healthy(self, timeout: int = 120) -> bool:
        """
        Wait for all services to report healthy status.

        Expected behavior:
        - Should check health of all services
        - Should retry until healthy or timeout
        - Should return True if all healthy, False if timeout
        """
        print("⏳ Waiting for services to become healthy...")

        services = [
            "test-postgres",
            "test-user-service",
            "test-project-service",
            "test-knowledge-service",
        ]

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # This will fail initially - we need proper health checking
                result = subprocess.run(
                    [
                        "docker-compose",
                        "-f",
                        str(self.test_dir / "docker-compose.integration.yml"),
                        "-p",
                        self.compose_project,
                        "ps",
                        "--format",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=self.test_dir,
                )

                if result.returncode == 0:
                    # Check if all services are healthy
                    # This is a simplified check - real implementation needed
                    healthy_count = 0
                    for service in services:
                        # Check service health via docker-compose
                        health_result = subprocess.run(
                            [
                                "docker-compose",
                                "-f",
                                str(self.test_dir / "docker-compose.integration.yml"),
                                "-p",
                                self.compose_project,
                                "exec",
                                "-T",
                                service,
                                "echo",
                                "healthy",
                            ],
                            capture_output=True,
                            text=True,
                            cwd=self.test_dir,
                        )

                        if health_result.returncode == 0:
                            healthy_count += 1

                    if healthy_count == len(services):
                        print("✅ All services are healthy")
                        return True

            except Exception as e:
                print(f"⚠️  Health check error: {e}")

            print(
                f"⏳ Services not ready yet, waiting... ({int(time.time() - start_time)}s)"
            )
            time.sleep(5)

        print(f"❌ Services did not become healthy within {timeout} seconds")
        return False

    def run_tests(self) -> bool:
        """
        Run the integration tests.

        Expected behavior:
        - Should run pytest with integration test configuration
        - Should generate coverage reports
        - Should return True if tests pass, False if they fail
        """
        print("🧪 Running integration tests...")

        try:
            # This will fail initially - we need proper test setup
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(self.test_dir / "integration"),
                    "-v",
                    "--tb=short",
                    "--durations=10",
                    "--cov=tests",
                    "--cov-report=term-missing",
                    "--cov-report=html:htmlcov",
                    "-m",
                    "integration",
                ],
                cwd=self.workspace_root,
            )

            if result.returncode == 0:
                print("✅ Integration tests passed!")
                return True
            else:
                print("❌ Integration tests failed!")
                return False

        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return False

    def stop_infrastructure(self):
        """
        Stop and clean up the test infrastructure.

        Expected behavior:
        - Should stop all service containers
        - Should remove containers and networks
        - Should clean up volumes if requested
        - Should handle cleanup errors gracefully
        """
        if not self.services_started:
            return

        print("🧹 Cleaning up integration test infrastructure...")

        try:
            compose_file = self.test_dir / "docker-compose.integration.yml"

            # Stop and remove containers
            subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    str(compose_file),
                    "-p",
                    self.compose_project,
                    "down",
                    "-v",
                    "--remove-orphans",
                ],
                capture_output=True,
                text=True,
                cwd=self.test_dir,
            )

            print("✅ Infrastructure cleaned up successfully")

        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")

    def run(self) -> int:
        """
        Run the complete integration test suite.

        Expected behavior:
        - Should set up environment
        - Should start infrastructure
        - Should run tests
        - Should clean up infrastructure
        - Should return 0 for success, 1 for failure
        """
        try:
            self.setup_environment()

            if not self.start_infrastructure():
                return 1

            # Give services a moment to fully initialize
            time.sleep(10)

            success = self.run_tests()

            return 0 if success else 1

        except KeyboardInterrupt:
            print("\n🛑 Integration tests interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return 1
        finally:
            self.stop_infrastructure()


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print("\n🛑 Received interrupt signal, cleaning up...")
    sys.exit(1)


def main():
    """Main entry point for integration test runner."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check prerequisites
    try:
        import docker

        docker.from_env().ping()
    except Exception as e:
        print(f"❌ Docker is not available: {e}")
        print("Please ensure Docker is installed and running")
        return 1

    # Run integration tests
    runner = IntegrationTestRunner()
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
