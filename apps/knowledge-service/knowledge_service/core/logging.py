"""Logging configuration for the Knowledge Service."""
import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Any, Dict

from packages.common.monitoring.models import LogLevel


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "knowledge-service",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = record.endpoint

        if hasattr(record, "method"):
            log_entry["method"] = record.method

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
                "request_id",
                "user_id",
                "endpoint",
                "method",
            ]:
                log_entry[key] = value

        return self._format_json(log_entry)

    def _format_json(self, log_entry: Dict[str, Any]) -> str:
        """Format log entry as JSON."""
        import json

        try:
            return json.dumps(log_entry, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            # Fallback to string representation
            return str(log_entry)


def setup_logging():
    """Setup logging configuration for the Knowledge Service."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "structured")  # structured or simple

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # Set formatter based on configuration
    if log_format == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    configure_service_loggers(log_level)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_format": log_format,
            "service": "knowledge-service",
        },
    )


def configure_service_loggers(log_level: str):
    """Configure loggers for different service components."""
    loggers_config = {
        "knowledge_service": log_level,
        "knowledge_service.api": log_level,
        "knowledge_service.services": log_level,
        "knowledge_service.models": log_level,
        "sqlalchemy.engine": "WARNING",  # Reduce SQL query noise
        "sqlalchemy.pool": "WARNING",
        "uvicorn": "INFO",
        "uvicorn.access": "WARNING",
        "fastapi": "INFO",
        "packages.common": log_level,
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level, logging.INFO))


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record if available."""
        # This would be set by middleware or dependency injection
        # For now, we'll just ensure the filter doesn't block logs
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    response_time_ms: float,
    user_id: str = None,
    request_id: str = None,
    error: str = None,
):
    """Log API request with structured data."""
    logger = get_logger("knowledge_service.api")

    extra_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "request_type": "api_request",
    }

    if user_id:
        extra_data["user_id"] = user_id

    if request_id:
        extra_data["request_id"] = request_id

    if error:
        extra_data["error"] = error

    message = f"{method} {path} - {status_code} ({response_time_ms:.2f}ms)"

    if status_code >= 500:
        logger.error(message, extra=extra_data)
    elif status_code >= 400:
        logger.warning(message, extra=extra_data)
    else:
        logger.info(message, extra=extra_data)


def log_service_operation(
    operation: str,
    service: str,
    success: bool,
    duration_ms: float = None,
    details: Dict[str, Any] = None,
    error: str = None,
):
    """Log service operation with structured data."""
    logger = get_logger(f"knowledge_service.services.{service}")

    extra_data = {
        "operation": operation,
        "service": service,
        "success": success,
        "operation_type": "service_operation",
    }

    if duration_ms is not None:
        extra_data["duration_ms"] = duration_ms

    if details:
        extra_data.update(details)

    if error:
        extra_data["error"] = error

    message = f"{service}.{operation} - {'SUCCESS' if success else 'FAILED'}"
    if duration_ms is not None:
        message += f" ({duration_ms:.2f}ms)"

    if success:
        logger.info(message, extra=extra_data)
    else:
        logger.error(message, extra=extra_data)


def log_database_operation(
    operation: str,
    table: str,
    success: bool,
    duration_ms: float = None,
    record_count: int = None,
    error: str = None,
):
    """Log database operation with structured data."""
    logger = get_logger("knowledge_service.database")

    extra_data = {
        "operation": operation,
        "table": table,
        "success": success,
        "operation_type": "database_operation",
    }

    if duration_ms is not None:
        extra_data["duration_ms"] = duration_ms

    if record_count is not None:
        extra_data["record_count"] = record_count

    if error:
        extra_data["error"] = error

    message = f"DB {operation} on {table} - {'SUCCESS' if success else 'FAILED'}"
    if record_count is not None:
        message += f" ({record_count} records)"
    if duration_ms is not None:
        message += f" ({duration_ms:.2f}ms)"

    if success:
        logger.info(message, extra=extra_data)
    else:
        logger.error(message, extra=extra_data)


# Initialize logging when module is imported
if not logging.getLogger().handlers:
    setup_logging()
