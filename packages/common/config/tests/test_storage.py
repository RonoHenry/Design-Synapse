"""Unit tests for Storage configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def disable_env_file(monkeypatch):
    """Disable .env file loading for all tests in this module."""
    monkeypatch.setenv("PYDANTIC_SETTINGS_IGNORE_ENV_FILE", "1")


@pytest.fixture
def mock_storage_env_vars(monkeypatch):
    """Set up mock environment variables for storage testing."""
    # Clear existing storage-related environment variables
    storage_env_keys = [k for k in os.environ.keys() if k.startswith("STORAGE_")]
    for key in storage_env_keys:
        monkeypatch.delenv(key, raising=False)
    
    env_vars = {
        # S3 settings
        "STORAGE_S3_BUCKET": "test-design-bucket",
        "STORAGE_S3_REGION": "us-west-2",
        "STORAGE_S3_ACCESS_KEY_ID": "test_access_key",
        "STORAGE_S3_SECRET_ACCESS_KEY": "test_secret_key",
        # CDN settings
        "STORAGE_CDN_URL": "https://cdn.example.com",
        "STORAGE_CDN_ENABLED": "true",
        # Upload settings
        "STORAGE_MAX_FILE_SIZE_MB": "50",
        "STORAGE_ALLOWED_EXTENSIONS": "jpg,jpeg,png,gif,pdf,dwg,step,ifc",
        # Lifecycle settings
        "STORAGE_LIFECYCLE_ENABLED": "true",
        "STORAGE_LIFECYCLE_TRANSITION_DAYS": "30",
        "STORAGE_LIFECYCLE_EXPIRATION_DAYS": "365",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def test_storage_config_initialization(mock_storage_env_vars):
    """Test that StorageConfig initializes correctly with valid environment variables."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()

    assert config.s3_bucket == "test-design-bucket"
    assert config.s3_region == "us-west-2"
    assert config.s3_access_key_id == "test_access_key"
    assert config.s3_secret_access_key == "test_secret_key"
    assert config.cdn_url == "https://cdn.example.com"
    assert config.cdn_enabled is True
    assert config.max_file_size_mb == 50
    assert config.allowed_extensions == ["jpg", "jpeg", "png", "gif", "pdf", "dwg", "step", "ifc"]


def test_storage_config_s3_client_kwargs(mock_storage_env_vars):
    """Test S3 client configuration generation."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()
    s3_kwargs = config.get_s3_client_kwargs()

    assert s3_kwargs["aws_access_key_id"] == "test_access_key"
    assert s3_kwargs["aws_secret_access_key"] == "test_secret_key"
    assert s3_kwargs["region_name"] == "us-west-2"
    assert "config" in s3_kwargs
    assert s3_kwargs["config"].retries["max_attempts"] == 3


def test_storage_config_upload_settings(mock_storage_env_vars):
    """Test upload settings configuration."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()
    upload_settings = config.get_upload_settings()

    assert upload_settings["max_file_size_bytes"] == 50 * 1024 * 1024  # 50MB in bytes
    assert upload_settings["allowed_extensions"] == ["jpg", "jpeg", "png", "gif", "pdf", "dwg", "step", "ifc"]
    assert upload_settings["enable_compression"] is True
    assert upload_settings["compression_quality"] == 85


def test_storage_config_lifecycle_settings(mock_storage_env_vars):
    """Test lifecycle policy settings."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()
    lifecycle_settings = config.get_lifecycle_settings()

    assert lifecycle_settings["enabled"] is True
    assert lifecycle_settings["transition_to_ia_days"] == 30
    assert lifecycle_settings["expiration_days"] == 365
    assert lifecycle_settings["abort_incomplete_multipart_days"] == 7


def test_storage_config_cdn_url_generation(mock_storage_env_vars):
    """Test CDN URL generation for files."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()

    # Test with CDN enabled
    cdn_url = config.get_file_url("designs/123/floor_plan.jpg")
    assert cdn_url == "https://cdn.example.com/designs/123/floor_plan.jpg"

    # Test with CDN disabled
    config.cdn_enabled = False
    s3_url = config.get_file_url("designs/123/floor_plan.jpg")
    assert s3_url == f"https://{config.s3_bucket}.s3.{config.s3_region}.amazonaws.com/designs/123/floor_plan.jpg"


