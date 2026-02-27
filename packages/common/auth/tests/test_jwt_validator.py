"""Tests for JWT token validation with various scenarios."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from ..models import AuthResult, TokenPayload
from ..validator import JWTValidator


class TestJWTValidator:
    """Test JWT token validation scenarios."""

    @pytest.fixture
    def secret_key(self):
        """Test secret key."""
        return "test-secret-key-for-jwt-validation"

    @pytest.fixture
    def validator(self, secret_key):
        """JWT validator instance."""
        return JWTValidator(secret_key=secret_key)

    @pytest.fixture
    def valid_token_payload(self):
        """Valid token payload."""
        return {
            "sub": "user123",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "roles": ["designer", "viewer"],
            "permissions": ["read:projects", "write:designs"],
        }

    @pytest.fixture
    def valid_token(self, secret_key, valid_token_payload):
        """Valid JWT token."""
        return jwt.encode(valid_token_payload, secret_key, algorithm="HS256")

    def test_decode_valid_token(self, validator, valid_token, valid_token_payload):
        """Test decoding a valid JWT token."""
        payload = validator.decode_token(valid_token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == valid_token_payload["sub"]
        assert payload.roles == valid_token_payload["roles"]
        assert payload.permissions == valid_token_payload["permissions"]

    def test_decode_token_with_service_info(self, validator, secret_key):
        """Test decoding token with service information."""
        payload = {
            "sub": "service-user",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "roles": ["service"],
            "service": "design-service",
            "permissions": ["service:internal"],
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        decoded = validator.decode_token(token)
        assert decoded.service == "design-service"
        assert "service" in decoded.roles

    def test_validate_signature_valid_token(self, validator, valid_token):
        """Test signature validation with valid token."""
        assert validator.validate_signature(valid_token) is True

    def test_validate_signature_invalid_token(self, validator):
        """Test signature validation with invalid token."""
        # Token signed with different key
        wrong_key = "wrong-secret-key"
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        invalid_token = jwt.encode(payload, wrong_key, algorithm="HS256")

        assert validator.validate_signature(invalid_token) is False

    def test_is_token_expired_valid_token(self, validator, valid_token):
        """Test expiration check with valid token."""
        assert validator.is_token_expired(valid_token) is False

    def test_is_token_expired_expired_token(self, validator, secret_key):
        """Test expiration check with expired token."""
        expired_payload = {
            "sub": "user123",
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int(
                (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
            ),  # Expired 1 hour ago
            "roles": ["viewer"],
        }
        expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")

        assert validator.is_token_expired(expired_token) is True

    def test_is_token_expired_no_exp_claim(self, validator, secret_key):
        """Test expiration check with token missing exp claim."""
        payload_no_exp = {
            "sub": "user123",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "roles": ["viewer"],
        }
        token_no_exp = jwt.encode(payload_no_exp, secret_key, algorithm="HS256")

        assert validator.is_token_expired(token_no_exp) is True

    def test_validate_token_success(self, validator, valid_token):
        """Test successful token validation."""
        result = validator.validate_token(valid_token)

        assert isinstance(result, AuthResult)
        assert result.success is True
        assert result.user_context is not None
        assert result.user_context.user_id == "user123"
        assert "designer" in result.user_context.roles
        assert "read:projects" in result.user_context.permissions

    def test_validate_token_with_bearer_prefix(self, validator, valid_token):
        """Test token validation with Bearer prefix."""
        bearer_token = f"Bearer {valid_token}"
        result = validator.validate_token(bearer_token)

        assert result.success is True
        assert result.user_context.user_id == "user123"

    def test_validate_token_expired(self, validator, secret_key):
        """Test validation of expired token."""
        expired_payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
            "roles": ["viewer"],
        }
        expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")

        result = validator.validate_token(expired_token)

        assert result.success is False
        assert result.error_code == "AUTH_003"  # Token expired
        assert "expired" in result.error_message.lower()

    def test_validate_token_invalid_signature(self, validator):
        """Test validation of token with invalid signature."""
        wrong_key = "wrong-secret-key"
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "roles": ["viewer"],
        }
        invalid_token = jwt.encode(payload, wrong_key, algorithm="HS256")

        result = validator.validate_token(invalid_token)

        assert result.success is False
        assert result.error_code == "AUTH_004"  # Invalid signature
        assert "signature" in result.error_message.lower()

    def test_validate_token_malformed(self, validator):
        """Test validation of malformed token."""
        malformed_token = "not.a.valid.jwt.token"

        result = validator.validate_token(malformed_token)

        assert result.success is False
        assert result.error_code == "AUTH_001"  # Authentication failed

    def test_validate_token_empty_roles_permissions(self, validator, secret_key):
        """Test token validation with empty roles and permissions."""
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        result = validator.validate_token(token)

        assert result.success is True
        assert result.user_context.roles == []
        assert result.user_context.permissions == []

    def test_validator_initialization_no_secret(self, monkeypatch):
        """Test validator initialization without secret key."""
        # Remove environment variables
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("SERVICE_SECRET_KEY", raising=False)

        with pytest.raises(ValueError, match="SECRET_KEY must be provided"):
            JWTValidator(secret_key=None)

    def test_validator_initialization_with_secret(self):
        """Test validator initialization with secret key."""
        validator = JWTValidator(secret_key="test-key")
        assert validator.secret_key == "test-key"
        assert validator.algorithm == "HS256"
