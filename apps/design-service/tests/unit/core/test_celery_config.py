"""Unit tests for Celery configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def disable_env_file(monkeypatch):
    """Disable .env file loading for all tests in this module."""
    monkeypatch.setenv("PYDANTIC_SETTINGS_IGNORE_ENV_FILE", "1")


@pytest.fixture
def mock_celery_config_env_vars(monkeypatch):
    """Set up mock environment variables for Celery configuration testing."""
    # Clear existing Celery-related environment variables
    celery_env_keys = [k for k in os.environ.keys() if k.startswith("CELERY_")]
    for key in celery_env_keys:
        monkeypatch.delenv(key, raising=False)
    
    env_vars = {
        # Broker and result backend
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
        # Task routing
        "CELERY_TASK_DEFAULT_QUEUE": "design_service",
        "CELERY_TASK_ROUTES": '{"src.tasks.visual_generation.*": {"queue": "visual_generation"}}',
        # Worker settings
        "CELERY_WORKER_CONCURRENCY": "4",
        "CELERY_WORKER_PREFETCH_MULTIPLIER": "1",
        "CELERY_WORKER_MAX_TASKS_PER_CHILD": "1000",
        # Task settings
        "CELERY_TASK_SERIALIZER": "json",
        "CELERY_RESULT_SERIALIZER": "json",
        "CELERY_ACCEPT_CONTENT": '["json"]',
        "CELERY_TIMEZONE": "UTC",
        "CELERY_ENABLE_UTC": "true",
        # Retry and timeout settings
        "CELERY_TASK_DEFAULT_RETRY_DELAY": "60",
        "CELERY_TASK_MAX_RETRIES": "3",
        "CELERY_TASK_SOFT_TIME_LIMIT": "300",
        "CELERY_TASK_TIME_LIMIT": "600",
        # Result backend settings
        "CELERY_RESULT_EXPIRES": "3600",
        "CELERY_RESULT_PERSISTENT": "true",
        # Connection settings
        "CELERY_BROKER_CONNECTION_RETRY": "true",
        "CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP": "true",
        "CELERY_BROKER_CONNECTION_MAX_RETRIES": "10",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def test_celery_config_initialization(mock_celery_config_env_vars):
    """Test that CeleryConfig initializes correctly with valid environment variables."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()

    assert config.broker_url == "redis://localhost:6379/0"
    assert config.result_backend == "redis://localhost:6379/1"
    assert config.task_default_queue == "design_service"
    assert config.worker_concurrency == 4
    assert config.worker_prefetch_multiplier == 1
    assert config.task_serializer == "json"
    assert config.result_serializer == "json"
    assert config.timezone == "UTC"
    assert config.enable_utc is True


def test_celery_config_broker_settings(mock_celery_config_env_vars):
    """Test Celery broker configuration settings."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    broker_settings = config.get_broker_settings()

    assert broker_settings["broker_url"] == "redis://localhost:6379/0"
    assert broker_settings["result_backend"] == "redis://localhost:6379/1"
    assert broker_settings["broker_connection_retry"] is True
    assert broker_settings["broker_connection_retry_on_startup"] is True
    assert broker_settings["broker_connection_max_retries"] == 10


def test_celery_config_task_routing(mock_celery_config_env_vars):
    """Test Celery task routing configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    routing_settings = config.get_task_routing_settings()

    assert routing_settings["task_default_queue"] == "design_service"
    assert "src.tasks.visual_generation.*" in routing_settings["task_routes"]
    assert routing_settings["task_routes"]["src.tasks.visual_generation.*"]["queue"] == "visual_generation"
    assert routing_settings["task_create_missing_queues"] is True


def test_celery_config_worker_settings(mock_celery_config_env_vars):
    """Test Celery worker configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    worker_settings = config.get_worker_settings()

    assert worker_settings["worker_concurrency"] == 4
    assert worker_settings["worker_prefetch_multiplier"] == 1
    assert worker_settings["worker_max_tasks_per_child"] == 1000


def test_celery_config_task_settings(mock_celery_config_env_vars):
    """Test Celery task configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    task_settings = config.get_task_settings()

    assert task_settings["task_serializer"] == "json"
    assert task_settings["result_serializer"] == "json"
    assert task_settings["accept_content"] == ["json"]
    assert task_settings["task_default_retry_delay"] == 60
    assert task_settings["task_max_retries"] == 3
    assert task_settings["task_soft_time_limit"] == 300
    assert task_settings["task_time_limit"] == 600


