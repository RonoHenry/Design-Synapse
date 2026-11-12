"""
Integration test configuration for workspace-level testing.

This module provides shared fixtures and utilities for testing across services.
Following TDD methodology - these tests define the expected behavior.
"""
import asyncio
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator

import pytest

# Import dependencies conditionally to avoid import errors during basic testing
try:
    import docker
    from httpx import AsyncClient
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from testcontainers.postgres import PostgresContainer

    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database() -> Generator[Dict[str, str], None, None]:
    """
    Create isolated test database for integration tests.

    This fixture should:
    - Start PostgreSQL containers for each service
    - Provide connection URLs
    - Clean up after tests
    """
    if not DEPENDENCIES_AVAILABLE:
        pytest.skip("Database dependencies not available")

    # Use separate containers for each service to avoid database creation issues
    containers = {}
    try:
        # Start containers for each service
        containers["user_service"] = PostgresContainer("postgres:13")
        containers["project_service"] = PostgresContainer("postgres:13")
        containers["knowledge_service"] = PostgresContainer("postgres:13")

        # Start all containers
        for service, container in containers.items():
            container.start()

        # Return connection URLs
        yield {
            service: container.get_connection_url()
            for service, container in containers.items()
        }

    finally:
        # Clean up containers
        for container in containers.values():
            try:
                container.stop()
            except Exception:
                pass  # Ignore cleanup errors


@pytest.fixture(scope="session")
def service_containers(test_database) -> Dict[str, Any]:
    """
    Start service containers for integration testing.

    For now, this returns mock containers since we're focusing on TDD tests.
    In a real implementation, this would start actual service containers.
    """
    if not DEPENDENCIES_AVAILABLE:
        pytest.skip("Docker dependencies not available")

    # Return mock containers for now - tests will fail and drive implementation
    containers = {}

    for service_name in ["user-service", "project-service", "knowledge-service"]:
        containers[service_name] = start_service_container(
            None, service_name, test_database.get(service_name.replace("-", "_"), "")
        )

    return containers


@pytest.fixture
def service_clients(service_containers) -> dict:
    """
    Create HTTP clients for each service.

    For now, this creates mock clients that will fail tests and drive implementation.
    """
    clients = {}

    for service_name, container in service_containers.items():
        # Create mock clients that will fail tests initially
        port = container.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
        base_url = f"http://localhost:{port}"

        # Create a mock client that will fail - this drives TDD implementation
        class MockAsyncClient:
            def __init__(self, base_url):
                self.base_url = base_url

            async def get(self, path, **kwargs):
                # This will fail initially - no real service running
                import httpx

                async with httpx.AsyncClient() as client:
                    return await client.get(f"{self.base_url}{path}", **kwargs)

            async def post(self, path, **kwargs):
                import httpx

                async with httpx.AsyncClient() as client:
                    return await client.post(f"{self.base_url}{path}", **kwargs)

        clients[service_name] = MockAsyncClient(base_url)

    return clients


@pytest.fixture
def test_data_factory():
    """
    Factory for creating test data across services.

    This fixture should:
    - Provide methods to create test users, projects, resources
    - Handle cross-service data relationships
    - Clean up test data after tests
    """
    # Import the factory we created
    import sys
    from pathlib import Path

    # Add the tests directory to the path
    tests_dir = Path(__file__).parent
    sys.path.insert(0, str(tests_dir))

    from factories import IntegrationTestFactory

    factory = IntegrationTestFactory()

    try:
        yield factory
    finally:
        factory.cleanup()


# Helper functions that need to be implemented
def start_service_container(client, service_name: str, db_url: str):
    """Start a service container with proper configuration."""

    # This function needs to be implemented
    # For now, create a mock container object
    class MockContainer:
        def __init__(self, service_name: str):
            self.service_name = service_name
            self.status = "running"
            self.attrs = {
                "NetworkSettings": {
                    "Ports": {
                        "8000/tcp": [
                            {"HostPort": str(8000 + hash(service_name) % 1000)}
                        ]
                    }
                }
            }

        def stop(self):
            self.status = "stopped"

        def remove(self):
            pass

        def reload(self):
            pass

        def kill(self, signal="SIGTERM"):
            self.status = "stopped"

        def wait(self, timeout=30):
            return {"StatusCode": 0}

    return MockContainer(service_name)


def wait_for_services_healthy(containers: dict, timeout: int = 60):
    """Wait for all services to report healthy status."""
    # This function needs to be implemented
    # For now, just return success
    return True


class ServiceManager:
    """Manager for service lifecycle during integration tests."""

    def __init__(self):
        self.services = {}
        self.containers = {}

    def start_service(self, service_name: str, config: dict = None):
        """Start a service for testing."""
        # Mock implementation for now
        self.services[service_name] = {"status": "running", "config": config}
        return True

    def stop_service(self, service_name: str):
        """Stop a service."""
        if service_name in self.services:
            self.services[service_name]["status"] = "stopped"
            return True
        return False

    def get_service_url(self, service_name: str) -> str:
        """Get the URL for a service."""
        port = 8000 + hash(service_name) % 1000
        return f"http://localhost:{port}"

    def cleanup(self):
        """Clean up all services."""
        for service_name in list(self.services.keys()):
            self.stop_service(service_name)


class IntegrationTestHelper:
    """Helper utilities for integration tests."""

    def __init__(self):
        self.service_manager = ServiceManager()

    async def wait_for_service_ready(self, service_url: str, timeout: int = 30):
        """Wait for a service to be ready."""
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/health")
                    if response.status_code == 200:
                        return True
            except Exception:
                pass

            await asyncio.sleep(1)

        return False

    async def create_test_user(self, user_data: dict):
        """Create a test user via API."""
        # Mock implementation for now
        return {"id": 1, "email": user_data.get("email", "test@example.com")}

    async def create_test_project(self, project_data: dict):
        """Create a test project via API."""
        # Mock implementation for now
        return {"id": 1, "name": project_data.get("name", "Test Project")}

    def cleanup(self):
        """Clean up test resources."""
        self.service_manager.cleanup()


# Import database testing fixtures
try:
    import sys
    from pathlib import Path

    # Add the project root to the Python path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from packages.common.testing.database import (DatabaseTestManager,
                                                  db_test_manager,
                                                  knowledge_db_session,
                                                  project_db_session,
                                                  user_db_session)

    # Re-export fixtures so they're available to tests
    __all__ = [
        "db_test_manager",
        "user_db_session",
        "knowledge_db_session",
        "project_db_session",
    ]

except ImportError as e:
    print(f"Warning: Database testing fixtures not available: {e}")

    # Create placeholder fixtures that skip tests
    @pytest.fixture
    def db_test_manager():
        pytest.skip("Database testing utilities not available")

    @pytest.fixture
    def user_db_session():
        pytest.skip("Database testing utilities not available")

    @pytest.fixture
    def knowledge_db_session():
        pytest.skip("Database testing utilities not available")

    @pytest.fixture
    def project_db_session():
        pytest.skip("Database testing utilities not available")
