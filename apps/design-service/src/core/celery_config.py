"""
Celery configuration for Design Service.

This module provides comprehensive Celery configuration management using
Pydantic settings with environment variable validation and structured
configuration generation for the visual outputs task queue system.

Key Features:
- Environment-based configuration with validation
- Task routing and queue management
- Worker performance tuning
- Retry and timeout policies
- Connection reliability settings
- Complete Celery app configuration generation

Usage:
    from src.core.celery_config import CeleryConfig
    
    config = CeleryConfig()
    celery_settings = config.get_complete_celery_config()
"""

import json
import logging
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_QUEUE = "design_service"
DEFAULT_VISUAL_QUEUE = "visual_generation"
DEFAULT_WORKER_CONCURRENCY = 4
DEFAULT_WORKER_PREFETCH = 1
DEFAULT_WORKER_MAX_TASKS = 1000
DEFAULT_SERIALIZER = "json"
DEFAULT_TIMEZONE = "UTC"
DEFAULT_RETRY_DELAY = 60
DEFAULT_MAX_RETRIES = 3
DEFAULT_SOFT_TIME_LIMIT = 300
DEFAULT_TIME_LIMIT = 600
DEFAULT_RESULT_EXPIRES = 3600
DEFAULT_CONNECTION_MAX_RETRIES = 10
DEFAULT_HEARTBEAT = 30
DEFAULT_POOL_LIMIT = 10

# Supported broker schemes
SUPPORTED_BROKER_SCHEMES = ["redis", "rediss"]


