"""
Tests for centralized logging infrastructure.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from ..log_aggregator import (LogAggregator, StructuredFormatter,
                              StructuredLogger, get_correlation_id,
                              get_request_id, get_user_id, set_correlation_id,
                              set_request_id, set_user_id)
from ..models import LogEntry, LogFilters, LogLevel


class TestStructuredFormatter:
    """Test structured JSON formatter."""

    def test_format_basic_log(self):
        """Test basic log formatting."""
        formatter = StructuredFormatter("test-service")

        # Create a mock log record
        import logging

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["service"] == "test-service"
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data

    def test_format_with_correlation_id(self):
        """Test log formatting with correlation ID."""
        formatter = StructuredFormatter("test-service")

        # Set correlation context
        set_correlation_id("test-correlation-id")
        set_request_id("test-request-id")
        set_user_id("test-user-id")

        import logging

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["correlation_id"] == "test-correlation-id"
        assert log_data["request_id"] == "test-request-id"
        assert log_data["user_id"] == "test-user-id"


class TestStructuredLogger:
    """Test structured logger functionality."""

    def test_logger_creation(self):
        """Test logger creation and configuration."""
        logger = StructuredLogger("test-service")
        assert logger.service_name == "test-service"
        assert logger.logger is not None

    def test_log_levels(self, structured_logger):
        """Test different log levels."""
        # These should not raise exceptions
        structured_logger.debug("Debug message")
        structured_logger.info("Info message")
        structured_logger.warning("Warning message")
        structured_logger.error("Error message")
        structured_logger.critical("Critical message")

    def test_log_with_metadata(self, structured_logger):
        """Test logging with metadata."""
        # Should not raise exception
        structured_logger.info("Test message", key1="value1", key2="value2")

    def test_log_request(self, structured_logger):
        """Test HTTP request logging."""
        structured_logger.log_request("GET", "/api/test", 200, 150.5)
        # Should not raise exception

    def test_log_error(self, structured_logger):
        """Test error logging with exception."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            structured_logger.log_error(e, {"context": "test"})
        # Should not raise exception


class TestLogAggregator:
    """Test log aggregation functionality."""

    def test_add_log(self, log_aggregator, sample_log_entry):
        """Test adding log entries."""
        log_aggregator.add_log(sample_log_entry)
        assert len(log_aggregator._logs) == 1
        assert log_aggregator._logs[0] == sample_log_entry

    def test_log_rotation(self, log_aggregator):
        """Test log rotation when max logs exceeded."""
        # Set a small max for testing
        log_aggregator._max_logs = 5

        # Add more logs than max
        for i in range(10):
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.INFO,
                service="test-service",
                message=f"Message {i}",
            )
            log_aggregator.add_log(log_entry)

        # Should only keep the last 5 logs
        assert len(log_aggregator._logs) == 5
        assert log_aggregator._logs[-1].message == "Message 9"

    def test_get_logs_no_filters(self, log_aggregator):
        """Test getting logs without filters."""
        # Add test logs
        for i in range(3):
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.INFO,
                service="test-service",
                message=f"Message {i}",
            )
            log_aggregator.add_log(log_entry)

        filters = LogFilters()
        logs = log_aggregator.get_logs(filters)
        assert len(logs) == 3

    def test_get_logs_with_service_filter(self, log_aggregator):
        """Test getting logs filtered by service."""
        # Add logs for different services
        services = ["service-1", "service-2", "service-1"]
        for i, service in enumerate(services):
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.INFO,
                service=service,
                message=f"Message {i}",
            )
            log_aggregator.add_log(log_entry)

        filters = LogFilters(service="service-1")
        logs = log_aggregator.get_logs(filters)
        assert len(logs) == 2
        assert all(log.service == "service-1" for log in logs)

    def test_get_logs_with_level_filter(self, log_aggregator):
        """Test getting logs filtered by level."""
        levels = [LogLevel.INFO, LogLevel.ERROR, LogLevel.INFO]
        for i, level in enumerate(levels):
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=level,
                service="test-service",
                message=f"Message {i}",
            )
            log_aggregator.add_log(log_entry)

        filters = LogFilters(level=LogLevel.ERROR)
        logs = log_aggregator.get_logs(filters)
        assert len(logs) == 1
        assert logs[0].level == LogLevel.ERROR

    def test_get_logs_with_time_filter(self, log_aggregator):
        """Test getting logs filtered by time range."""
        now = datetime.utcnow()
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        # Add logs with different timestamps
        timestamps = [past, now, future]
        for i, timestamp in enumerate(timestamps):
            log_entry = LogEntry(
                timestamp=timestamp,
                level=LogLevel.INFO,
                service="test-service",
                message=f"Message {i}",
            )
            log_aggregator.add_log(log_entry)

        filters = LogFilters(start_time=now, end_time=future)
        logs = log_aggregator.get_logs(filters)
        assert len(logs) == 2  # now and future

    def test_get_logs_by_correlation_id(self, log_aggregator):
        """Test getting logs by correlation ID."""
        correlation_ids = ["corr-1", "corr-2", "corr-1"]
        for i, corr_id in enumerate(correlation_ids):
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=LogLevel.INFO,
                service="test-service",
                message=f"Message {i}",
                correlation_id=corr_id,
            )
            log_aggregator.add_log(log_entry)

        logs = log_aggregator.get_logs_by_correlation_id("corr-1")
        assert len(logs) == 2
        assert all(log.correlation_id == "corr-1" for log in logs)

    def test_get_error_logs(self, log_aggregator):
        """Test getting error logs from recent time period."""
        levels = [LogLevel.INFO, LogLevel.ERROR, LogLevel.WARNING, LogLevel.ERROR]
        for i, level in enumerate(levels):
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=level,
                service="test-service",
                message=f"Message {i}",
            )
            log_aggregator.add_log(log_entry)

        error_logs = log_aggregator.get_error_logs()
        assert len(error_logs) == 2
        assert all(log.level == LogLevel.ERROR for log in error_logs)


class TestCorrelationContext:
    """Test correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        correlation_id = set_correlation_id("test-correlation")
        assert correlation_id == "test-correlation"
        assert get_correlation_id() == "test-correlation"

    def test_auto_generate_correlation_id(self):
        """Test auto-generating correlation ID."""
        correlation_id = set_correlation_id()
        assert correlation_id is not None
        assert len(correlation_id) > 0
        assert get_correlation_id() == correlation_id

    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        request_id = set_request_id("test-request")
        assert request_id == "test-request"
        assert get_request_id() == "test-request"

    def test_set_and_get_user_id(self):
        """Test setting and getting user ID."""
        set_user_id("test-user")
        assert get_user_id() == "test-user"
