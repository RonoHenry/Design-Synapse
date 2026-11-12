"""Tests for input validation and sanitization - RED phase (failing tests)."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request

from packages.common.security.input_validation import (InputSanitizer,
                                                       InputValidator)
from packages.common.security.models import (SanitizationResult,
                                             ValidationResult)


class TestInputValidator:
    """Test input validation against injection attacks."""

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self, malicious_payloads):
        """Test detection of SQL injection attempts."""
        validator = InputValidator()

        for payload in malicious_payloads["sql_injection"]:
            result = await validator.validate_input(payload, "text")
            assert not result.is_valid
            assert "sql_injection" in result.threats_detected
            assert result.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_xss_detection(self, malicious_payloads):
        """Test detection of XSS attempts."""
        validator = InputValidator()

        for payload in malicious_payloads["xss"]:
            result = await validator.validate_input(payload, "text")
            assert not result.is_valid
            assert "xss" in result.threats_detected
            assert result.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_command_injection_detection(self, malicious_payloads):
        """Test detection of command injection attempts."""
        validator = InputValidator()

        for payload in malicious_payloads["command_injection"]:
            result = await validator.validate_input(payload, "text")
            assert not result.is_valid
            assert "command_injection" in result.threats_detected
            assert result.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_path_traversal_detection(self, malicious_payloads):
        """Test detection of path traversal attempts."""
        validator = InputValidator()

        for payload in malicious_payloads["path_traversal"]:
            result = await validator.validate_input(payload, "path")
            assert not result.is_valid
            assert "path_traversal" in result.threats_detected
            assert result.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_valid_input_passes(self):
        """Test that valid input passes validation."""
        validator = InputValidator()

        valid_inputs = [
            "normal text",
            "user@example.com",
            "123456",
            "valid-filename.txt",
        ]

        for input_data in valid_inputs:
            result = await validator.validate_input(input_data, "text")
            assert result.is_valid
            assert len(result.threats_detected) == 0
            assert result.risk_level == "LOW"

    @pytest.mark.asyncio
    async def test_input_length_validation(self):
        """Test input length validation."""
        validator = InputValidator(max_length=10)

        # Valid length
        result = await validator.validate_input("short", "text")
        assert result.is_valid

        # Invalid length
        result = await validator.validate_input("this is too long", "text")
        assert not result.is_valid
        assert "length_exceeded" in result.threats_detected

    @pytest.mark.asyncio
    async def test_request_validation(self):
        """Test full request validation."""
        validator = InputValidator()

        # Mock request with malicious data
        request = Mock()
        request.json = AsyncMock(
            return_value={
                "username": "admin'--",
                "comment": "<script>alert('xss')</script>",
            }
        )
        request.query_params = {"search": "; rm -rf /"}

        result = await validator.validate_request(request)
        assert not result.is_valid
        assert len(result.threats_detected) >= 3  # SQL, XSS, Command injection


class TestInputSanitizer:
    """Test input sanitization functionality."""

    @pytest.mark.asyncio
    async def test_html_sanitization(self, malicious_payloads):
        """Test HTML/XSS sanitization."""
        sanitizer = InputSanitizer()

        for payload in malicious_payloads["xss"]:
            result = await sanitizer.sanitize_input(payload, "html")
            assert result.sanitized_value != payload
            assert "<script>" not in result.sanitized_value
            assert "javascript:" not in result.sanitized_value
            assert result.was_modified

    @pytest.mark.asyncio
    async def test_sql_sanitization(self, malicious_payloads):
        """Test SQL injection sanitization."""
        sanitizer = InputSanitizer()

        for payload in malicious_payloads["sql_injection"]:
            result = await sanitizer.sanitize_input(payload, "sql")
            assert result.sanitized_value != payload
            assert "--" not in result.sanitized_value
            assert "DROP" not in result.sanitized_value.upper()
            assert result.was_modified

    @pytest.mark.asyncio
    async def test_path_sanitization(self, malicious_payloads):
        """Test path traversal sanitization."""
        sanitizer = InputSanitizer()

        for payload in malicious_payloads["path_traversal"]:
            result = await sanitizer.sanitize_input(payload, "path")
            assert result.sanitized_value != payload
            assert "../" not in result.sanitized_value
            assert "..\\" not in result.sanitized_value
            assert result.was_modified

    @pytest.mark.asyncio
    async def test_command_sanitization(self, malicious_payloads):
        """Test command injection sanitization."""
        sanitizer = InputSanitizer()

        for payload in malicious_payloads["command_injection"]:
            result = await sanitizer.sanitize_input(payload, "command")
            assert result.sanitized_value != payload
            assert ";" not in result.sanitized_value
            assert "|" not in result.sanitized_value
            assert "&" not in result.sanitized_value
            assert result.was_modified

    @pytest.mark.asyncio
    async def test_clean_input_unchanged(self):
        """Test that clean input remains unchanged."""
        sanitizer = InputSanitizer()

        clean_inputs = [
            "normal text",
            "user@example.com",
            "valid-filename.txt",
            "123456",
        ]

        for input_data in clean_inputs:
            result = await sanitizer.sanitize_input(input_data, "text")
            assert result.sanitized_value == input_data
            assert not result.was_modified

    @pytest.mark.asyncio
    async def test_request_sanitization(self):
        """Test full request sanitization."""
        sanitizer = InputSanitizer()

        # Mock request with malicious data
        request_data = {
            "username": "admin'--",
            "comment": "<script>alert('xss')</script>",
            "file_path": "../../../etc/passwd",
        }

        result = await sanitizer.sanitize_request_data(request_data)
        assert result.sanitized_data["username"] != request_data["username"]
        assert result.sanitized_data["comment"] != request_data["comment"]
        assert result.sanitized_data["file_path"] != request_data["file_path"]
        assert result.was_modified
        assert (
            len(result.modifications) >= 3
        )  # At least 3 modifications (could be more due to multiple patterns)


class TestInputValidationIntegration:
    """Test integration between validation and sanitization."""

    @pytest.mark.asyncio
    async def test_validate_then_sanitize_workflow(self, malicious_payloads):
        """Test the validate-then-sanitize workflow."""
        validator = InputValidator()
        sanitizer = InputSanitizer()

        for payload in malicious_payloads["xss"]:
            # First validate
            validation_result = await validator.validate_input(payload, "html")
            assert not validation_result.is_valid

            # Then sanitize
            sanitization_result = await sanitizer.sanitize_input(payload, "html")
            assert sanitization_result.was_modified

            # Validate sanitized input should pass
            clean_validation = await validator.validate_input(
                sanitization_result.sanitized_value, "html"
            )
            assert clean_validation.is_valid

    @pytest.mark.asyncio
    async def test_sanitize_preserves_functionality(self):
        """Test that sanitization preserves legitimate functionality."""
        sanitizer = InputSanitizer()

        # Legitimate HTML that should be preserved
        legitimate_html = "<p>This is <strong>bold</strong> text</p>"
        result = await sanitizer.sanitize_input(legitimate_html, "html")

        # Should preserve basic formatting tags
        assert "<p>" in result.sanitized_value
        assert "<strong>" in result.sanitized_value
        assert "bold" in result.sanitized_value

    @pytest.mark.asyncio
    async def test_performance_with_large_input(self):
        """Test validation/sanitization performance with large inputs."""
        validator = InputValidator()
        sanitizer = InputSanitizer()

        # Large input (10KB)
        large_input = "a" * 10000

        import time

        start_time = time.time()

        validation_result = await validator.validate_input(large_input, "text")
        sanitization_result = await sanitizer.sanitize_input(large_input, "text")

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process within reasonable time (< 1 second)
        assert processing_time < 1.0
        assert validation_result.is_valid
        assert not sanitization_result.was_modified
