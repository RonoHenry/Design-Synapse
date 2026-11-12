"""HTTP client utilities for inter-service communication."""

from .base_client import BaseHTTPClient
from .clients import (KnowledgeServiceClient, ProjectServiceClient,
                      UserServiceClient)
from .service_registry import ServiceRegistry

__all__ = [
    "BaseHTTPClient",
    "UserServiceClient",
    "ProjectServiceClient",
    "KnowledgeServiceClient",
    "ServiceRegistry",
]
