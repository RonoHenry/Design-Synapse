"""
Celery application instance and task management for Design Service.

This module provides the main Celery application instance configured for
visual generation tasks, along with comprehensive utilities for health monitoring,
task discovery, worker management, and application lifecycle management.

Key Features:
- Singleton Celery application instance
- Task autodiscovery for visual generation modules
- Worker health monitoring and diagnostics
- Configuration validation and management
- Graceful shutdown and lifecycle management

Usage:
    from src.tasks import celery_app, get_celery_health_status
    
    # Use the global app instance
    @celery_app.task
    def my_task():
        pass
    
    # Check health status
    health = get_celery_health_status()
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from ..core.celery_config import CeleryConfig
from ..infrastructure.celery_connectivity import (
    check_celery_health,
    get_celery_configuration_summary,
    validate_broker_url,
)

# Configure logging
logger = logging.getLogger(__name__)

# Global Celery app instance
_celery_app: Optional[Celery] = None

# Task discovery modules
TASK_DISCOVERY_MODULES = [
    'src.tasks.visual_generation',
]

# Worker health tracking
_worker_health_data: Dict = {
    "workers": {},
    "last_check": None,
    "check_count": 0,
}

# Health check thresholds
HEALTH_CHECK_TIMEOUT = 10  # seconds
WORKER_RESPONSE_TIMEOUT = 5  # seconds
MAX_FAILED_HEALTH_CHECKS = 3


def create_celery_app(app_name: str = "design_service") -> Celery:
    """
    Create and configure a new Celery application instance.
    
    Args:
        app_name: Name of the Celery application
        
    Returns:
        Configured Celery application instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    logger.info(f"Creating Celery application: {app_name}")
    
    # Get configuration
    config = CeleryConfig()
    celery_config = config.get_complete_celery_config()
    
    # Create Celery app
    app = Celery(app_name)
    
    # Apply configuration
    app.config_from_object(celery_config)
    
    # Configure task autodiscovery
    app.autodiscover_tasks(TASK_DISCOVERY_MODULES)
    
    logger.info(f"Celery application '{app_name}' created successfully")
    return app


def get_celery_app() -> Celery:
    """
    Get or create the global Celery application instance (singleton pattern).
    
    Returns:
        Global Celery application instance
    """
    global _celery_app
    
    if _celery_app is None:
        _celery_app = create_celery_app()
    
    return _celery_app


def get_celery_health_status(app: Optional[Celery] = None) -> Dict:
    """
    Get health status of the Celery application.
    
    Args:
        app: Celery application instance (uses global if None)
        
    Returns:
        Dictionary containing health status information
    """
    if app is None:
        app = get_celery_app()
    
    try:
        # Get basic app info
        health_status = {
            "status": "healthy",
            "app_name": app.main,
            "broker_url": app.conf.broker_url,
            "result_backend": app.conf.result_backend,
        }
        
        # Get worker health from connectivity module
        worker_health = check_celery_health()
        health_status.update(worker_health)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error getting Celery health status: {e}")
        return {
            "status": "unhealthy",
            "app_name": app.main if app else "unknown",
            "error": str(e)
        }


def get_registered_tasks(app: Optional[Celery] = None) -> List[str]:
    """
    Get list of registered tasks in the Celery application.
    
    Args:
        app: Celery application instance (uses global if None)
        
    Returns:
        List of registered task names
    """
    if app is None:
        app = get_celery_app()
    
    try:
        return list(app.tasks.keys())
    except Exception as e:
        logger.error(f"Error getting registered tasks: {e}")
        return []


def get_queue_configuration(app: Optional[Celery] = None) -> Dict:
    """
    Get queue configuration from the Celery application.
    
    Args:
        app: Celery application instance (uses global if None)
        
    Returns:
        Dictionary containing queue configuration
    """
    if app is None:
        app = get_celery_app()
    
    try:
        # Extract queue information from task routes
        visual_generation_queue = "visual_generation"
        for pattern, config in app.conf.task_routes.items():
            if "visual_generation" in pattern and isinstance(config, dict):
                visual_generation_queue = config.get("queue", "visual_generation")
                break
        
        return {
            "default_queue": app.conf.task_default_queue,
            "visual_generation_queue": visual_generation_queue,
            "task_routes": app.conf.task_routes,
        }
        
    except Exception as e:
        logger.error(f"Error getting queue configuration: {e}")
        return {
            "default_queue": "design_service",
            "visual_generation_queue": "visual_generation",
            "task_routes": {},
        }


