"""
Celery connectivity and configuration utilities for Design Service.

This module provides functions for creating and configuring Celery applications,
testing Redis connections, and validating task queue configurations for the
visual generation task queue system.

Key Features:
- Celery application creation and configuration
- Redis broker connection testing
- Task routing and queue management
- Worker health monitoring
- Environment-based configuration
"""

import json
import logging
import os
from typing import Dict, List, Optional
from urllib.parse import urlparse

import redis
from celery import Celery

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_QUEUE = "design_service"
DEFAULT_VISUAL_QUEUE = "visual_generation"
DEFAULT_WORKER_CONCURRENCY = 4
DEFAULT_WORKER_PREFETCH = 1
DEFAULT_SERIALIZER = "json"
DEFAULT_TIMEZONE = "UTC"

# Supported broker schemes
SUPPORTED_BROKER_SCHEMES = ["redis", "rediss"]


def validate_broker_url(broker_url: str) -> bool:
    """
    Validate broker URL format and scheme.
    
    Args:
        broker_url: The broker URL to validate (e.g., 'redis://localhost:6379/0')
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If URL format is invalid or scheme is unsupported
    """
    if not broker_url or not isinstance(broker_url, str):
        raise ValueError("Broker URL must be a non-empty string")
    
    try:
        parsed = urlparse(broker_url)
        
        # Check for required components
        if not parsed.scheme:
            raise ValueError(f"Missing scheme in broker URL: {broker_url}")
        if not parsed.netloc:
            raise ValueError(f"Missing host/port in broker URL: {broker_url}")
        
        # Check for supported schemes
        if parsed.scheme not in SUPPORTED_BROKER_SCHEMES:
            raise ValueError(
                f"Unsupported broker scheme '{parsed.scheme}'. "
                f"Supported schemes: {', '.join(SUPPORTED_BROKER_SCHEMES)}"
            )
        
        logger.debug(f"Broker URL validation successful: {parsed.scheme}://{parsed.netloc}")
        return True
        
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid broker URL format: {broker_url}") from e


def test_redis_connection(broker_url: str, timeout: int = 5) -> bool:
    """
    Test Redis broker connection with timeout.
    
    Args:
        broker_url: Redis connection URL
        timeout: Connection timeout in seconds (default: 5)
        
    Returns:
        True if connection successful
        
    Raises:
        redis.ConnectionError: If connection fails
        redis.TimeoutError: If connection times out
        ValueError: If broker URL is invalid
    """
    # Validate URL first
    validate_broker_url(broker_url)
    
    try:
        # Create Redis client with timeout
        redis_client = redis.Redis.from_url(
            broker_url,
            socket_connect_timeout=timeout,
            socket_timeout=timeout
        )
        
        # Test connection
        redis_client.ping()
        logger.info(f"Redis connection test successful: {broker_url}")
        return True
        
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        raise
    except redis.TimeoutError as e:
        logger.error(f"Redis connection timeout: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error testing Redis connection: {e}")
        raise


