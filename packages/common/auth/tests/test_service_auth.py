"""Tests for service-to-service authentication flows."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from ..models import AuthResult, ServiceToken, UserContext
from ..service_auth import ServiceAuthenticator


class TestServiceAuthenticator:
    """Test service-to-service authentication."""

    @pytest.fixture
    def secret_key(self):
        """Test secret key for service authentication."""
        return "test-service-secret-key"

    @pytest.fixture
    def service_auth(self, secret_key):
        """Service authenticator instance."""
        return ServiceAuthenticator(secret_key=secret_key)

    def test_generate_service_token(self, service_auth):
        """Test generating service token."""
        service_name = "test-service"
        service_token = service_auth.generate_service_token(service_name)

        assert isinstance(service_token, ServiceToken)
        assert service_token.service_name == service_name
        assert service_token.token is not None
        assert service_token.expires_at > datetime.now(timezone.utc)

    def test_generate_service_token_payload(self, service_auth, secret_key):
        """Test service token contains correct payload."""
        service_name = "design-service"
        service_token = service_auth.generate_service_token(service_name)

        # Decode token to verify payload
        payload = jwt.decode(service_token.token, secret_key, algorithms=["HS256"])

        assert payload["sub"] == service_name
        assert payload["service"] == service_name
        assert payload["type"] == "service"
        assert "service" in payload["roles"]
        assert "service:internal" in payload["permissions"]
        assert "read:all" in payload["permissions"]
        assert "write:all" in payload["permissions"]

    def test_validate_service_token_success(self, service_auth):
        """Test successful service token validation."""
        service_name = "user-service"
        service_token = service_auth.generate_service_token(service_name)

        result = service_auth.validate_service_token(service_token.token)

        assert isinstance(result, AuthResult)
        assert result.success is True
        assert result.user_context is not None
        assert result.user_context.user_id == f"service:{service_name}"
        assert result.user_context.service_name == service_name
        assert "service" in result.user_context.roles
        assert "service:internal" in result.user_context.permissions

    def test_validate_service_token_with_bearer_prefix(self, service_auth):
        """Test service token validation with Bearer prefix."""
        service_token = service_auth.generate_service_token("api-gateway")
        bearer_token = f"Bearer {service_token.token}"

        result = service_auth.validate_service_token(bearer_token)

        assert result.success is True
        assert result.user_context.service_name == "api-gateway"

    def test_validate_service_token_expired(self, service_auth, secret_key):
        """Test validation of expired service token."""
        # Create expired token
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "expired-service",
            "iat": int((past_time - timedelta(hours=1)).timestamp()),
            "exp": int(past_time.timestamp()),  # Expired
            "service": "expired-service",
            "type": "service",
            "roles": ["service"],
            "permissions": ["service:internal"],
        }
        expired_token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = service_auth.validate_service_token(expired_token)

        assert result.success is False
        assert result.error_code == "AUTH_003"
        assert "expired" in result.error_message.lower()

    def test_validate_service_token_invalid_signature(self, service_auth):
        """Test validation of service token with invalid signature."""
        wrong_key = "wrong-service-secret"
        payload = {
            "sub": "invalid-service",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "service": "invalid-service",
            "type": "service",
            "roles": ["service"],
        }
        invalid_token = jwt.encode(payload, wrong_key, algorithm="HS256")

        result = service_auth.validate_service_token(invalid_token)

        assert result.success is False
        assert result.error_code == "AUTH_001"
        assert "validation failed" in result.error_message.lower()

    def test_validate_service_token_wrong_type(self, service_auth, secret_key):
        """Test validation of token with wrong type."""
        # Create user token instead of service token
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "type": "user",  # Wrong type
            "roles": ["designer"],
        }
        user_token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = service_auth.validate_service_token(user_token)

        assert result.success is False
        assert result.error_code == "AUTH_001"
        assert "Invalid service token type" in result.error_message

    def test_validate_service_token_missing_service_name(
        self, service_auth, secret_key
    ):
        """Test validation of service token missing service name."""
        payload = {
            "sub": "service-without-name",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "type": "service",
            "roles": ["service"]
            # Missing "service" field
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = service_auth.validate_service_token(token)

        assert result.success is False
        assert result.error_code == "AUTH_001"
        assert "Service name not found" in result.error_message

    def test_validate_service_token_malformed(self, service_auth):
        """Test validation of malformed service token."""
        malformed_token = "not.a.valid.jwt.token"

        result = service_auth.validate_service_token(malformed_token)

        assert result.success is False
        assert result.error_code == "AUTH_001"

    def test_create_service_context(self, service_auth):
        """Test creating service user context."""
        service_name = "knowledge-service"
        context = service_auth.create_service_context(service_name)

        assert isinstance(context, UserContext)
        assert context.user_id == f"service:{service_name}"
        assert context.email == f"{service_name}@internal.service"
        assert context.service_name == service_name
        assert "service" in context.roles
        assert "service:internal" in context.permissions
        assert "read:all" in context.permissions
        assert "write:all" in context.permissions

    def test_get_service_headers(self, service_auth):
        """Test getting headers for service-to-service requests."""
        service_name = "project-service"
        headers = service_auth.get_service_headers(service_name)

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["X-Service-Name"] == service_name
        assert headers["X-Service-Type"] == "internal"

        # Verify the token in the Authorization header is valid
        token = headers["Authorization"].replace("Bearer ", "")
        result = service_auth.validate_service_token(token)
        assert result.success is True
        assert result.user_context.service_name == service_name

    def test_service_authenticator_initialization_no_secret(self, monkeypatch):
        """Test service authenticator initialization without secret key."""
        # Remove environment variables
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("SERVICE_SECRET_KEY", raising=False)

        with pytest.raises(
            ValueError, match="SERVICE_SECRET_KEY or SECRET_KEY must be provided"
        ):
            ServiceAuthenticator(secret_key=None)

    def test_service_authenticator_initialization_with_secret(self):
        """Test service authenticator initialization with secret key."""
        secret = "test-secret"
        auth = ServiceAuthenticator(secret_key=secret)
        assert auth.secret_key == secret
        assert auth.algorithm == "HS256"
        assert auth.token_expiry_hours == 24  # Default

    def test_service_token_expiry_configuration(self, secret_key, monkeypatch):
        """Test service token expiry configuration."""
        # Set custom expiry hours
        monkeypatch.setenv("SERVICE_TOKEN_EXPIRY_HOURS", "12")

        auth = ServiceAuthenticator(secret_key=secret_key)
        assert auth.token_expiry_hours == 12

        # Generate token and check expiry
        service_token = auth.generate_service_token("test-service")
        expected_expiry = datetime.now(timezone.utc) + timedelta(hours=12)

        # Allow 1 minute tolerance for test execution time
        assert abs((service_token.expires_at - expected_expiry).total_seconds()) < 60

    def test_multiple_service_tokens(self, service_auth):
        """Test generating tokens for multiple services."""
        services = ["user-service", "project-service", "design-service"]
        tokens = {}

        for service in services:
            token = service_auth.generate_service_token(service)
            tokens[service] = token

            # Validate each token
            result = service_auth.validate_service_token(token.token)
            assert result.success is True
            assert result.user_context.service_name == service

        # Ensure tokens are different
        token_strings = [token.token for token in tokens.values()]
        assert len(set(token_strings)) == len(services)  # All unique

    def test_service_context_email_format(self, service_auth):
        """Test service context email format."""
        services = ["user-service", "api-gateway", "design-service"]

        for service in services:
            context = service_auth.create_service_context(service)
            expected_email = f"{service}@internal.service"
            assert context.email == expected_email
