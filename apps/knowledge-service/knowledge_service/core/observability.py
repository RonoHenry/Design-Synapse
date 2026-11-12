"""Enhanced observability utilities for the Knowledge Service."""

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from .logging import get_logger, log_service_operation

logger = get_logger(__name__)


class PerformanceMonitor:
    """Utilities for monitoring service performance."""

    @staticmethod
    def track_operation(
        operation_name: str,
        service_name: str = "knowledge-service",
        log_threshold_ms: float = 1000.0,
        include_args: bool = False,
    ):
        """Decorator to track operation performance.

        Args:
            operation_name: Name of the operation
            service_name: Name of the service
            log_threshold_ms: Log warning if operation takes longer than this
            include_args: Whether to include function arguments in logs
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                operation_logger = get_logger(
                    f"knowledge_service.performance.{service_name}"
                )

                # Prepare context data
                context_data = {
                    "operation": operation_name,
                    "service": service_name,
                }

                if include_args:
                    # Safely include arguments (avoid logging sensitive data)
                    safe_args = []
                    for arg in args:
                        if hasattr(arg, "__dict__"):
                            safe_args.append(f"<{type(arg).__name__}>")
                        else:
                            safe_args.append(str(arg)[:100])  # Truncate long strings

                    safe_kwargs = {}
                    for key, value in kwargs.items():
                        if (
                            "password" in key.lower()
                            or "secret" in key.lower()
                            or "token" in key.lower()
                        ):
                            safe_kwargs[key] = "<REDACTED>"
                        elif hasattr(value, "__dict__"):
                            safe_kwargs[key] = f"<{type(value).__name__}>"
                        else:
                            safe_kwargs[key] = str(value)[:100]

                    context_data.update({"args": safe_args, "kwargs": safe_kwargs})

                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000

                    # Log performance metrics
                    log_level = (
                        logging.WARNING
                        if duration_ms > log_threshold_ms
                        else logging.INFO
                    )
                    operation_logger.log(
                        log_level,
                        f"Operation {operation_name} completed in {duration_ms:.2f}ms",
                        extra={
                            **context_data,
                            "duration_ms": duration_ms,
                            "success": True,
                            "slow_operation": duration_ms > log_threshold_ms,
                        },
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    operation_logger.error(
                        f"Operation {operation_name} failed after {duration_ms:.2f}ms: {str(e)}",
                        extra={
                            **context_data,
                            "duration_ms": duration_ms,
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                operation_logger = get_logger(
                    f"knowledge_service.performance.{service_name}"
                )

                # Prepare context data (same as async version)
                context_data = {
                    "operation": operation_name,
                    "service": service_name,
                }

                if include_args:
                    safe_args = []
                    for arg in args:
                        if hasattr(arg, "__dict__"):
                            safe_args.append(f"<{type(arg).__name__}>")
                        else:
                            safe_args.append(str(arg)[:100])

                    safe_kwargs = {}
                    for key, value in kwargs.items():
                        if (
                            "password" in key.lower()
                            or "secret" in key.lower()
                            or "token" in key.lower()
                        ):
                            safe_kwargs[key] = "<REDACTED>"
                        elif hasattr(value, "__dict__"):
                            safe_kwargs[key] = f"<{type(value).__name__}>"
                        else:
                            safe_kwargs[key] = str(value)[:100]

                    context_data.update({"args": safe_args, "kwargs": safe_kwargs})

                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000

                    # Log performance metrics
                    log_level = (
                        logging.WARNING
                        if duration_ms > log_threshold_ms
                        else logging.INFO
                    )
                    operation_logger.log(
                        log_level,
                        f"Operation {operation_name} completed in {duration_ms:.2f}ms",
                        extra={
                            **context_data,
                            "duration_ms": duration_ms,
                            "success": True,
                            "slow_operation": duration_ms > log_threshold_ms,
                        },
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    operation_logger.error(
                        f"Operation {operation_name} failed after {duration_ms:.2f}ms: {str(e)}",
                        extra={
                            **context_data,
                            "duration_ms": duration_ms,
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    raise

            # Return appropriate wrapper based on function type
            if (
                hasattr(func, "__code__") and func.__code__.co_flags & 0x80
            ):  # CO_COROUTINE
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


class ResourceMetrics:
    """Utilities for tracking resource usage metrics."""

    @staticmethod
    def track_resource_usage(resource_type: str, operation: str = "process"):
        """Decorator to track resource usage metrics.

        Args:
            resource_type: Type of resource being processed
            operation: Operation being performed
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                metrics_logger = get_logger("knowledge_service.metrics")
                start_time = time.time()

                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000

                    # Log resource metrics
                    metrics_logger.info(
                        f"Resource {operation} completed",
                        extra={
                            "resource_type": resource_type,
                            "operation": operation,
                            "duration_ms": duration_ms,
                            "success": True,
                            "metric_type": "resource_processing",
                        },
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_logger.error(
                        f"Resource {operation} failed",
                        extra={
                            "resource_type": resource_type,
                            "operation": operation,
                            "duration_ms": duration_ms,
                            "success": False,
                            "error": str(e),
                            "metric_type": "resource_processing",
                        },
                    )
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                metrics_logger = get_logger("knowledge_service.metrics")
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000

                    # Log resource metrics
                    metrics_logger.info(
                        f"Resource {operation} completed",
                        extra={
                            "resource_type": resource_type,
                            "operation": operation,
                            "duration_ms": duration_ms,
                            "success": True,
                            "metric_type": "resource_processing",
                        },
                    )

                    return result

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_logger.error(
                        f"Resource {operation} failed",
                        extra={
                            "resource_type": resource_type,
                            "operation": operation,
                            "duration_ms": duration_ms,
                            "success": False,
                            "error": str(e),
                            "metric_type": "resource_processing",
                        },
                    )
                    raise

            # Return appropriate wrapper based on function type
            if (
                hasattr(func, "__code__") and func.__code__.co_flags & 0x80
            ):  # CO_COROUTINE
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


@contextmanager
def operation_span(
    operation_name: str, service_name: str = "knowledge-service", **span_attributes
):
    """Context manager for creating operation spans with structured logging.

    Args:
        operation_name: Name of the operation
        service_name: Name of the service
        **span_attributes: Additional attributes for the span
    """
    span_logger = get_logger(f"knowledge_service.spans.{service_name}")
    start_time = time.time()

    span_context = {
        "operation": operation_name,
        "service": service_name,
        "span_id": f"{operation_name}_{int(start_time * 1000)}",
        **span_attributes,
    }

    try:
        span_logger.info(
            f"Starting span: {operation_name}",
            extra={**span_context, "span_event": "start"},
        )

        yield span_context

        duration_ms = (time.time() - start_time) * 1000
        span_logger.info(
            f"Completed span: {operation_name}",
            extra={
                **span_context,
                "span_event": "end",
                "duration_ms": duration_ms,
                "success": True,
            },
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        span_logger.error(
            f"Failed span: {operation_name}",
            extra={
                **span_context,
                "span_event": "error",
                "duration_ms": duration_ms,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise


def log_business_event(
    event_name: str,
    event_data: Dict[str, Any],
    user_id: Optional[str] = None,
    resource_id: Optional[int] = None,
):
    """Log business events for analytics and monitoring.

    Args:
        event_name: Name of the business event
        event_data: Data associated with the event
        user_id: Optional user ID
        resource_id: Optional resource ID
    """
    business_logger = get_logger("knowledge_service.business_events")

    log_data = {
        "event_name": event_name,
        "event_type": "business_event",
        "timestamp": time.time(),
        **event_data,
    }

    if user_id:
        log_data["user_id"] = user_id

    if resource_id:
        log_data["resource_id"] = resource_id

    business_logger.info(f"Business event: {event_name}", extra=log_data)


def log_security_event(
    event_name: str,
    event_data: Dict[str, Any],
    severity: str = "info",
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Log security events for monitoring and alerting.

    Args:
        event_name: Name of the security event
        event_data: Data associated with the event
        severity: Severity level (info, warning, error, critical)
        user_id: Optional user ID
        ip_address: Optional IP address
    """
    security_logger = get_logger("knowledge_service.security_events")

    log_data = {
        "event_name": event_name,
        "event_type": "security_event",
        "severity": severity,
        "timestamp": time.time(),
        **event_data,
    }

    if user_id:
        log_data["user_id"] = user_id

    if ip_address:
        log_data["ip_address"] = ip_address

    # Map severity to log level
    log_level_map = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    log_level = log_level_map.get(severity.lower(), logging.INFO)

    security_logger.log(log_level, f"Security event: {event_name}", extra=log_data)
