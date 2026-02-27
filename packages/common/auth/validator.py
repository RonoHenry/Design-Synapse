"""JWT token validation utilities."""

import os
from datetime import datetime, timezone
from typing import Optional

from jose import JWTError, jwt

from .models import AuthResult, TokenPayload, UserContext


class JWTValidator:
    """JWT token validator with proper error handling."""

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        """Initialize JWT validator.

        Args:
            secret_key: Secret key for JWT validation. If None, uses SECRET_KEY env var
            algorithm: JWT algorithm to use
        """
        self.secret_key = secret_key or os.getenv("SECRET_KEY")
        self.algorithm = algorithm

        if not self.secret_key:
            raise ValueError(
                "SECRET_KEY must be provided or set as environment variable"
            )

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload with decoded token data

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            return TokenPayload(
                sub=payload.get("sub"),
                iat=payload.get("iat"),
                exp=payload.get("exp"),
                roles=payload.get("roles", []),
                service=payload.get("service"),
                permissions=payload.get("permissions", []),
            )
        except JWTError as e:
            raise JWTError(f"Token validation failed: {str(e)}")

    def validate_signature(self, token: str) -> bool:
        """Validate JWT token signature.

        Args:
            token: JWT token string

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},  # Only check signature
            )
            return True
        except JWTError:
            return False

    def is_token_expired(self, token: str) -> bool:
        """Check if JWT token is expired.

        Args:
            token: JWT token string

        Returns:
            True if token is expired, False otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": False},
            )

            exp = payload.get("exp")
            if not exp:
                return True

            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            return datetime.now(timezone.utc) > exp_datetime

        except JWTError:
            return True

    def validate_token(self, token: str) -> AuthResult:
        """Validate JWT token and return authentication result.

        Args:
            token: JWT token string

        Returns:
            AuthResult with validation outcome
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            payload = self.decode_token(token)

            # Create user context
            user_context = UserContext(
                user_id=payload.sub,
                email=payload.sub,  # Assuming sub is email for now
                roles=payload.roles,
                permissions=payload.permissions or [],
                service_name=payload.service,
            )

            return AuthResult(success=True, user_context=user_context)

        except JWTError as e:
            error_msg = str(e)
            error_code = "AUTH_001"  # Authentication failed

            if "expired" in error_msg.lower():
                error_code = "AUTH_003"  # Token expired
            elif "signature" in error_msg.lower():
                error_code = "AUTH_004"  # Invalid signature

            return AuthResult(
                success=False, error_message=error_msg, error_code=error_code
            )
