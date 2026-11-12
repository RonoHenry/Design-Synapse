"""Service-to-service authentication mechanism."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from jose import jwt

from .models import AuthResult, ServiceToken, UserContext


class ServiceAuthenticator:
    """Service-to-service authentication handler."""

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        """Initialize service authenticator.

        Args:
            secret_key: Secret key for JWT signing. If None, uses SERVICE_SECRET_KEY env var
            algorithm: JWT algorithm to use
        """
        self.secret_key = (
            secret_key or os.getenv("SERVICE_SECRET_KEY") or os.getenv("SECRET_KEY")
        )
        self.algorithm = algorithm
        self.token_expiry_hours = int(os.getenv("SERVICE_TOKEN_EXPIRY_HOURS", "24"))

        if not self.secret_key:
            raise ValueError(
                "SERVICE_SECRET_KEY or SECRET_KEY must be provided or set as environment variable"
            )

    def generate_service_token(self, service_name: str) -> ServiceToken:
        """Generate JWT token for service-to-service authentication.

        Args:
            service_name: Name of the service requesting the token

        Returns:
            ServiceToken with JWT and expiration info
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.token_expiry_hours)

        payload = {
            "sub": service_name,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "service": service_name,
            "roles": ["service"],
            "permissions": ["service:internal", "read:all", "write:all"],
            "type": "service",
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return ServiceToken(
            service_name=service_name, token=token, expires_at=expires_at
        )

    def validate_service_token(self, token: str) -> AuthResult:
        """Validate service-to-service authentication token.

        Args:
            token: JWT token string

        Returns:
            AuthResult with validation outcome
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify this is a service token
            if payload.get("type") != "service":
                return AuthResult(
                    success=False,
                    error_message="Invalid service token type",
                    error_code="AUTH_001",
                )

            service_name = payload.get("service")
            if not service_name:
                return AuthResult(
                    success=False,
                    error_message="Service name not found in token",
                    error_code="AUTH_001",
                )

            # Create service user context
            user_context = UserContext(
                user_id=f"service:{service_name}",
                email=f"{service_name}@internal.service",
                roles=payload.get("roles", ["service"]),
                permissions=payload.get("permissions", []),
                service_name=service_name,
            )

            return AuthResult(success=True, user_context=user_context)

        except jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                error_message="Service token has expired",
                error_code="AUTH_003",
            )
        except jwt.JWTError as e:
            return AuthResult(
                success=False,
                error_message=f"Service token validation failed: {str(e)}",
                error_code="AUTH_001",
            )

    def create_service_context(self, service_name: str) -> UserContext:
        """Create a service user context for internal operations.

        Args:
            service_name: Name of the service

        Returns:
            UserContext configured for service operations
        """
        return UserContext(
            user_id=f"service:{service_name}",
            email=f"{service_name}@internal.service",
            roles=["service"],
            permissions=["service:internal", "read:all", "write:all"],
            service_name=service_name,
        )

    def get_service_headers(self, service_name: str) -> Dict[str, str]:
        """Get headers for service-to-service requests.

        Args:
            service_name: Name of the calling service

        Returns:
            Dictionary of headers to include in requests
        """
        service_token = self.generate_service_token(service_name)

        return {
            "Authorization": f"Bearer {service_token.token}",
            "X-Service-Name": service_name,
            "X-Service-Type": "internal",
        }