class CeleryConfig(BaseSettings):
    """
    Comprehensive Celery configuration with environment-based settings.
    
    This class manages all Celery configuration for the Design Service's
    visual generation task queue system, including:
    
    - Broker and result backend configuration
    - Task routing for visual generation queues
    - Worker performance and concurrency settings
    - Retry policies and timeout management
    - Connection reliability and health monitoring
    
    Environment Variables:
        All settings can be configured via environment variables with the
        'CELERY_' prefix. For example:
        
        - CELERY_BROKER_URL: Redis broker URL
        - CELERY_TASK_DEFAULT_QUEUE: Default task queue name
        - CELERY_WORKER_CONCURRENCY: Number of worker processes
        - CELERY_TASK_ROUTES: JSON string for task routing
        
    Example:
        config = CeleryConfig()
        celery_app.config_from_object(config.get_complete_celery_config())
    """

    model_config = SettingsConfigDict(
        env_prefix="CELERY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Broker and result backend settings
    broker_url: str = Field(..., min_length=1, description="Celery broker URL (e.g., redis://localhost:6379/0)")
    result_backend: Optional[str] = Field(default=None, description="Result backend URL (defaults to broker_url)")

    # Task routing settings
    task_default_queue: str = Field(default=DEFAULT_QUEUE, description="Default queue for tasks")
    task_routes: str = Field(default="{}", description="Task routing configuration as JSON")

    # Worker settings
    worker_concurrency: int = Field(
        default=DEFAULT_WORKER_CONCURRENCY, 
        ge=1, 
        le=100,
        description="Number of concurrent worker processes"
    )
    worker_prefetch_multiplier: int = Field(
        default=DEFAULT_WORKER_PREFETCH, 
        ge=1, 
        le=10,
        description="Worker prefetch multiplier"
    )
    worker_max_tasks_per_child: int = Field(
        default=DEFAULT_WORKER_MAX_TASKS, 
        ge=100, 
        le=10000,
        description="Maximum tasks per worker child process"
    )

    # Task settings
    task_serializer: str = Field(default=DEFAULT_SERIALIZER, description="Task serialization format")
    result_serializer: str = Field(default=DEFAULT_SERIALIZER, description="Result serialization format")
    accept_content: str = Field(default='["json"]', description="Accepted content types as JSON")

    # Timezone settings
    timezone: str = Field(default=DEFAULT_TIMEZONE, description="Celery timezone")
    enable_utc: bool = Field(default=True, description="Enable UTC timezone")

    # Retry and timeout settings
    task_default_retry_delay: int = Field(
        default=DEFAULT_RETRY_DELAY, 
        ge=1, 
        le=3600,
        description="Default retry delay in seconds"
    )
    task_max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES, 
        ge=0, 
        le=10,
        description="Maximum number of task retries"
    )
    task_soft_time_limit: int = Field(
        default=DEFAULT_SOFT_TIME_LIMIT, 
        ge=30, 
        le=3600,
        description="Soft time limit for tasks in seconds"
    )
    task_time_limit: int = Field(
        default=DEFAULT_TIME_LIMIT, 
        ge=60, 
        le=7200,
        description="Hard time limit for tasks in seconds"
    )

    # Result backend settings
    result_expires: int = Field(
        default=DEFAULT_RESULT_EXPIRES, 
        ge=300, 
        le=86400,
        description="Result expiration time in seconds"
    )
    result_persistent: bool = Field(default=True, description="Enable persistent results")

    # Connection settings
    broker_connection_retry: bool = Field(default=True, description="Enable broker connection retry")
    broker_connection_retry_on_startup: bool = Field(default=True, description="Retry connection on startup")
    broker_connection_max_retries: int = Field(
        default=DEFAULT_CONNECTION_MAX_RETRIES, 
        ge=1, 
        le=100,
        description="Maximum broker connection retries"
    )

    @field_validator("broker_url")
    @classmethod
    def validate_broker_url(cls, v: str) -> str:
        """Validate broker URL format and scheme."""
        if not v or not isinstance(v, str):
            raise ValueError("Broker URL must be a non-empty string")
        
        try:
            parsed = urlparse(v)
            
            if not parsed.scheme:
                raise ValueError(f"Missing scheme in broker URL: {v}")
            if not parsed.netloc:
                raise ValueError(f"Missing host/port in broker URL: {v}")
            
            if parsed.scheme not in SUPPORTED_BROKER_SCHEMES:
                raise ValueError(
                    f"Unsupported broker scheme '{parsed.scheme}'. "
                    f"Supported schemes: {', '.join(SUPPORTED_BROKER_SCHEMES)}"
                )
            
            return v
            
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid broker URL format: {v}") from e

    @field_validator("task_routes")
    @classmethod
    def validate_task_routes(cls, v: str) -> str:
        """Validate task routes JSON format."""
        if not v:
            return "{}"
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, dict):
                raise ValueError("Task routes must be a JSON object")
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid task routes JSON: {e}") from e

    @field_validator("accept_content")
    @classmethod
    def validate_accept_content(cls, v: str) -> str:
        """Validate accept content JSON format."""
        try:
            content = json.loads(v)
            if not isinstance(content, list):
                raise ValueError("Accept content must be a JSON array")
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid accept content JSON: {e}") from e

    def get_task_routes_dict(self) -> Dict:
        """Get task routes as a dictionary."""
        try:
            return json.loads(self.task_routes)
        except json.JSONDecodeError:
            logger.warning("Invalid task routes JSON, returning empty dict")
            return {}

    def get_accept_content_list(self) -> List[str]:
        """Get accept content as a list."""
        try:
            return json.loads(self.accept_content)
        except json.JSONDecodeError:
            logger.warning("Invalid accept content JSON, returning default")
            return ["json"]

    def model_post_init(self, __context) -> None:
        """Post-initialization processing."""
        # Set result_backend to broker_url if not provided
        if not self.result_backend:
            self.result_backend = self.broker_url

    def get_broker_settings(self) -> Dict:
        """Get broker configuration settings."""
        return {
            "broker_url": self.broker_url,
            "result_backend": self.result_backend,
            "broker_connection_retry": self.broker_connection_retry,
            "broker_connection_retry_on_startup": self.broker_connection_retry_on_startup,
            "broker_connection_max_retries": self.broker_connection_max_retries,
        }

    def get_task_routing_settings(self) -> Dict:
        """Get task routing configuration settings."""
        return {
            "task_default_queue": self.task_default_queue,
            "task_routes": self.get_task_routes_dict(),
            "task_create_missing_queues": True,
        }

    def get_worker_settings(self) -> Dict:
        """Get worker configuration settings."""
        return {
            "worker_concurrency": self.worker_concurrency,
            "worker_prefetch_multiplier": self.worker_prefetch_multiplier,
            "worker_max_tasks_per_child": self.worker_max_tasks_per_child,
        }

    def get_task_settings(self) -> Dict:
        """Get task configuration settings."""
        return {
            "task_serializer": self.task_serializer,
            "result_serializer": self.result_serializer,
            "accept_content": self.get_accept_content_list(),
            "task_default_retry_delay": self.task_default_retry_delay,
            "task_max_retries": self.task_max_retries,
            "task_soft_time_limit": self.task_soft_time_limit,
            "task_time_limit": self.task_time_limit,
        }

    def get_result_backend_settings(self) -> Dict:
        """Get result backend configuration settings."""
        return {
            "result_backend": self.result_backend,
            "result_expires": self.result_expires,
            "result_persistent": self.result_persistent,
        }

    def get_timezone_settings(self) -> Dict:
        """Get timezone configuration settings."""
        return {
            "timezone": self.timezone,
            "enable_utc": self.enable_utc,
        }

    def get_retry_settings(self) -> Dict:
        """Get retry and timeout configuration settings."""
        return {
            "task_default_retry_delay": self.task_default_retry_delay,
            "task_max_retries": self.task_max_retries,
            "task_soft_time_limit": self.task_soft_time_limit,
            "task_time_limit": self.task_time_limit,
            "task_acks_late": True,
            "task_reject_on_worker_lost": True,
        }

    def get_connection_settings(self) -> Dict:
        """Get connection configuration settings."""
        return {
            "broker_connection_retry": self.broker_connection_retry,
            "broker_connection_retry_on_startup": self.broker_connection_retry_on_startup,
            "broker_connection_max_retries": self.broker_connection_max_retries,
            "broker_heartbeat": DEFAULT_HEARTBEAT,
            "broker_pool_limit": DEFAULT_POOL_LIMIT,
        }

    def get_complete_celery_config(self) -> Dict:
        """
        Get complete Celery configuration dictionary optimized for visual generation.
        
        This method combines all configuration sections into a single dictionary
        that can be used directly with Celery's config_from_object() method.
        
        Returns:
            Dictionary containing all Celery configuration settings
        """
        config = {}
        
        # Core configuration sections
        config.update(self.get_broker_settings())
        config.update(self.get_task_routing_settings())
        config.update(self.get_worker_settings())
        config.update(self.get_task_settings())
        config.update(self.get_result_backend_settings())
        config.update(self.get_timezone_settings())
        config.update(self.get_retry_settings())
        config.update(self.get_connection_settings())
        
        # Performance and monitoring optimizations
        config.update(self.get_performance_settings())
        config.update(self.get_monitoring_settings())
        
        # Validate the complete configuration
        try:
            self.validate_configuration()
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        logger.info(f"Generated complete Celery configuration with {len(config)} settings")
        return config

    def get_all_queue_names(self) -> List[str]:
        """
        Get all configured queue names.
        
        Returns:
            List of unique queue names
        """
        queues = {self.task_default_queue}
        
        # Extract queues from task routes
        for route_config in self.get_task_routes_dict().values():
            if isinstance(route_config, dict) and "queue" in route_config:
                queues.add(route_config["queue"])
        
        # Add default visual generation queue if not present
        if DEFAULT_VISUAL_QUEUE not in queues:
            queues.add(DEFAULT_VISUAL_QUEUE)
        
        return sorted(list(queues))

    def get_queue_definitions(self) -> List[Dict]:
        """
        Get queue definitions for Celery configuration.
        
        Returns:
            List of queue definition dictionaries
        """
        queues = []
        for queue_name in self.get_all_queue_names():
            queues.append({
                "name": queue_name,
                "routing_key": queue_name,
                "durable": True,
                "auto_delete": False,
            })
        return queues

    def get_performance_settings(self) -> Dict:
        """
        Get performance-optimized settings for visual generation workloads.
        
        Returns:
            Dictionary containing performance settings
        """
        return {
            # Task execution settings
            "task_acks_late": True,
            "task_reject_on_worker_lost": True,
            "task_track_started": True,
            
            # Worker optimization
            "worker_disable_rate_limits": False,
            "worker_enable_remote_control": True,
            "worker_send_task_events": True,
            
            # Memory management
            "worker_max_memory_per_child": 200000,  # 200MB
            "worker_autoscaler": "celery.worker.autoscale:Autoscaler",
            
            # Connection pooling
            "broker_pool_limit": DEFAULT_POOL_LIMIT,
            "broker_connection_timeout": 4.0,
            "broker_connection_retry": True,
            "broker_connection_max_retries": self.broker_connection_max_retries,
        }

    def get_monitoring_settings(self) -> Dict:
        """
        Get monitoring and logging settings.
        
        Returns:
            Dictionary containing monitoring settings
        """
        return {
            "task_send_sent_event": True,
            "task_track_started": True,
            "worker_send_task_events": True,
            "task_serializer": self.task_serializer,
            "result_serializer": self.result_serializer,
            "event_serializer": "json",
            "result_accept_content": self.get_accept_content_list(),
        }

    def validate_configuration(self) -> None:
        """
        Validate the complete configuration with comprehensive checks.
        
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        # Validate broker URL
        try:
            self.validate_broker_url(self.broker_url)
        except ValueError as e:
            errors.append(f"Broker URL validation failed: {e}")
        
        # Validate time limits
        if self.task_soft_time_limit >= self.task_time_limit:
            errors.append(
                f"task_soft_time_limit ({self.task_soft_time_limit}) must be less than "
                f"task_time_limit ({self.task_time_limit})"
            )
        
        # Validate worker settings
        if self.worker_concurrency < 1:
            errors.append(f"worker_concurrency must be at least 1, got {self.worker_concurrency}")
        
        # Validate retry settings
        if self.task_max_retries < 0:
            errors.append(f"task_max_retries must be non-negative, got {self.task_max_retries}")
        
        # Validate queue configuration
        try:
            task_routes = self.get_task_routes_dict()
            if not isinstance(task_routes, dict):
                errors.append("Task routes must be a dictionary")
        except Exception as e:
            errors.append(f"Task routes validation failed: {e}")
        
        # Validate result backend
        if self.result_backend:
            try:
                parsed = urlparse(self.result_backend)
                if not parsed.scheme or not parsed.netloc:
                    errors.append(f"Invalid result backend URL: {self.result_backend}")
            except Exception as e:
                errors.append(f"Result backend URL validation failed: {e}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        logger.info("Celery configuration validation successful")

    def get_configuration_summary(self) -> Dict:
        """
        Get a comprehensive summary of the current configuration.
        
        Returns:
            Dictionary containing configuration summary with masked credentials
        """
        return {
            "broker": {
                "url": self._mask_url_credentials(self.broker_url),
                "connection_retry": self.broker_connection_retry,
                "max_retries": self.broker_connection_max_retries,
            },
            "result_backend": {
                "url": self._mask_url_credentials(self.result_backend or ""),
                "expires": self.result_expires,
                "persistent": self.result_persistent,
            },
            "queues": {
                "default": self.task_default_queue,
                "all_queues": self.get_all_queue_names(),
                "routes_count": len(self.get_task_routes_dict()),
            },
            "worker": {
                "concurrency": self.worker_concurrency,
                "prefetch_multiplier": self.worker_prefetch_multiplier,
                "max_tasks_per_child": self.worker_max_tasks_per_child,
            },
            "tasks": {
                "serializer": self.task_serializer,
                "max_retries": self.task_max_retries,
                "soft_time_limit": self.task_soft_time_limit,
                "time_limit": self.task_time_limit,
            },
            "timezone": {
                "timezone": self.timezone,
                "enable_utc": self.enable_utc,
            }
        }

    def _mask_url_credentials(self, url: str) -> str:
        """Mask credentials in URL for logging/display purposes."""
        if not url:
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