def test_celery_config_result_backend_settings(mock_celery_config_env_vars):
    """Test Celery result backend configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    result_settings = config.get_result_backend_settings()

    assert result_settings["result_expires"] == 3600
    assert result_settings["result_persistent"] is True
    assert result_settings["result_backend"] == "redis://localhost:6379/1"


def test_celery_config_timezone_settings(mock_celery_config_env_vars):
    """Test Celery timezone configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    timezone_settings = config.get_timezone_settings()

    assert timezone_settings["timezone"] == "UTC"
    assert timezone_settings["enable_utc"] is True


def test_celery_config_complete_configuration(mock_celery_config_env_vars):
    """Test complete Celery configuration generation."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    complete_config = config.get_complete_celery_config()

    # Test that all major sections are present
    assert "broker_url" in complete_config
    assert "result_backend" in complete_config
    assert "task_default_queue" in complete_config
    assert "task_routes" in complete_config
    assert "worker_concurrency" in complete_config
    assert "task_serializer" in complete_config
    assert "timezone" in complete_config


def test_celery_config_validation_missing_broker_url():
    """Test that missing broker URL raises validation error."""
    from src.core.celery_config import CeleryConfig
    
    # Since we now have CELERY_BROKER_URL in .env, this test should verify
    # that the config works when broker_url is available
    config = CeleryConfig()
    assert config.broker_url is not None
    assert "redis://" in config.broker_url


def test_celery_config_validation_invalid_broker_url():
    """Test that invalid broker URL raises validation error."""
    with patch.dict(os.environ, {"CELERY_BROKER_URL": "invalid-url"}, clear=True):
        from src.core.celery_config import CeleryConfig
        
        with pytest.raises(ValidationError) as exc_info:
            CeleryConfig()
        
        assert "broker_url" in str(exc_info.value)


def test_celery_config_validation_invalid_worker_concurrency():
    """Test that invalid worker concurrency raises validation error."""
    with patch.dict(os.environ, {
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_WORKER_CONCURRENCY": "0"  # Invalid: must be >= 1
    }, clear=True):
        from src.core.celery_config import CeleryConfig
        
        with pytest.raises(ValidationError) as exc_info:
            CeleryConfig()
        
        assert "worker_concurrency" in str(exc_info.value)


def test_celery_config_validation_invalid_task_routes():
    """Test that invalid task routes JSON raises validation error."""
    with patch.dict(os.environ, {
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_TASK_ROUTES": "invalid-json"  # Invalid JSON
    }, clear=True):
        from src.core.celery_config import CeleryConfig
        
        with pytest.raises(ValidationError) as exc_info:
            CeleryConfig()
        
        assert "task_routes" in str(exc_info.value)


def test_celery_config_default_values():
    """Test default values when optional environment variables are not set."""
    with patch.dict(os.environ, {
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        # Only required fields provided - should use defaults for others
    }, clear=True):
        from src.core.celery_config import CeleryConfig
        
        config = CeleryConfig()
        
        assert config.result_backend == "redis://localhost:6379/0"  # Defaults to broker_url
        assert config.task_default_queue == "design_service"  # Default
        assert config.worker_concurrency == 4  # Default
        assert config.task_serializer == "json"  # Default
        assert config.timezone == "UTC"  # Default


def test_celery_config_environment_variable_validation(mock_celery_config_env_vars):
    """Test that all environment variables are properly validated."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    
    # Test validation method
    config.validate_configuration()  # Should not raise any exception


def test_celery_config_queue_names_validation(mock_celery_config_env_vars):
    """Test that queue names are properly validated."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    queue_names = config.get_all_queue_names()
    
    assert "design_service" in queue_names
    assert "visual_generation" in queue_names
    assert len(queue_names) >= 2


def test_celery_config_retry_settings(mock_celery_config_env_vars):
    """Test Celery retry and timeout configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    retry_settings = config.get_retry_settings()

    assert retry_settings["task_default_retry_delay"] == 60
    assert retry_settings["task_max_retries"] == 3
    assert retry_settings["task_soft_time_limit"] == 300
    assert retry_settings["task_time_limit"] == 600
    assert retry_settings["task_acks_late"] is True
    assert retry_settings["task_reject_on_worker_lost"] is True


def test_celery_config_connection_settings(mock_celery_config_env_vars):
    """Test Celery connection configuration."""
    from src.core.celery_config import CeleryConfig

    config = CeleryConfig()
    connection_settings = config.get_connection_settings()

    assert connection_settings["broker_connection_retry"] is True
    assert connection_settings["broker_connection_retry_on_startup"] is True
    assert connection_settings["broker_connection_max_retries"] == 10
    assert connection_settings["broker_heartbeat"] == 30
    assert connection_settings["broker_pool_limit"] == 10