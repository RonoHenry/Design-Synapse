"""Tests for service registry."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import os
from common.http.service_registry import ServiceRegistry, ServiceConfig, ServiceName


@pytest.fixture
def registry():
    """Create a service registry for testing."""
    return ServiceRegistry()


def test_registry_initialization(registry):
    """Test registry initializes with default services."""
    assert registry.get(ServiceName.USER_SERVICE.value) is not None
    assert registry.get(ServiceName.PROJECT_SERVICE.value) is not None
    assert registry.get(ServiceName.KNOWLEDGE_SERVICE.value) is not None


def test_service_config_base_url():
    """Test service config generates correct base URL."""
    config = ServiceConfig(
        name="test-service",
        host="localhost",
        port=8000,
        protocol="http",
        api_prefix="/api/v1"
    )
    
    assert config.base_url == "http://localhost:8000/api/v1"
    assert config.health_url == "http://localhost:8000/health"
    assert config.ready_url == "http://localhost:8000/ready"


def test_register_custom_service(registry):
    """Test registering a custom service."""
    config = ServiceConfig(
        name="custom-service",
        host="custom.example.com",
        port=9000,
        protocol="https"
    )
    
    registry.register(config)
    
    retrieved = registry.get("custom-service")
    assert retrieved is not None
    assert retrieved.host == "custom.example.com"
    assert retrieved.port == 9000
    assert retrieved.protocol == "https"


def test_get_base_url(registry):
    """Test getting base URL for a service."""
    url = registry.get_base_url(ServiceName.USER_SERVICE.value)
    assert url.startswith("http://")
    assert "/api/v1" in url


def test_get_base_url_nonexistent_service(registry):
    """Test getting base URL for nonexistent service raises error."""
    with pytest.raises(ValueError, match="not registered"):
        registry.get_base_url("nonexistent-service")


def test_list_services(registry):
    """Test listing all services."""
    services = registry.list_services()
    
    assert len(services) >= 3
    assert ServiceName.USER_SERVICE.value in services
    assert ServiceName.PROJECT_SERVICE.value in services
    assert ServiceName.KNOWLEDGE_SERVICE.value in services


def test_environment_variable_configuration(monkeypatch):
    """Test service configuration from environment variables."""
    monkeypatch.setenv("USER_SERVICE_HOST", "custom-host")
    monkeypatch.setenv("USER_SERVICE_PORT", "9999")
    monkeypatch.setenv("USER_SERVICE_PROTOCOL", "https")
    
    registry = ServiceRegistry()
    config = registry.get(ServiceName.USER_SERVICE.value)
    
    assert config.host == "custom-host"
    assert config.port == 9999
    assert config.protocol == "https"
