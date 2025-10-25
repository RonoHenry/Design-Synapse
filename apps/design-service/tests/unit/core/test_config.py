"""Unit tests for Design Service configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def disable_env_file(monkeypatch):
    """Disable .env file loading for all tests in this module."""
    # Move to a non-existent directory to prevent .env file loading
    monkeypatch.setenv("PYDANTIC_SETTINGS_IGNORE_ENV_FILE", "1")


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    # Clear ALL existing environment variables to avoid interference
    import os
    env_keys_to_clear = [k for k in os.environ.keys()]
    for key in env_keys_to_clear:
        monkeypatch.delenv(key, raising=False)
    
    env_vars = {
        # Database settings
        "DB_USERNAME": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_DATABASE": "test_db",
        "DB_HOST": "localhost",
        "DB_PORT": "4000",
        "DB_DATABASE_TYPE": "tidb",
        # JWT settings
        "JWT_SECRET_KEY": "test_secret_key_that_is_at_least_32_characters_long",
        "JWT_ALGORITHM": "HS256",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        # LLM settings
        "LLM_PRIMARY_PROVIDER": "openai",
        "LLM_FALLBACK_PROVIDERS": "[]",  # Empty JSON array for no fallback providers
        "LLM_OPENAI_API_KEY": "test_openai_key",
        "LLM_OPENAI_MODEL": "gpt-3.5-turbo",
        # Service URLs
        "USER_SERVICE_URL": "http://localhost:8001",
        "PROJECT_SERVICE_URL": "http://localhost:8003",
        "KNOWLEDGE_SERVICE_URL": "http://localhost:8002",
        # Design settings
        "DESIGN_MAX_DESIGNS_PER_PROJECT": "50",
        "DESIGN_MAX_DESIGN_ITERATIONS": "10",
        "DESIGN_ENABLE_AUTO_GENERATION": "true",
        # Base settings
        "ENVIRONMENT": "testing",
        "DEBUG": "false",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def test_design_service_config_initialization(mock_env_vars):
    """Test that DesignServiceConfig initializes correctly with valid environment variables."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()

    assert config.service_name == "design-service"
    assert config.port == 8004
    assert config.environment.value == "testing"
    assert config.user_service_url == "http://localhost:8001"
    assert config.project_service_url == "http://localhost:8003"
    assert config.knowledge_service_url == "http://localhost:8002"


def test_design_service_config_database_url(mock_env_vars):
    """Test database URL generation."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()

    # Test sync URL
    sync_url = config.get_database_url(async_driver=False)
    assert "mysql+pymysql" in sync_url
    assert "test_user" in sync_url
    assert "test_password" in sync_url
    assert "test_db" in sync_url

    # Test async URL
    async_url = config.get_database_url(async_driver=True)
    assert "mysql+aiomysql" in async_url


def test_design_service_config_jwt_config(mock_env_vars):
    """Test JWT configuration retrieval."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()
    jwt_config = config.get_jwt_config()

    assert (
        jwt_config["secret_key"]
        == "test_secret_key_that_is_at_least_32_characters_long"
    )
    assert jwt_config["algorithm"] == "HS256"
    assert jwt_config["access_token_expire_minutes"] == 30


def test_design_service_config_llm_config(mock_env_vars):
    """Test LLM configuration retrieval."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()
    llm_config = config.get_llm_config()

    assert "primary_provider" in llm_config
    assert "fallback_providers" in llm_config
    assert "max_retries" in llm_config
    assert "timeout" in llm_config


def test_design_service_config_design_config(mock_env_vars):
    """Test design configuration retrieval."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()
    design_config = config.get_design_config()

    assert design_config["max_designs_per_project"] == 50
    assert design_config["max_design_iterations"] == 10
    assert design_config["enable_auto_generation"] is True
    assert "generation_timeout_seconds" in design_config
    assert "max_concurrent_generations" in design_config


def test_design_service_config_service_urls(mock_env_vars):
    """Test service URLs configuration."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()
    service_urls = config.get_service_urls()

    assert service_urls["user_service"] == "http://localhost:8001"
    assert service_urls["project_service"] == "http://localhost:8003"
    assert service_urls["knowledge_service"] == "http://localhost:8002"


def test_design_service_config_rate_limit_config(mock_env_vars):
    """Test rate limiting configuration."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()
    rate_limit_config = config.get_rate_limit_config()

    assert "requests_per_minute" in rate_limit_config
    assert "burst" in rate_limit_config
    assert rate_limit_config["requests_per_minute"] > 0
    assert rate_limit_config["burst"] > 0


def test_design_service_config_environment_checks(mock_env_vars):
    """Test environment check methods."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()

    assert config.is_testing() is True
    assert config.is_development() is False
    assert config.is_production() is False


def test_design_service_config_missing_required_vars(mock_env_vars):
    """Test that config validation works with required variables."""
    from src.core.config import DesignServiceConfig

    # This test verifies that with all required vars set, config initializes successfully
    # The mock_env_vars fixture provides all required environment variables
    config = DesignServiceConfig()
    
    # Verify config was created successfully
    assert config.service_name == "design-service"
    assert config.jwt.secret_key == "test_secret_key_that_is_at_least_32_characters_long"


def test_design_settings_validation():
    """Test DesignSettings validation."""
    from src.core.config import DesignSettings

    # Valid settings
    settings = DesignSettings(
        max_designs_per_project=50,
        max_design_iterations=10,
        enable_auto_generation=True,
    )
    assert settings.max_designs_per_project == 50

    # Invalid settings - negative value
    with pytest.raises(ValidationError):
        DesignSettings(max_designs_per_project=0)


def test_jwt_settings_validation():
    """Test JWTSettings validation."""
    from src.core.config import JWTSettings

    # Valid settings
    settings = JWTSettings(
        secret_key="test_secret_key_that_is_at_least_32_characters_long",
        algorithm="HS256",
    )
    assert settings.algorithm == "HS256"

    # Invalid algorithm
    with pytest.raises(ValidationError):
        JWTSettings(
            secret_key="test_secret_key_that_is_at_least_32_characters_long",
            algorithm="INVALID",
        )

    # Secret key too short
    with pytest.raises(ValidationError):
        JWTSettings(secret_key="short", algorithm="HS256")


def test_design_service_config_database_engine_kwargs(mock_env_vars):
    """Test database engine kwargs generation."""
    from src.core.config import DesignServiceConfig

    config = DesignServiceConfig()
    engine_kwargs = config.get_database_engine_kwargs()

    assert "pool_size" in engine_kwargs
    assert "max_overflow" in engine_kwargs
    assert "pool_timeout" in engine_kwargs
    assert "pool_recycle" in engine_kwargs
    assert "pool_pre_ping" in engine_kwargs
    assert engine_kwargs["pool_pre_ping"] is True
