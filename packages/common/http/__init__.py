"""HTTP client utilities for inter-service communication."""

from .base_client import BaseHTTPClient, CircuitBreakerState
from .service_registry import ServiceRegistry, ServiceConfig
from .clients import UserServiceClient, ProjectServiceClient, KnowledgeServiceClient

__all__ = [
    "BaseHTTPClient",
    "CircuitBreakerState",
    "ServiceRegistry",
    "ServiceConfig",
    "UserServiceClient",
    "ProjectServiceClient",
    "KnowledgeServiceClient",
]