def create_celery_app(app_name: str = "design_service") -> Celery:
    """
    Create and configure Celery application with comprehensive settings.
    
    Args:
        app_name: Name of the Celery application (default: "design_service")
        
    Returns:
        Configured Celery application instance
        
    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    # Get and validate required environment variables
    broker_url = os.getenv("CELERY_BROKER_URL")
    if not broker_url:
        raise ValueError(
            "CELERY_BROKER_URL environment variable is required. "
            "Example: redis://localhost:6379/0"
        )
    
    # Validate broker URL
    validate_broker_url(broker_url)
    
    result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)
    validate_broker_url(result_backend)
    
    logger.info(f"Creating Celery app '{app_name}' with broker: {broker_url}")
    
    # Create Celery app
    app = Celery(app_name)
    
    # Configure broker and result backend
    app.conf.broker_url = broker_url
    app.conf.result_backend = result_backend
    
    # Task routing configuration
    _configure_task_routing(app)
    
    # Serialization settings
    _configure_serialization(app)
    
    # Timezone settings
    _configure_timezone(app)
    
    # Worker settings
    _configure_worker_settings(app)
    
    # Additional performance and reliability settings
    _configure_advanced_settings(app)
    
    logger.info(f"Celery app '{app_name}' configured successfully")
    return app


def _configure_task_routing(app: Celery) -> None:
    """Configure task routing and queue settings."""
    default_queue = os.getenv("CELERY_TASK_DEFAULT_QUEUE", DEFAULT_QUEUE)
    app.conf.task_default_queue = default_queue
    
    # Parse task routes from environment
    task_routes_str = os.getenv("CELERY_TASK_ROUTES", "{}")
    try:
        task_routes = json.loads(task_routes_str)
        app.conf.task_routes = task_routes
        logger.debug(f"Task routes configured: {task_routes}")
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid CELERY_TASK_ROUTES JSON, using empty routes: {e}")
        app.conf.task_routes = {}


def _configure_serialization(app: Celery) -> None:
    """Configure serialization settings."""
    app.conf.task_serializer = os.getenv("CELERY_TASK_SERIALIZER", DEFAULT_SERIALIZER)
    app.conf.result_serializer = os.getenv("CELERY_RESULT_SERIALIZER", DEFAULT_SERIALIZER)
    
    accept_content_str = os.getenv("CELERY_ACCEPT_CONTENT", '["json"]')
    try:
        accept_content = json.loads(accept_content_str)
        app.conf.accept_content = accept_content
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid CELERY_ACCEPT_CONTENT JSON, using default: {e}")
        app.conf.accept_content = ["json"]


def _configure_timezone(app: Celery) -> None:
    """Configure timezone settings."""
    app.conf.timezone = os.getenv("CELERY_TIMEZONE", DEFAULT_TIMEZONE)
    app.conf.enable_utc = os.getenv("CELERY_ENABLE_UTC", "true").lower() == "true"


def _configure_worker_settings(app: Celery) -> None:
    """Configure worker-specific settings."""
    # Worker concurrency
    worker_concurrency_str = os.getenv("CELERY_WORKER_CONCURRENCY", str(DEFAULT_WORKER_CONCURRENCY))
    try:
        app.conf.worker_concurrency = int(worker_concurrency_str)
    except ValueError as e:
        logger.warning(f"Invalid CELERY_WORKER_CONCURRENCY, using default {DEFAULT_WORKER_CONCURRENCY}: {e}")
        app.conf.worker_concurrency = DEFAULT_WORKER_CONCURRENCY
    
    # Worker prefetch multiplier
    worker_prefetch_str = os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", str(DEFAULT_WORKER_PREFETCH))
    try:
        app.conf.worker_prefetch_multiplier = int(worker_prefetch_str)
    except ValueError as e:
        logger.warning(f"Invalid CELERY_WORKER_PREFETCH_MULTIPLIER, using default {DEFAULT_WORKER_PREFETCH}: {e}")
        app.conf.worker_prefetch_multiplier = DEFAULT_WORKER_PREFETCH


def _configure_advanced_settings(app: Celery) -> None:
    """Configure advanced Celery settings for reliability and performance."""
    # Task execution settings
    app.conf.task_acks_late = True
    app.conf.task_reject_on_worker_lost = True
    
    # Result backend settings
    app.conf.result_expires = 3600  # 1 hour
    app.conf.result_persistent = True
    
    # Connection settings
    app.conf.broker_connection_retry_on_startup = True
    app.conf.broker_connection_retry = True
    
    # Task routing
    app.conf.task_create_missing_queues = True


def check_celery_health(timeout: int = 10) -> Dict:
    """
    Check Celery worker health status with comprehensive diagnostics.
    
    Args:
        timeout: Timeout for health check operations in seconds
        
    Returns:
        Dictionary containing health status, worker information, and diagnostics
    """
    try:
        app = create_celery_app()
        inspect = app.control.inspect(timeout=timeout)
        
        # Get worker statistics
        stats = inspect.stats()
        active_tasks = inspect.active()
        registered_tasks = inspect.registered()
        
        if stats:
            worker_count = len(stats)
            total_pool_size = sum(
                worker_stats.get("pool", {}).get("max-concurrency", 0)
                for worker_stats in stats.values()
            )
            
            active_task_count = sum(
                len(tasks) for tasks in (active_tasks or {}).values()
            )
            
            return {
                "status": "healthy",
                "timestamp": _get_current_timestamp(),
                "workers": {
                    "count": worker_count,
                    "total_pool_size": total_pool_size,
                    "stats": stats
                },
                "tasks": {
                    "active_count": active_task_count,
                    "active": active_tasks,
                    "registered": registered_tasks
                }
            }
        else:
            return {
                "status": "unhealthy",
                "timestamp": _get_current_timestamp(),
                "error": "No workers available",
                "workers": {"count": 0}
            }
            
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": _get_current_timestamp(),
            "error": str(e),
            "workers": {"count": 0}
        }


def _get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_queue_configuration() -> Dict:
    """
    Validate and analyze queue configuration settings.
    
    Returns:
        Dictionary containing comprehensive queue configuration analysis
    """
    default_queue = os.getenv("CELERY_TASK_DEFAULT_QUEUE", DEFAULT_QUEUE)
    
    # Parse task routes to analyze queue configuration
    task_routes_str = os.getenv("CELERY_TASK_ROUTES", "{}")
    visual_queue = DEFAULT_VISUAL_QUEUE
    configured_routes = {}
    
    try:
        task_routes = json.loads(task_routes_str)
        configured_routes = task_routes.copy()
        
        # Find visual generation queue from routes
        for pattern, config in task_routes.items():
            if "visual_generation" in pattern:
                visual_queue = config.get("queue", DEFAULT_VISUAL_QUEUE)
                break
                
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid CELERY_TASK_ROUTES JSON: {e}")
    
    # Analyze queue configuration
    unique_queues = {default_queue, visual_queue}
    for route_config in configured_routes.values():
        if isinstance(route_config, dict) and "queue" in route_config:
            unique_queues.add(route_config["queue"])
    
    return {
        "default_queue": default_queue,
        "visual_generation_queue": visual_queue,
        "configured_routes": configured_routes,
        "unique_queues": sorted(list(unique_queues)),
        "queue_count": len(unique_queues),
        "queues_configured": len(configured_routes) > 0,
        "validation_status": "valid"
    }


def get_celery_configuration_summary() -> Dict:
    """
    Get a comprehensive summary of current Celery configuration.
    
    Returns:
        Dictionary containing complete configuration summary
    """
    try:
        broker_url = os.getenv("CELERY_BROKER_URL", "Not configured")
        result_backend = os.getenv("CELERY_RESULT_BACKEND", "Not configured")
        
        # Mask sensitive information in URLs
        masked_broker = _mask_url_credentials(broker_url)
        masked_result_backend = _mask_url_credentials(result_backend)
        
        return {
            "broker": {
                "url": masked_broker,
                "configured": broker_url != "Not configured"
            },
            "result_backend": {
                "url": masked_result_backend,
                "configured": result_backend != "Not configured"
            },
            "queues": validate_queue_configuration(),
            "worker": {
                "concurrency": os.getenv("CELERY_WORKER_CONCURRENCY", str(DEFAULT_WORKER_CONCURRENCY)),
                "prefetch_multiplier": os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", str(DEFAULT_WORKER_PREFETCH))
            },
            "serialization": {
                "task_serializer": os.getenv("CELERY_TASK_SERIALIZER", DEFAULT_SERIALIZER),
                "result_serializer": os.getenv("CELERY_RESULT_SERIALIZER", DEFAULT_SERIALIZER),
                "accept_content": os.getenv("CELERY_ACCEPT_CONTENT", '["json"]')
            },
            "timezone": {
                "timezone": os.getenv("CELERY_TIMEZONE", DEFAULT_TIMEZONE),
                "enable_utc": os.getenv("CELERY_ENABLE_UTC", "true")
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting Celery configuration summary: {e}")
        return {
            "error": str(e),
            "status": "configuration_error"
        }


def _mask_url_credentials(url: str) -> str:
    """Mask credentials in URL for logging/display purposes."""
    if not url or url == "Not configured":
        return url
    
    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            # Replace credentials with masked version
            netloc = parsed.netloc
            if "@" in netloc:
                netloc = "***:***@" + netloc.split("@", 1)[1]
            return f"{parsed.scheme}://{netloc}{parsed.path}"
        return url
    except Exception:
        return url