"""Data models for authentication middleware."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class UserContext:
    """User context extracted from JWT token."""

    user_id: str
    email: str
    roles: List[str]
    permissions: List[str]
    service_name: Optional[str] = None  # For service-to-service auth


@dataclass
class TokenPayload:
    """JWT token payload structure."""

    sub: str  # Subject (user_id or email)
    iat: int  # Issued at
    exp: int  # Expiration
    roles: List[str]
    service: Optional[str] = None
    permissions: Optional[List[str]] = None


@dataclass
class ServiceToken:
    """Service-to-service authentication token."""

    service_name: str
    token: str
    expires_at: datetime


@dataclass
class AuthResult:
    """Result of authentication validation."""

    success: bool
    user_context: Optional[UserContext] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class PermissionRule:
    """Permission rule for endpoint access."""

    endpoint_pattern: str
    required_roles: List[str]
    required_permissions: List[str]
    allow_service_auth: bool = True
    description: Optional[str] = None
