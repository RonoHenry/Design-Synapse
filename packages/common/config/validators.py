"""Configuration validation classes and utilities."""

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


@dataclass
class ValidationError:
    """Represents a configuration validation error."""

    field_name: str
    message: str
    context: str = ""
    current_value: Optional[Any] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str] = None
    degraded_features: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.degraded_features is None:
            self.degraded_features = []


class BaseValidator(ABC):
    """Base class for configuration validators."""

    def __init__(self, field_name: str):
        self.field_name = field_name

    @abstractmethod
    def validate(self, value: Any = None) -> ValidationResult:
        """Validate a configuration value."""
        pass


class RequiredConfigValidator(BaseValidator):
    """Validates that required configuration values are present."""

    def __init__(self, required_fields: List[str]):
        super().__init__("required_fields")
        self.required_fields = required_fields

    def validate(self, value: Any = None) -> ValidationResult:
        """Validate that all required environment variables are present."""
        errors = []
        service_name = os.getenv("SERVICE_NAME", "unknown")

        for field in self.required_fields:
            env_value = os.getenv(field)
            if not env_value:
                error = ValidationError(
                    field_name=field,
                    message=f"Required environment variable '{field}' is missing",
                    context=f"service: {service_name}",
                    current_value=None,
                )
                errors.append(error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


class TypeValidator(BaseValidator):
    """Validates configuration value types and allowed values."""

    def __init__(
        self,
        field_name: str,
        expected_type: type,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        allowed_values: Optional[List[Any]] = None,
    ):
        super().__init__(field_name)
        self.expected_type = expected_type
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values

    def validate(self, value: Any) -> ValidationResult:
        """Validate type and constraints."""
        errors = []

        # Type validation
        if not isinstance(value, self.expected_type):
            message = f"Field '{self.field_name}' must be of type {self.expected_type.__name__}"
            if self.min_value is not None and self.max_value is not None:
                message += f" between {self.min_value} and {self.max_value}"

            error = ValidationError(
                field_name=self.field_name, message=message, current_value=value
            )
            errors.append(error)
            return ValidationResult(is_valid=False, errors=errors)

        # Range validation for numeric types
        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                error = ValidationError(
                    field_name=self.field_name,
                    message=f"Value {value} is below minimum {self.min_value}",
                    current_value=value,
                )
                errors.append(error)

            if self.max_value is not None and value > self.max_value:
                error = ValidationError(
                    field_name=self.field_name,
                    message=f"Value {value} is above maximum {self.max_value}",
                    current_value=value,
                )
                errors.append(error)

        # Allowed values validation
        if self.allowed_values and value not in self.allowed_values:
            error = ValidationError(
                field_name=self.field_name,
                message=f"Value '{value}' not in allowed values: {', '.join(map(str, self.allowed_values))}",
                current_value=value,
            )
            errors.append(error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


class RangeValidator(BaseValidator):
    """Validates numeric ranges."""

    def __init__(
        self,
        field_name: str,
        value_type: type,
        min_value: Union[int, float],
        max_value: Union[int, float],
    ):
        super().__init__(field_name)
        self.value_type = value_type
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> ValidationResult:
        """Validate that value is within range."""
        errors = []

        try:
            numeric_value = self.value_type(value)
        except (ValueError, TypeError):
            error = ValidationError(
                field_name=self.field_name,
                message=f"Cannot convert '{value}' to {self.value_type.__name__}",
                current_value=value,
            )
            return ValidationResult(is_valid=False, errors=[error])

        if numeric_value < self.min_value or numeric_value > self.max_value:
            error = ValidationError(
                field_name=self.field_name,
                message=f"Value {numeric_value} must be between {self.min_value} and {self.max_value}",
                current_value=value,
            )
            errors.append(error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


class URLValidator(BaseValidator):
    """Validates URL format."""

    def __init__(self, field_name: str, allowed_schemes: Optional[List[str]] = None):
        super().__init__(field_name)
        self.allowed_schemes = allowed_schemes or [
            "http",
            "https",
            "postgresql",
            "mysql",
        ]

    def validate(self, value: str) -> ValidationResult:
        """Validate URL format."""
        errors = []

        try:
            parsed = urlparse(value)

            if not parsed.scheme:
                error = ValidationError(
                    field_name=self.field_name,
                    message=f"Invalid URL format '{value}'. Example: postgresql://user:pass@host:5432/db",
                    current_value=value,
                )
                errors.append(error)
            elif parsed.scheme not in self.allowed_schemes:
                error = ValidationError(
                    field_name=self.field_name,
                    message=f"Invalid URL format - scheme '{parsed.scheme}' not allowed. Allowed: {', '.join(self.allowed_schemes)}",
                    current_value=value,
                )
                errors.append(error)
            elif not parsed.netloc or not parsed.hostname:
                error = ValidationError(
                    field_name=self.field_name,
                    message=f"Invalid URL format - missing host in '{value}'. Example: postgresql://user:pass@host:5432/db",
                    current_value=value,
                )
                errors.append(error)
        except Exception:
            error = ValidationError(
                field_name=self.field_name,
                message=f"Invalid URL format '{value}'. Example: postgresql://user:pass@host:5432/db",
                current_value=value,
            )
            errors.append(error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


class SecretValidator(BaseValidator):
    """Validates secret key strength."""

    def __init__(
        self, field_name: str, min_length: int = 32, require_complexity: bool = True
    ):
        super().__init__(field_name)
        self.min_length = min_length
        self.require_complexity = require_complexity

    def validate(self, value: str) -> ValidationResult:
        """Validate secret key strength."""
        errors = []

        if len(value) < self.min_length:
            error = ValidationError(
                field_name=self.field_name,
                message=f"Secret key must be at least {self.min_length} characters long",
                current_value="[REDACTED]",
            )
            errors.append(error)

        if self.require_complexity:
            # Check for repetitive patterns
            if len(set(value)) < len(value) * 0.5:  # Less than 50% unique characters
                error = ValidationError(
                    field_name=self.field_name,
                    message="Secret key lacks complexity (too many repeated characters)",
                    current_value="[REDACTED]",
                )
                errors.append(error)

            # Check for simple patterns
            if value.isdigit() or value.isalpha():
                error = ValidationError(
                    field_name=self.field_name,
                    message="Secret key should contain mixed characters (letters, numbers, symbols)",
                    current_value="[REDACTED]",
                )
                errors.append(error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)


class EnvironmentValidator(BaseValidator):
    """Validates configuration based on environment."""

    def __init__(self, environment: str):
        super().__init__("environment")
        self.environment = environment.lower()

    def validate(self, value: Any = None) -> ValidationResult:
        """Default validate method - not used for environment validator."""
        return ValidationResult(is_valid=True, errors=[])

    def validate_database_config(self, db_config: Any) -> ValidationResult:
        """Validate database configuration for specific environment."""
        errors = []
        warnings = []

        if self.environment == "production":
            # Production-specific validations
            if not hasattr(db_config, "password") or not db_config.password:
                error = ValidationError(
                    field_name="password",
                    message="Database password is required in production environment",
                    context="production environment",
                )
                errors.append(error)

            if hasattr(db_config, "host") and db_config.host == "localhost":
                error = ValidationError(
                    field_name="host",
                    message="Database host should not be 'localhost' in production",
                    context="production environment",
                    current_value=db_config.host,
                )
                errors.append(error)

        elif self.environment == "development":
            # Development warnings
            if not hasattr(db_config, "password") or not db_config.password:
                warnings.append(
                    "Database password not set - acceptable for development environment"
                )

        elif self.environment == "testing":
            # Testing-specific validations
            if hasattr(db_config, "name") and not ("test" in db_config.name.lower()):
                error = ValidationError(
                    field_name="name",
                    message="Database name should contain 'test' in testing environment",
                    context="testing environment",
                    current_value=db_config.name,
                )
                errors.append(error)

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_config(self, config: Any) -> ValidationResult:
        """Validate entire configuration for environment."""
        errors = []
        warnings = []

        # Validate database config
        if hasattr(config, "database"):
            db_result = self.validate_database_config(config.database)
            errors.extend(db_result.errors)
            warnings.extend(db_result.warnings)

        # Validate API config for environment
        if hasattr(config, "api") and config.api:
            if self.environment == "production":
                if hasattr(config.api, "debug") and config.api.debug:
                    error = ValidationError(
                        field_name="debug",
                        message="Debug mode should not be enabled in production",
                        context="production environment",
                    )
                    errors.append(error)

                if hasattr(config.api, "secret_key") and config.api.secret_key:
                    # Validate secret strength in production
                    secret_validator = SecretValidator("secret_key")
                    secret_result = secret_validator.validate(config.api.secret_key)
                    if not secret_result.is_valid:
                        errors.extend(secret_result.errors)

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )


class ConfigValidator:
    """Main configuration validator that orchestrates other validators."""

    def __init__(self):
        self.validators = []

    def add_validator(self, validator: BaseValidator):
        """Add a validator to the chain."""
        self.validators.append(validator)

    def validate_database_config(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate database configuration data."""
        errors = []

        # Check required fields
        required_fields = ["host", "port", "name", "user"]
        for field in required_fields:
            if field not in config_data or not config_data[field]:
                error = ValidationError(
                    field_name=field,
                    message=f"Database field '{field}' is required",
                    current_value=config_data.get(field),
                )
                errors.append(error)

        # Validate port if present
        if "port" in config_data:
            try:
                port = int(config_data["port"])
                if port < 1 or port > 65535:
                    error = ValidationError(
                        field_name="port",
                        message="Port must be between 1 and 65535",
                        current_value=config_data["port"],
                    )
                    errors.append(error)
            except (ValueError, TypeError):
                error = ValidationError(
                    field_name="port",
                    message="Port must be a valid integer",
                    current_value=config_data["port"],
                )
                errors.append(error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_with_degradation(self, config: Any) -> ValidationResult:
        """Validate configuration with graceful degradation for optional services."""
        errors = []
        warnings = []
        degraded_features = []

        # Check for optional Redis
        if not hasattr(config, "redis") or not config.redis:
            warnings.append("Redis configuration missing - caching will be disabled")
            degraded_features.append("caching")

        # Check for optional vector database
        if not hasattr(config, "vector") or not config.vector:
            warnings.append(
                "Vector database configuration missing - search features will be limited"
            )
            degraded_features.append("vector_search")

        return ValidationResult(
            is_valid=True,  # Valid even with degraded features
            errors=errors,
            warnings=warnings,
            degraded_features=degraded_features,
        )