def get_task_discovery_modules() -> List[str]:
    """
    Get list of modules configured for task discovery.
    
    Returns:
        List of module names for task discovery
    """
    return TASK_DISCOVERY_MODULES.copy()


def validate_celery_configuration(app: Optional[Celery] = None) -> Dict:
    """
    Validate the Celery application configuration.
    
    Args:
        app: Celery application instance (uses global if None)
        
    Returns:
        Dictionary containing validation results
    """
    if app is None:
        app = get_celery_app()
    
    try:
        validation_result = {
            "valid": True,
            "app_name": app.main,
            "broker_url": app.conf.broker_url,
            "result_backend": app.conf.result_backend,
            "task_routes": app.conf.task_routes,
            "errors": []
        }
        
        # Validate broker URL
        try:
            validate_broker_url(app.conf.broker_url)
        except ValueError as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Broker URL validation failed: {e}")
        
        # Validate basic configuration
        if not app.conf.task_default_queue:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing task_default_queue configuration")
        
        if not app.conf.task_serializer:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing task_serializer configuration")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating Celery configuration: {e}")
        return {
            "valid": False,
            "error": str(e),
            "errors": [str(e)]
        }


def check_worker_health(app: Optional[Celery] = None, timeout: int = HEALTH_CHECK_TIMEOUT) -> Dict:
    """
    Comprehensive health check of Celery workers with detailed diagnostics.
    
    Args:
        app: Celery application instance (uses global if None)
        timeout: Timeout for health check operations in seconds
        
    Returns:
        Dictionary containing detailed worker health information
    """
    if app is None:
        app = get_celery_app()
    
    global _worker_health_data
    check_start_time = time.time()
    
    try:
        inspect = app.control.inspect(timeout=timeout)
        
        # Get comprehensive worker information
        stats = inspect.stats()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        registered_tasks = inspect.registered()
        
        # Update health tracking
        _worker_health_data["last_check"] = datetime.now(timezone.utc).isoformat()
        _worker_health_data["check_count"] += 1
        
        if stats:
            worker_details = {}
            total_active_tasks = 0
            total_pool_size = 0
            
            for worker_name, worker_stats in stats.items():
                # Calculate worker metrics
                pool_info = worker_stats.get("pool", {})
                pool_size = pool_info.get("max-concurrency", 0)
                active_count = len(active_tasks.get(worker_name, []))
                scheduled_count = len(scheduled_tasks.get(worker_name, []))
                reserved_count = len(reserved_tasks.get(worker_name, []))
                
                total_active_tasks += active_count
                total_pool_size += pool_size
                
                # Determine worker health status
                worker_health = "healthy"
                if active_count >= pool_size * 0.9:  # 90% capacity
                    worker_health = "busy"
                elif active_count == 0 and scheduled_count == 0:
                    worker_health = "idle"
                
                worker_details[worker_name] = {
                    "status": worker_health,
                    "pool_size": pool_size,
                    "active_tasks": active_count,
                    "scheduled_tasks": scheduled_count,
                    "reserved_tasks": reserved_count,
                    "registered_tasks": len(registered_tasks.get(worker_name, [])),
                    "load_factor": round(active_count / max(pool_size, 1), 2),
                    "stats": worker_stats,
                }
                
                # Update worker health tracking
                _worker_health_data["workers"][worker_name] = {
                    "last_seen": _worker_health_data["last_check"],
                    "status": worker_health,
                    "consecutive_failures": 0,
                }
            
            # Calculate overall health
            overall_status = "healthy"
            if total_active_tasks >= total_pool_size * 0.8:  # 80% overall capacity
                overall_status = "busy"
            elif total_active_tasks == 0:
                overall_status = "idle"
            
            check_duration = round(time.time() - check_start_time, 3)
            
            return {
                "status": overall_status,
                "timestamp": _worker_health_data["last_check"],
                "check_duration_seconds": check_duration,
                "workers": worker_details,
                "summary": {
                    "worker_count": len(stats),
                    "total_pool_size": total_pool_size,
                    "total_active_tasks": total_active_tasks,
                    "average_load_factor": round(total_active_tasks / max(total_pool_size, 1), 2),
                },
                "queues": _get_queue_health_info(app),
            }
        else:
            # No workers available
            _update_worker_failures()
            
            return {
                "status": "unhealthy",
                "timestamp": _worker_health_data["last_check"],
                "check_duration_seconds": round(time.time() - check_start_time, 3),
                "workers": {},
                "summary": {
                    "worker_count": 0,
                    "total_pool_size": 0,
                    "total_active_tasks": 0,
                    "average_load_factor": 0,
                },
                "error": "No workers available",
                "queues": {},
            }
            
    except Exception as e:
        logger.error(f"Error checking worker health: {e}")
        _update_worker_failures()
        
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check_duration_seconds": round(time.time() - check_start_time, 3),
            "workers": {},
            "summary": {
                "worker_count": 0,
                "total_pool_size": 0,
                "total_active_tasks": 0,
                "average_load_factor": 0,
            },
            "error": str(e),
            "queues": {},
        }