def test_storage_config_file_extension_validation(mock_storage_env_vars):
    """Test file extension validation."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()

    # Valid extensions
    assert config.is_allowed_extension("test.jpg") is True
    assert config.is_allowed_extension("design.pdf") is True
    assert config.is_allowed_extension("model.step") is True

    # Invalid extensions
    assert config.is_allowed_extension("malware.exe") is False
    assert config.is_allowed_extension("script.js") is False
    assert config.is_allowed_extension("file.txt") is False


def test_storage_config_file_size_validation(mock_storage_env_vars):
    """Test file size validation."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()

    # Valid file sizes
    assert config.is_valid_file_size(1024) is True  # 1KB
    assert config.is_valid_file_size(25 * 1024 * 1024) is True  # 25MB

    # Invalid file sizes
    assert config.is_valid_file_size(100 * 1024 * 1024) is False  # 100MB (exceeds 50MB limit)
    assert config.is_valid_file_size(0) is False  # Empty file


def test_storage_config_missing_required_vars():
    """Test that config validation fails with missing required variables."""
    from packages.common.config.storage import StorageConfig

    # Test missing S3 bucket
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            StorageConfig()
        assert "s3_bucket" in str(exc_info.value)


def test_storage_config_invalid_region():
    """Test validation of invalid AWS region."""
    from packages.common.config.storage import StorageConfig

    with patch.dict(os.environ, {
        "STORAGE_S3_BUCKET": "test-bucket",
        "STORAGE_S3_REGION": "invalid-region",
        "STORAGE_S3_ACCESS_KEY_ID": "test_key",
        "STORAGE_S3_SECRET_ACCESS_KEY": "test_secret",
    }):
        with pytest.raises(ValidationError) as exc_info:
            StorageConfig()
        assert "s3_region" in str(exc_info.value)


def test_storage_config_invalid_file_size():
    """Test validation of invalid max file size."""
    from packages.common.config.storage import StorageConfig

    with patch.dict(os.environ, {
        "STORAGE_S3_BUCKET": "test-bucket",
        "STORAGE_S3_REGION": "us-west-2",
        "STORAGE_S3_ACCESS_KEY_ID": "test_key",
        "STORAGE_S3_SECRET_ACCESS_KEY": "test_secret",
        "STORAGE_MAX_FILE_SIZE_MB": "0",  # Invalid: zero size
    }):
        with pytest.raises(ValidationError) as exc_info:
            StorageConfig()
        assert "max_file_size_mb" in str(exc_info.value)


def test_storage_config_invalid_lifecycle_days():
    """Test validation of invalid lifecycle days."""
    from packages.common.config.storage import StorageConfig

    with patch.dict(os.environ, {
        "STORAGE_S3_BUCKET": "test-bucket",
        "STORAGE_S3_REGION": "us-west-2",
        "STORAGE_S3_ACCESS_KEY_ID": "test_key",
        "STORAGE_S3_SECRET_ACCESS_KEY": "test_secret",
        "STORAGE_LIFECYCLE_TRANSITION_DAYS": "-1",  # Invalid: negative days
    }):
        with pytest.raises(ValidationError) as exc_info:
            StorageConfig()
        assert "lifecycle_transition_days" in str(exc_info.value)


def test_storage_config_environment_variable_validation(mock_storage_env_vars):
    """Test that all required environment variables are validated."""
    from packages.common.config.storage import StorageConfig

    config = StorageConfig()
    
    # Test validation method
    config.validate_required_settings()  # Should not raise any exception
    
    # Test with missing credentials
    config.s3_access_key_id = ""
    with pytest.raises(ValueError) as exc_info:
        config.validate_required_settings()
    assert "S3 credentials" in str(exc_info.value)


def test_storage_config_default_values():
    """Test default values when optional environment variables are not set."""
    from packages.common.config.storage import StorageConfig

    with patch.dict(os.environ, {
        "STORAGE_S3_BUCKET": "test-bucket",
        "STORAGE_S3_REGION": "us-west-2",
        "STORAGE_S3_ACCESS_KEY_ID": "test_key",
        "STORAGE_S3_SECRET_ACCESS_KEY": "test_secret",
        # CDN and lifecycle settings not provided - should use defaults
    }, clear=True):
        config = StorageConfig()
        
        assert config.cdn_enabled is False  # Default
        assert config.max_file_size_mb == 100  # Default
        assert config.lifecycle_enabled is False  # Default
        assert config.lifecycle_transition_days == 30  # Default
        assert config.lifecycle_expiration_days == 365  # Default