"""Unit tests for logging configuration."""

import logging
from unittest.mock import patch

import pytest
from src.core.logging import CustomJsonFormatter, get_logger, setup_logging


@pytest.mark.unit
class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_setup_logging_configures_root_logger(self):
        """Test that setup_logging configures the root logger."""
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level in [logging.DEBUG, logging.INFO]
        assert len(root_logger.handlers) > 0

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_returns_different_loggers_for_different_names(self):
        """Test that different names return different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_custom_json_formatter_adds_service_fields(self):
        """Test that CustomJsonFormatter adds service fields."""
        formatter = CustomJsonFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format the record
        formatted = formatter.format(record)

        # Check that it's valid JSON-like string
        assert isinstance(formatted, str)
        assert "service" in formatted or "Engineering Service" in formatted

    def test_logging_works_in_debug_mode(self):
        """Test that logging works in debug mode."""
        with patch("src.core.logging.settings") as mock_settings:
            mock_settings.debug = True
            mock_settings.environment = "development"
            mock_settings.app_name = "Test Service"

            setup_logging()
            logger = get_logger("test")

            # Should not raise any exceptions
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")

    def test_logging_works_in_production_mode(self):
        """Test that logging works in production mode."""
        with patch("src.core.logging.settings") as mock_settings:
            mock_settings.debug = False
            mock_settings.environment = "production"
            mock_settings.app_name = "Test Service"

            setup_logging()
            logger = get_logger("test")

            # Should not raise any exceptions
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