def _get_queue_health_info(app: Celery) -> Dict:
    """Get health information for configured queues."""
    try:
        queue_config = get_queue_configuration(app)
        return {
            "configured_queues": [
                queue_config["default_queue"],
                queue_config["visual_generation_queue"]
            ],
            "routing_rules": len(queue_config["task_routes"]),
        }
    except Exception as e:
        logger.error(f"Error getting queue health info: {e}")
        return {}


def _update_worker_failures():
    """Update failure counts for worker health tracking."""
    global _worker_health_data
    
    for worker_name in _worker_health_data["workers"]:
        _worker_health_data["workers"][worker_name]["consecutive_failures"] += 1


def get_worker_diagnostics(app: Optional[Celery] = None) -> Dict:
    """
    Get detailed diagnostics for Celery workers.
    
    Args:
        app: Celery application instance (uses global if None)
        
    Returns:
        Dictionary containing comprehensive worker diagnostics
    """
    if app is None:
        app = get_celery_app()
    
    try:
        inspect = app.control.inspect(timeout=WORKER_RESPONSE_TIMEOUT)
        
        # Gather comprehensive diagnostics
        diagnostics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "app_info": {
                "name": app.main,
                "broker_url": _mask_url_credentials(app.conf.broker_url),
                "result_backend": _mask_url_credentials(app.conf.result_backend or ""),
            },
            "workers": {},
            "system_info": {},
        }
        
        # Get worker-specific diagnostics
        stats = inspect.stats()
        if stats:
            for worker_name, worker_stats in stats.items():
                diagnostics["workers"][worker_name] = {
                    "broker_info": worker_stats.get("broker", {}),
                    "pool_info": worker_stats.get("pool", {}),
                    "rusage": worker_stats.get("rusage_soft", {}),
                    "clock": worker_stats.get("clock", "unknown"),
                    "pid": worker_stats.get("pid", "unknown"),
                }
        
        # Get system-level information
        diagnostics["system_info"] = {
            "registered_tasks": len(app.tasks),
            "task_discovery_modules": TASK_DISCOVERY_MODULES,
            "health_check_history": {
                "total_checks": _worker_health_data["check_count"],
                "last_check": _worker_health_data["last_check"],
            },
        }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Error getting worker diagnostics: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "app_info": {
                "name": app.main if app else "unknown",
            },
            "workers": {},
            "system_info": {},
        }


