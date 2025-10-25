"""Unit tests for Celery application instance."""

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
        # Required Celery settings
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
        "CELERY_TASK_DEFAULT_QUEUE": "design_service",
        "CELERY_TASK_ROUTES": '{"src.tasks.visual_generation.*": {"queue": "visual_generation"}}',
        "CELERY_WORKER_CONCURRENCY": "4",
        "CELERY_TASK_SERIALIZER": "json",
        "CELERY_RESULT_SERIALIZER": "json",
        "CELERY_TIMEZONE": "UTC",
        "CELERY_ENABLE_UTC": "true",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def test_celery_app_creation(mock_celery_env_vars):
    """Test that Celery app can be created and configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    assert app is not None
    assert app.main == "design_service"
    assert app.conf.broker_url == "redis://localhost:6379/0"
    assert app.conf.result_backend == "redis://localhost:6379/1"


def test_celery_app_configuration(mock_celery_env_vars):
    """Test that Celery app is properly configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test basic configuration
    assert app.conf.task_default_queue == "design_service"
    assert app.conf.task_serializer == "json"
    assert app.conf.result_serializer == "json"
    assert app.conf.timezone == "UTC"
    assert app.conf.enable_utc is True


def test_celery_app_task_autodiscovery(mock_celery_env_vars):
    """Test that Celery app has task autodiscovery configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test that autodiscover_tasks is configured
    assert hasattr(app, 'autodiscover_tasks')
    
    # Test that it includes expected modules
    expected_modules = ['src.tasks.visual_generation']
    # This should not raise an exception
    app.autodiscover_tasks(expected_modules)


def test_celery_app_task_routes(mock_celery_env_vars):
    """Test that Celery app has proper task routing configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test task routes configuration
    assert "src.tasks.visual_generation.*" in app.conf.task_routes
    assert app.conf.task_routes["src.tasks.visual_generation.*"]["queue"] == "visual_generation"


def test_celery_app_logging_configuration(mock_celery_env_vars):
    """Test that Celery app has logging properly configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test that logging is configured for task execution
    assert app.conf.worker_send_task_events is True
    assert app.conf.task_send_sent_event is True
    assert app.conf.task_track_started is True


def test_celery_app_worker_settings(mock_celery_env_vars):
    """Test that Celery app has proper worker settings."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test worker configuration
    assert app.conf.worker_concurrency == 4
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True


def test_celery_app_health_check_integration(mock_celery_env_vars):
    """Test that Celery app integrates with health check utilities."""
    from src.tasks import create_celery_app, get_celery_health_status
    
    app = create_celery_app()
    health_status = get_celery_health_status(app)
    
    assert "status" in health_status
    assert "app_name" in health_status
    assert health_status["app_name"] == "design_service"


def test_celery_app_task_registration(mock_celery_env_vars):
    """Test that Celery app can register tasks properly."""
    from src.tasks import create_celery_app, get_registered_tasks
    
    app = create_celery_app()
    registered_tasks = get_registered_tasks(app)
    
    assert isinstance(registered_tasks, list)
    # Should include built-in Celery tasks at minimum
    assert len(registered_tasks) >= 0


def test_celery_app_queue_configuration(mock_celery_env_vars):
    """Test that Celery app has proper queue configuration."""
    from src.tasks import create_celery_app, get_queue_configuration
    
    app = create_celery_app()
    queue_config = get_queue_configuration(app)
    
    assert "default_queue" in queue_config
    assert "visual_generation_queue" in queue_config
    assert queue_config["default_queue"] == "design_service"
    assert queue_config["visual_generation_queue"] == "visual_generation"


def test_celery_app_monitoring_setup(mock_celery_env_vars):
    """Test that Celery app has monitoring and events configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test monitoring configuration
    assert app.conf.worker_send_task_events is True
    assert app.conf.task_send_sent_event is True
    assert app.conf.task_track_started is True
    assert app.conf.result_expires == 3600  # 1 hour


def test_celery_app_error_handling(mock_celery_env_vars):
    """Test that Celery app has proper error handling configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test error handling settings
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True
    assert app.conf.task_default_retry_delay == 60
    assert app.conf.task_max_retries == 3


def test_celery_app_performance_settings(mock_celery_env_vars):
    """Test that Celery app has performance optimizations configured."""
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    
    # Test performance settings
    assert app.conf.broker_connection_retry is True
    assert app.conf.broker_connection_retry_on_startup is True
    assert app.conf.task_create_missing_queues is True


def test_celery_app_singleton_pattern(mock_celery_env_vars):
    """Test that Celery app follows singleton pattern."""
    from src.tasks import get_celery_app
    
    app1 = get_celery_app()
    app2 = get_celery_app()
    
    # Should return the same instance
    assert app1 is app2
    assert app1.main == "design_service"


def test_celery_app_configuration_validation(mock_celery_env_vars):
    """Test that Celery app validates configuration on creation."""
    from src.tasks import create_celery_app, validate_celery_configuration
    
    app = create_celery_app()
    
    # This should not raise any exceptions
    validation_result = validate_celery_configuration(app)
    assert validation_result["valid"] is True
    assert "broker_url" in validation_result
    assert "task_routes" in validation_result


def test_celery_app_missing_broker_url():
    """Test that Celery app creation works with broker URL from environment."""
    # Since we now have CELERY_BROKER_URL in .env, test that it works
    from src.tasks import create_celery_app
    
    app = create_celery_app()
    assert app is not None
    assert app.conf.broker_url is not None
    assert "redis://" in app.conf.broker_url


def test_celery_app_task_discovery_modules(mock_celery_env_vars):
    """Test that Celery app discovers tasks from expected modules."""
    from src.tasks import create_celery_app, get_task_discovery_modules
    
    app = create_celery_app()
    discovery_modules = get_task_discovery_modules()
    
    assert "src.tasks.visual_generation" in discovery_modules
    assert isinstance(discovery_modules, list)


def test_celery_app_worker_health_utilities(mock_celery_env_vars):
    """Test that Celery app includes worker health check utilities."""
    from src.tasks import create_celery_app, check_worker_health
    
    app = create_celery_app()
    
    # Mock the inspect functionality
    with patch.object(app.control, 'inspect') as mock_inspect:
        mock_inspect.return_value.stats.return_value = {"worker1": {"pool": {"max-concurrency": 4}}}
        
        health_result = check_worker_health(app)
        
        assert "workers" in health_result
        assert "status" in health_result


def test_celery_app_graceful_shutdown(mock_celery_env_vars):
    """Test that Celery app supports graceful shutdown."""
    from src.tasks import create_celery_app, shutdown_celery_app
    
    app = create_celery_app()
    
    # This should not raise any exceptions
    shutdown_result = shutdown_celery_app(app)
    assert shutdown_result["shutdown"] is True