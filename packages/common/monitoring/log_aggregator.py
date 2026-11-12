"""
Centralized logging infrastructure with structured formatting and correlation IDs.
"""

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional

from packages.common.monitoring.models import LogEntry, LogFilters, LogLevel

# Context variables for request correlation
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel(record.levelname),
            service=self.service_name,
            message=record.getMessage(),
            request_id=request_id_var.get(),
            user_id=user_id_var.get(),
            correlation_id=correlation_id_var.get(),
            metadata=getattr(record, "metadata", {}),
        )

        return json.dumps(log_entry.to_dict(), default=str)


class StructuredLogger:
    """Structured logger with correlation ID support."""

    def __init__(self, service_name: str, logger_name: str = None):
        self.service_name = service_name
        self.logger = logging.getLogger(logger_name or service_name)

        # Configure structured formatter
        handler = logging.StreamHandler()
        formatter = StructuredFormatter(service_name)
        handler.setFormatter(formatter)

        # Only add handler if not already configured
        if not self.logger.handlers:
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _log(self, level: LogLevel, message: str, **metadata):
        """Internal logging method with metadata support."""
        # Create a log record with metadata
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=getattr(logging, level.value),
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        record.metadata = metadata
        self.logger.handle(record)

    def debug(self, message: str, **metadata):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **metadata)

    def info(self, message: str, **metadata):
        """Log info message."""
        self._log(LogLevel.INFO, message, **metadata)

    def warning(self, message: str, **metadata):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **metadata)

    def error(self, message: str, **metadata):
        """Log error message."""
        self._log(LogLevel.ERROR, message, **metadata)

    def critical(self, message: str, **metadata):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, **metadata)

    def log_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Log HTTP request with standard format."""
        self.info(
            f"{method} {path} - {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            event_type="http_request",
        )

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with exception details."""
        self.error(
            f"Error: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
            event_type="error",
        )


class LogAggregator:
    """Centralized log aggregation and search."""

    def __init__(self):
        self._logs: List[LogEntry] = []
        self._max_logs = 10000  # Keep last 10k logs in memory

    def add_log(self, log_entry: LogEntry):
        """Add a log entry to the aggregator."""
        self._logs.append(log_entry)

        # Rotate logs if we exceed max
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs :]

    def get_logs(self, filters: LogFilters) -> List[LogEntry]:
        """Get logs matching the specified filters."""
        filtered_logs = self._logs

        # Apply filters
        if filters.service:
            filtered_logs = [
                log for log in filtered_logs if log.service == filters.service
            ]

        if filters.level:
            filtered_logs = [log for log in filtered_logs if log.level == filters.level]

        if filters.start_time:
            filtered_logs = [
                log for log in filtered_logs if log.timestamp >= filters.start_time
            ]

        if filters.end_time:
            filtered_logs = [
                log for log in filtered_logs if log.timestamp <= filters.end_time
            ]

        if filters.request_id:
            filtered_logs = [
                log for log in filtered_logs if log.request_id == filters.request_id
            ]

        if filters.user_id:
            filtered_logs = [
                log for log in filtered_logs if log.user_id == filters.user_id
            ]

        if filters.correlation_id:
            filtered_logs = [
                log
                for log in filtered_logs
                if log.correlation_id == filters.correlation_id
            ]

        # Sort by timestamp (newest first) and apply limit
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_logs[: filters.limit]

    def get_logs_by_correlation_id(self, correlation_id: str) -> List[LogEntry]:
        """Get all logs for a specific correlation ID."""
        return [log for log in self._logs if log.correlation_id == correlation_id]

    def get_error_logs(self, service: str = None, hours: int = 24) -> List[LogEntry]:
        """Get error logs from the last N hours."""
        start_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - hours)
        filters = LogFilters(
            service=service, level=LogLevel.ERROR, start_time=start_time, limit=1000
        )
        return self.get_logs(filters)


def set_correlation_id(correlation_id: str = None) -> str:
    """Set correlation ID for current context."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def set_request_id(request_id: str = None) -> str:
    """Set request ID for current context."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def set_user_id(user_id: str):
    """Set user ID for current context."""
    user_id_var.set(user_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get current user ID."""
    return user_id_var.get()


# Global log aggregator instance
_log_aggregator = LogAggregator()


def get_logger(service_name: str, logger_name: str = None) -> StructuredLogger:
    """Get a structured logger for a service."""
    return StructuredLogger(service_name, logger_name)


def get_log_aggregator() -> LogAggregator:
    """Get the global log aggregator instance."""
    return _log_aggregator