def monitor_worker_performance(app: Optional[Celery] = None, duration_minutes: int = 5) -> Dict:
    """
    Monitor worker performance over a specified duration.
    
    Args:
        app: Celery application instance (uses global if None)
        duration_minutes: Duration to monitor in minutes
        
    Returns:
        Dictionary containing performance monitoring results
    """
    if app is None:
        app = get_celery_app()
    
    start_time = datetime.now(timezone.utc)
    monitoring_data = {
        "start_time": start_time.isoformat(),
        "duration_minutes": duration_minutes,
        "samples": [],
        "summary": {},
    }
    
    try:
        # Take initial sample
        initial_health = check_worker_health(app)
        monitoring_data["samples"].append({
            "timestamp": start_time.isoformat(),
            "health_data": initial_health,
        })
        
        # For now, return the initial sample
        # In a real implementation, this would collect samples over time
        monitoring_data["summary"] = {
            "initial_worker_count": initial_health.get("summary", {}).get("worker_count", 0),
            "initial_load_factor": initial_health.get("summary", {}).get("average_load_factor", 0),
            "status": initial_health.get("status", "unknown"),
        }
        
        return monitoring_data
        
    except Exception as e:
        logger.error(f"Error monitoring worker performance: {e}")
        return {
            "start_time": start_time.isoformat(),
            "duration_minutes": duration_minutes,
            "error": str(e),
            "samples": [],
            "summary": {},
        }


def _mask_url_credentials(url: str) -> str:
    """Mask credentials in URL for logging/display purposes."""
    if not url:
        return url
    
    try:
        from urllib.parse import urlparse
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


def shutdown_celery_app(app: Optional[Celery] = None) -> Dict:
    """
    Gracefully shutdown the Celery application.
    
    Args:
        app: Celery application instance (uses global if None)
        
    Returns:
        Dictionary containing shutdown status
    """
    if app is None:
        app = get_celery_app()
    
    try:
        # Perform graceful shutdown operations
        logger.info(f"Shutting down Celery application: {app.main}")
        
        # Close any open connections
        if hasattr(app, 'close'):
            app.close()
        
        # Reset global app instance
        global _celery_app
        if _celery_app is app:
            _celery_app = None
        
        return {
            "shutdown": True,
            "app_name": app.main,
            "message": "Celery application shutdown successfully"
        }
        
    except Exception as e:
        logger.error(f"Error shutting down Celery application: {e}")
        return {
            "shutdown": False,
            "app_name": app.main if app else "unknown",
            "error": str(e)
        }


# Celery signal handlers for worker lifecycle management
@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info(f"Worker {sender} is ready and available for tasks")
    
    # Update worker health tracking
    global _worker_health_data
    worker_name = str(sender) if sender else "unknown"
    _worker_health_data["workers"][worker_name] = {
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
        "consecutive_failures": 0,
    }


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(f"Worker {sender} is shutting down")
    
    # Clean up worker health tracking
    global _worker_health_data
    worker_name = str(sender) if sender else "unknown"
    if worker_name in _worker_health_data["workers"]:
        del _worker_health_data["workers"][worker_name]


def reset_health_tracking():
    """Reset worker health tracking data."""
    global _worker_health_data
    _worker_health_data = {
        "workers": {},
        "last_check": None,
        "check_count": 0,
    }
    logger.info("Worker health tracking data reset")


def get_health_tracking_summary() -> Dict:
    """
    Get summary of health tracking data.
    
    Returns:
        Dictionary containing health tracking summary
    """
    global _worker_health_data
    
    return {
        "tracking_enabled": True,
        "total_checks_performed": _worker_health_data["check_count"],
        "last_check_time": _worker_health_data["last_check"],
        "tracked_workers": list(_worker_health_data["workers"].keys()),
        "worker_count": len(_worker_health_data["workers"]),
    }


# Create the default app instance for easy import
celery_app = get_celery_app()

# Export key functions and utilities
__all__ = [
    'celery_app',
    'create_celery_app',
    'get_celery_app',
    'get_celery_health_status',
    'check_worker_health',
    'get_worker_diagnostics',
    'monitor_worker_performance',
    'get_registered_tasks',
    'get_queue_configuration',
    'get_task_discovery_modules',
    'validate_celery_configuration',
    'shutdown_celery_app',
    'reset_health_tracking',
    'get_health_tracking_summary',
]