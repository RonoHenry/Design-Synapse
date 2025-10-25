"""Unit tests for Celery connectivity and configuration."""

import os
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def disable_env_file(monkeypatch):
    """Disable .env file loading for all tests in this module."""
    monkeypatch.setenv("PYDANTIC_SETTINGS_IGNORE_ENV_FILE", "1")


@pytest.fixture
def mock_celery_env_vars(monkeypatch):
    """Set up mock environment variables for Celery testing."""
    # Clear existing Celery-related environment variables
    celery_env_keys = [k for k in os.environ.keys() if k.startswith("CELERY_")]
    for key in celery_env_keys:
        monkeypatch.delenv(key, raising=False)
    
    env_vars = {
        # Redis broker settings
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
        # Task routing
        "CELERY_TASK_DEFAULT_QUEUE": "design_service",
        "CELERY_TASK_ROUTES": '{"src.tasks.visual_generation.*": {"queue": "visual_generation"}}',
        # Worker settings
        "CELERY_WORKER_CONCURRENCY": "4",
        "CELERY_WORKER_PREFETCH_MULTIPLIER": "1",
        # Task settings
        "CELERY_TASK_SERIALIZER": "json",
        "CELERY_RESULT_SERIALIZER": "json",
        "CELERY_ACCEPT_CONTENT": '["json"]',
        "CELERY_TIMEZONE": "UTC",
        "CELERY_ENABLE_UTC": "true",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def test_celery_import_available():
    """Test that Celery can be imported."""
    try:
        import celery
        assert celery.__version__ is not None
    except ImportError:
        pytest.fail("Celery is not installed or not importable")


def test_redis_import_available():
    """Test that Redis client can be imported."""
    try:
        import redis
        assert redis.__version__ is not None
    except ImportError:
        pytest.fail("Redis client is not installed or not importable")


@patch('src.infrastructure.celery_connectivity.redis.Redis')
def test_redis_broker_connection(mock_redis_class, mock_celery_env_vars):
    """Test Redis broker connection."""
    # Arrange
    mock_redis_client = Mock()
    mock_redis_class.from_url.return_value = mock_redis_client
    mock_redis_client.ping.return_value = True
    
    # Import after mocking to avoid actual connection
    from src.infrastructure.celery_connectivity import test_redis_connection
    
    # Act
    result = test_redis_connection("redis://localhost:6379/0")
    
    # Assert
    assert result is True
    mock_redis_class.from_url.assert_called_once_with(
        "redis://localhost:6379/0",
        socket_connect_timeout=5,
        socket_timeout=5
    )
    mock_redis_client.ping.assert_called_once()


@patch('src.infrastructure.celery_connectivity.redis.Redis')
def test_redis_broker_connection_failure(mock_redis_class, mock_celery_env_vars):
    """Test Redis broker connection failure handling."""
    # Arrange
    mock_redis_client = Mock()
    mock_redis_class.from_url.return_value = mock_redis_client
    mock_redis_client.ping.side_effect = Exception("Connection failed")
    
    from src.infrastructure.celery_connectivity import test_redis_connection
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        test_redis_connection("redis://localhost:6379/0")
    
    assert "Connection failed" in str(exc_info.value)


def test_celery_app_creation(mock_celery_env_vars):
    """Test Celery application creation."""
    from src.infrastructure.celery_connectivity import create_celery_app
    
    # Act
    app = create_celery_app()
    
    # Assert
    assert app is not None
    assert app.main == "design_service"
    assert app.conf.broker_url == "redis://localhost:6379/0"
    assert app.conf.result_backend == "redis://localhost:6379/0"


def test_celery_task_routing_configuration(mock_celery_env_vars):
    """Test Celery task routing configuration."""
    from src.infrastructure.celery_connectivity import create_celery_app
    
    # Act
    app = create_celery_app()
    
    # Assert
    assert app.conf.task_default_queue == "design_service"
    assert "src.tasks.visual_generation.*" in app.conf.task_routes
    assert app.conf.task_routes["src.tasks.visual_generation.*"]["queue"] == "visual_generation"


def test_celery_serialization_settings(mock_celery_env_vars):
    """Test Celery serialization settings."""
    from src.infrastructure.celery_connectivity import create_celery_app
    
    # Act
    app = create_celery_app()
    
    # Assert
    assert app.conf.task_serializer == "json"
    assert app.conf.result_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert app.conf.timezone == "UTC"
    assert app.conf.enable_utc is True


def test_celery_worker_settings(mock_celery_env_vars):
    """Test Celery worker configuration."""
    from src.infrastructure.celery_connectivity import create_celery_app
    
    # Act
    app = create_celery_app()
    
    # Assert
    assert app.conf.worker_concurrency == 4
    assert app.conf.worker_prefetch_multiplier == 1


def test_celery_task_discovery(mock_celery_env_vars):
    """Test Celery task autodiscovery configuration."""
    from src.infrastructure.celery_connectivity import create_celery_app
    
    # Act
    app = create_celery_app()
    
    # Assert
    # Check that autodiscover_tasks is configured
    assert hasattr(app, 'autodiscover_tasks')
    # Check that it includes the expected modules
    expected_modules = ['src.tasks.visual_generation']
    app.autodiscover_tasks(expected_modules)


@patch('src.infrastructure.celery_connectivity.create_celery_app')
def test_celery_health_check(mock_create_app, mock_celery_env_vars):
    """Test Celery health check functionality."""
    # Arrange
    mock_app = Mock()
    mock_create_app.return_value = mock_app
    
    # Mock the inspect chain properly
    mock_inspect = Mock()
    mock_app.control.inspect.return_value = mock_inspect
    mock_inspect.stats.return_value = {"worker1": {"pool": {"max-concurrency": 4}}}
    mock_inspect.active.return_value = {"worker1": []}
    mock_inspect.registered.return_value = {"worker1": ["task1", "task2"]}
    
    from src.infrastructure.celery_connectivity import check_celery_health
    
    # Act
    result = check_celery_health()
    
    # Assert
    assert result["status"] == "healthy"
    assert "workers" in result
    assert result["workers"]["count"] == 1
    assert result["workers"]["total_pool_size"] == 4
    assert "tasks" in result


@patch('src.infrastructure.celery_connectivity.create_celery_app')
def test_celery_health_check_no_workers(mock_create_app, mock_celery_env_vars):
    """Test Celery health check when no workers are available."""
    # Arrange
    mock_app = Mock()
    mock_create_app.return_value = mock_app
    mock_app.control.inspect.return_value.stats.return_value = None
    
    from src.infrastructure.celery_connectivity import check_celery_health
    
    # Act
    result = check_celery_health()
    
    # Assert
    assert result["status"] == "unhealthy"
    assert result["error"] == "No workers available"


def test_queue_configuration_validation(mock_celery_env_vars):
    """Test that queue configuration is properly validated."""
    from src.infrastructure.celery_connectivity import validate_queue_configuration
    
    # Act
    result = validate_queue_configuration()
    
    # Assert
    assert result["default_queue"] == "design_service"
    assert result["visual_generation_queue"] == "visual_generation"
    assert result["queues_configured"] is True


def test_missing_broker_url_raises_error():
    """Test that missing broker URL raises configuration error."""
    with patch.dict(os.environ, {}, clear=True):
        from src.infrastructure.celery_connectivity import create_celery_app
        
        with pytest.raises(ValueError) as exc_info:
            create_celery_app()
        
        assert "CELERY_BROKER_URL" in str(exc_info.value)


def test_invalid_broker_url_format():
    """Test that invalid broker URL format raises error."""
    with patch.dict(os.environ, {"CELERY_BROKER_URL": "invalid-url"}, clear=True):
        from src.infrastructure.celery_connectivity import validate_broker_url
        
        with pytest.raises(ValueError) as exc_info:
            validate_broker_url("invalid-url")
        
        assert "Missing scheme in broker URL" in str(exc_info.value)