"""Service registry for managing service endpoints."""

import os
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class ServiceName(Enum):
    """Enumeration of available services."""
    USER_SERVICE = "user-service"
    PROJECT_SERVICE = "project-service"
    KNOWLEDGE_SERVICE = "knowledge-service"
    DESIGN_SERVICE = "design-service"
    ANALYTICS_SERVICE = "analytics-service"
    MARKETPLACE_SERVICE = "marketplace-service"


@dataclass
class ServiceConfig:
    """Configuration for a service."""
    name: str
    host: str
    port: int
    protocol: str = "http"
    api_prefix: str = "/api/v1"
    
    @property
    def base_url(self) -> str:
        """Get the full base URL for the service."""
        return f"{self.protocol}://{self.host}:{self.port}{self.api_prefix}"
    
    @property
    def health_url(self) -> str:
        """Get the health check URL."""
        return f"{self.protocol}://{self.host}:{self.port}/health"
    
    @property
    def ready_url(self) -> str:
        """Get the readiness check URL."""
        return f"{self.protocol}://{self.host}:{self.port}/ready"


class ServiceRegistry:
    """Registry for managing service configurations."""
    
    def __init__(self):
        """Initialize the service registry with default configurations."""
        self._services: Dict[str, ServiceConfig] = {}
        self._load_default_configs()
    
    def _load_default_configs(self):
        """Load default service configurations from environment variables."""
        # User Service
        self.register(ServiceConfig(
            name=ServiceName.USER_SERVICE.value,
            host=os.getenv("USER_SERVICE_HOST", "localhost"),
            port=int(os.getenv("USER_SERVICE_PORT", "8001")),
            protocol=os.getenv("USER_SERVICE_PROTOCOL", "http"),
        ))
        
        # Project Service
        self.register(ServiceConfig(
            name=ServiceName.PROJECT_SERVICE.value,
            host=os.getenv("PROJECT_SERVICE_HOST", "localhost"),
            port=int(os.getenv("PROJECT_SERVICE_PORT", "8003")),
            protocol=os.getenv("PROJECT_SERVICE_PROTOCOL", "http"),
        ))
        
        # Knowledge Service
        self.register(ServiceConfig(
            name=ServiceName.KNOWLEDGE_SERVICE.value,
            host=os.getenv("KNOWLEDGE_SERVICE_HOST", "localhost"),
            port=int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8002")),
            protocol=os.getenv("KNOWLEDGE_SERVICE_PROTOCOL", "http"),
        ))
        
        # Design Service
        self.register(ServiceConfig(
            name=ServiceName.DESIGN_SERVICE.value,
            host=os.getenv("DESIGN_SERVICE_HOST", "localhost"),
            port=int(os.getenv("DESIGN_SERVICE_PORT", "8000")),
            protocol=os.getenv("DESIGN_SERVICE_PROTOCOL", "http"),
        ))
        
        # Analytics Service
        self.register(ServiceConfig(
            name=ServiceName.ANALYTICS_SERVICE.value,
            host=os.getenv("ANALYTICS_SERVICE_HOST", "localhost"),
            port=int(os.getenv("ANALYTICS_SERVICE_PORT", "8004")),
            protocol=os.getenv("ANALYTICS_SERVICE_PROTOCOL", "http"),
        ))
        
        # Marketplace Service
        self.register(ServiceConfig(
            name=ServiceName.MARKETPLACE_SERVICE.value,
            host=os.getenv("MARKETPLACE_SERVICE_HOST", "localhost"),
            port=int(os.getenv("MARKETPLACE_SERVICE_PORT", "8005")),
            protocol=os.getenv("MARKETPLACE_SERVICE_PROTOCOL", "http"),
        ))
    
    def register(self, config: ServiceConfig):
        """Register a service configuration.
        
        Args:
            config: Service configuration to register
        """
        self._services[config.name] = config
    
    def get(self, service_name: str) -> Optional[ServiceConfig]:
        """Get a service configuration by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service configuration or None if not found
        """
        return self._services.get(service_name)
    
    def get_base_url(self, service_name: str) -> str:
        """Get the base URL for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Base URL for the service
            
        Raises:
            ValueError: If service is not registered
        """
        config = self.get(service_name)
        if not config:
            raise ValueError(f"Service '{service_name}' not registered")
        return config.base_url
    
    def list_services(self) -> Dict[str, ServiceConfig]:
        """List all registered services.
        
        Returns:
            Dictionary of service configurations
        """
        return self._services.copy()


# Global service registry instance
_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance.
    
    Returns:
        Service registry instance
    """
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry
