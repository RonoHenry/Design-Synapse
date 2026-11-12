"""API Gateway error handling using shared error classes."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

# Import shared error classes
from common.errors.base import APIError
from common.errors.base import AuthenticationError as BaseAuthenticationError
from common.errors.base import AuthorizationError as BaseAuthorizationError
from common.errors.base import CircuitBreakerError, RateLimitError
from common.errors.base import \
    ServiceUnavailableError as BaseServiceUnavailableError
from common.errors.base import ValidationError as BaseValidationError


class GatewayError(APIError):
    """Base exception for API Gateway errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a gateway error."""
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class ServiceUnavailableError(BaseServiceUnavailableError):
    """Raised when a target service is unavailable."""

    def __init__(self, service_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            service_name=service_name,
            message=f"Service '{service_name}' is currently unavailable",
            retry_after=None,
        )
        if details:
            self.details.update(details)


class AuthenticationError(BaseAuthenticationError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message)


class AuthorizationError(BaseAuthorizationError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Authorization failed"):
        super().__init__(message=message)


class RateLimitExceededError(RateLimitError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None
    ):
        super().__init__(message=message, retry_after=retry_after)


class ValidationError(BaseValidationError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when circuit breaker is open."""

    def __init__(self, service_name: str, retry_after: Optional[int] = None):
        super().__init__(
            service_name=service_name,
            message=f"Circuit breaker is open for service '{service_name}'",
            retry_after=retry_after,
        )


class ServiceRoutingError(GatewayError):
    """Error when routing to a service fails."""

    def __init__(self, service_name: str, message: str = None):
        """Initialize a service routing error."""
        message = message or f"Failed to route request to {service_name}"
        super().__init__(
            message=message,
            error_code="SERVICE_ROUTING_ERROR",
            status_code=503,
            details={"service": service_name},
        )


class ServiceDiscoveryError(GatewayError):
    """Error when service discovery fails."""

    def __init__(self, service_name: str, message: str = None):
        """Initialize a service discovery error."""
        message = message or f"Service {service_name} not found"
        super().__init__(
            message=message,
            error_code="SERVICE_DISCOVERY_ERROR",
            status_code=503,
            details={"service": service_name},
        )
