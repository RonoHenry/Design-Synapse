"""Input validation and sanitization for security hardening."""

import html
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from fastapi import Request

from .models import SanitizationResult, ValidationResult


class InputValidator:
    """Validates input against common attack vectors."""

    def __init__(self, max_length: int = 10000):
        self.max_length = max_length

        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\'\s*(OR|AND)\s+\'\w+\'\s*=\s*\'\w+)",
            r"(\bUNION\s+SELECT\b)",
        ]

        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"alert\s*\(",
            r"String\.fromCharCode",
            r"document\.",
            r"window\.",
        ]

        # Command injection patterns
        self.command_patterns = [
            r"[;&|`]",
            r"\$\([^)]*\)",
            r"`[^`]*`",
            r"\|\s*(cat|ls|pwd|whoami|id|uname)",
            r"&&\s*\w+",  # More specific for command chaining
            r";\s*\w+",  # More specific for command separation
        ]

        # Path traversal patterns
        self.path_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"\.\.%2f",
            r"\.\.%5c",
        ]

    async def validate_input(
        self, input_data: str, input_type: str = "text"
    ) -> ValidationResult:
        """Validate input against attack patterns."""
        threats_detected = []
        risk_level = "LOW"

        if not input_data:
            return ValidationResult(
                is_valid=True, threats_detected=[], risk_level="LOW"
            )

        # Check input length
        if len(input_data) > self.max_length:
            threats_detected.append("length_exceeded")
            risk_level = "MEDIUM"

        # Check for SQL injection
        for pattern in self.sql_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                threats_detected.append("sql_injection")
                risk_level = "HIGH"
                break

        # Check for XSS (but not in HTML-escaped content)
        # First check if content is HTML-escaped
        is_html_escaped = (
            "&lt;" in input_data or "&gt;" in input_data or "&amp;" in input_data
        )

        for pattern in self.xss_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                # If content is HTML-escaped, be more lenient with certain patterns
                if is_html_escaped and pattern in [
                    r"on\w+\s*=",
                    r"<iframe[^>]*>",
                    r"<object[^>]*>",
                    r"<embed[^>]*>",
                    r"<link[^>]*>",
                    r"<meta[^>]*>",
                ]:
                    continue  # Skip these patterns for escaped content
                threats_detected.append("xss")
                risk_level = "HIGH"
                break

        # Check for command injection (but not in HTML-escaped content)
        for pattern in self.command_patterns:
            if re.search(pattern, input_data):
                # If content is HTML-escaped, ignore HTML entities
                if is_html_escaped:
                    # Remove HTML entities before checking patterns
                    temp_data = (
                        input_data.replace("&lt;", "")
                        .replace("&gt;", "")
                        .replace("&amp;", "")
                        .replace("&quot;", "")
                        .replace("&#", "")
                    )
                    if not re.search(pattern, temp_data):
                        continue  # Pattern only matched HTML entities
                threats_detected.append("command_injection")
                risk_level = "HIGH"
                break

        # Check for path traversal (for path inputs)
        if input_type in ["path", "file"]:
            for pattern in self.path_patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    threats_detected.append("path_traversal")
                    risk_level = "HIGH"
                    break

        is_valid = len(threats_detected) == 0

        return ValidationResult(
            is_valid=is_valid,
            threats_detected=threats_detected,
            risk_level=risk_level,
            details={"input_length": len(input_data), "input_type": input_type},
        )

    async def validate_request(self, request: Request) -> ValidationResult:
        """Validate entire request for malicious content."""
        all_threats = []
        max_risk_level = "LOW"

        # Validate query parameters
        for key, value in request.query_params.items():
            result = await self.validate_input(str(value), "text")
            if not result.is_valid:
                all_threats.extend(result.threats_detected)
                if result.risk_level == "HIGH":
                    max_risk_level = "HIGH"
                elif result.risk_level == "MEDIUM" and max_risk_level == "LOW":
                    max_risk_level = "MEDIUM"

        # Validate JSON body if present
        try:
            if hasattr(request, "json"):
                body = await request.json()
                if isinstance(body, dict):
                    for key, value in body.items():
                        if isinstance(value, str):
                            result = await self.validate_input(value, "text")
                            if not result.is_valid:
                                all_threats.extend(result.threats_detected)
                                if result.risk_level == "HIGH":
                                    max_risk_level = "HIGH"
                                elif (
                                    result.risk_level == "MEDIUM"
                                    and max_risk_level == "LOW"
                                ):
                                    max_risk_level = "MEDIUM"
        except Exception:
            # If we can't parse JSON, that's suspicious
            all_threats.append("malformed_json")
            max_risk_level = "MEDIUM"

        is_valid = len(all_threats) == 0

        return ValidationResult(
            is_valid=is_valid,
            threats_detected=list(set(all_threats)),  # Remove duplicates
            risk_level=max_risk_level,
        )


class InputSanitizer:
    """Sanitizes input to remove malicious content."""

    def __init__(self):
        # Characters to remove/escape for different contexts
        self.sql_chars = ["'", '"', "--", ";", "/*", "*/"]
        self.html_tags = [
            "script",
            "iframe",
            "object",
            "embed",
            "link",
            "meta",
            "style",
        ]
        self.command_chars = [";", "&", "|", "`", "$"]
        self.path_sequences = ["../", "..\\", "%2e%2e%2f", "%2e%2e%5c"]

    async def sanitize_input(
        self, input_data: str, input_type: str = "text"
    ) -> SanitizationResult:
        """Sanitize input based on type."""
        if not input_data:
            return SanitizationResult(
                sanitized_value="", was_modified=False, modifications=[]
            )

        original_value = input_data
        sanitized_value = input_data
        modifications = []

        if input_type == "html":
            sanitized_value, html_mods = self._sanitize_html(sanitized_value)
            modifications.extend(html_mods)

        elif input_type == "sql":
            sanitized_value, sql_mods = self._sanitize_sql(sanitized_value)
            modifications.extend(sql_mods)

        elif input_type == "path":
            sanitized_value, path_mods = self._sanitize_path(sanitized_value)
            modifications.extend(path_mods)

        elif input_type == "command":
            sanitized_value, cmd_mods = self._sanitize_command(sanitized_value)
            modifications.extend(cmd_mods)

        else:  # General text sanitization
            # Remove common dangerous patterns
            sanitized_value, general_mods = self._sanitize_general(sanitized_value)
            modifications.extend(general_mods)

            # Also apply basic HTML sanitization for text that might contain HTML
            if any(
                char in sanitized_value for char in ["<", ">", "javascript:", "alert("]
            ):
                html_sanitized, html_mods = self._sanitize_html(sanitized_value)
                if html_sanitized != sanitized_value:
                    sanitized_value = html_sanitized
                    modifications.extend(html_mods)

        was_modified = sanitized_value != original_value

        return SanitizationResult(
            sanitized_value=sanitized_value,
            was_modified=was_modified,
            modifications=modifications,
        )

    def _sanitize_html(self, value: str) -> tuple[str, List[str]]:
        """Sanitize HTML content."""
        modifications = []
        original_value = value

        # Remove dangerous tags
        for tag in self.html_tags:
            pattern = f"<{tag}[^>]*>.*?</{tag}>"
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                value = re.sub(pattern, "", value, flags=re.IGNORECASE | re.DOTALL)
                modifications.append(f"removed_{tag}_tag")

        # Remove javascript: URLs
        if "javascript:" in value.lower():
            value = re.sub(r"javascript:[^\"']*", "", value, flags=re.IGNORECASE)
            modifications.append("removed_javascript_url")

        # Remove event handlers
        if re.search(r"on\w+\s*=", value, re.IGNORECASE):
            value = re.sub(
                r"on\w+\s*=\s*[\"'][^\"']*[\"']", "", value, flags=re.IGNORECASE
            )
            modifications.append("removed_event_handlers")

        # Remove dangerous JavaScript patterns
        if re.search(r"alert\s*\(", value, re.IGNORECASE):
            value = re.sub(r"alert\s*\([^)]*\)", "", value, flags=re.IGNORECASE)
            modifications.append("removed_alert_calls")

        if "String.fromCharCode" in value:
            value = re.sub(r"String\.fromCharCode[^;]*", "", value, flags=re.IGNORECASE)
            modifications.append("removed_fromcharcode")

        # Remove JavaScript comments that might be left over
        if "//" in value:
            value = re.sub(r"//.*$", "", value, flags=re.MULTILINE)
            modifications.append("removed_js_comments")

        # Remove remaining dangerous characters that could be used for injection
        dangerous_chars = [";", "&", "|", "`"]
        for char in dangerous_chars:
            if (
                char in value and len(modifications) > 0
            ):  # Only if we already detected threats
                value = value.replace(char, "")
                modifications.append(f"removed_dangerous_char_{char}")

        # Only escape HTML if we detected dangerous content
        if len(modifications) > 0 or any(char in value for char in ["<", ">", "&"]):
            # For legitimate HTML, only escape if it contains dangerous patterns
            safe_tags = ["p", "strong", "em", "b", "i", "u", "br"]
            has_safe_tags_only = True

            # Check if it only contains safe tags
            tag_pattern = r"<(/?)(\w+)[^>]*>"
            tags_found = re.findall(tag_pattern, value, re.IGNORECASE)
            for _, tag in tags_found:
                if tag.lower() not in safe_tags:
                    has_safe_tags_only = False
                    break

            # If it has dangerous content or unsafe tags, escape it
            if not has_safe_tags_only or len(modifications) > 0:
                value = html.escape(value, quote=False)

        return value, modifications

    def _sanitize_sql(self, value: str) -> tuple[str, List[str]]:
        """Sanitize SQL content."""
        modifications = []

        # Remove SQL comments
        if "--" in value or "/*" in value:
            value = re.sub(r"--.*$", "", value, flags=re.MULTILINE)
            value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
            modifications.append("removed_sql_comments")

        # Escape quotes
        if "'" in value or '"' in value:
            value = value.replace("'", "''").replace('"', '""')
            modifications.append("escaped_quotes")

        # Remove dangerous SQL keywords
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "EXEC"]
        for keyword in dangerous_keywords:
            if keyword.lower() in value.lower():
                value = re.sub(rf"\b{keyword}\b", "", value, flags=re.IGNORECASE)
                modifications.append(f"removed_{keyword.lower()}_keyword")

        return value, modifications

    def _sanitize_path(self, value: str) -> tuple[str, List[str]]:
        """Sanitize file path content."""
        modifications = []

        # Remove path traversal sequences
        for sequence in self.path_sequences:
            if sequence in value.lower():
                value = value.replace(sequence, "")
                modifications.append("removed_path_traversal")

        # URL decode and check again
        decoded = urllib.parse.unquote(value)
        if decoded != value:
            value = decoded
            # Check again after decoding
            for sequence in ["../", "..\\"]:
                if sequence in value:
                    value = value.replace(sequence, "")
                    modifications.append("removed_decoded_path_traversal")

        # Normalize path separators
        value = value.replace("\\", "/")

        return value, modifications

    def _sanitize_command(self, value: str) -> tuple[str, List[str]]:
        """Sanitize command content."""
        modifications = []

        # Remove command injection characters
        for char in self.command_chars:
            if char in value:
                value = value.replace(char, "")
                modifications.append(f"removed_command_char_{char}")

        # Remove command substitution
        value = re.sub(r"\$\([^)]*\)", "", value)
        value = re.sub(r"`[^`]*`", "", value)
        if "$(" in value or "`" in value:
            modifications.append("removed_command_substitution")

        return value, modifications

    def _sanitize_general(self, value: str) -> tuple[str, List[str]]:
        """General sanitization for text input."""
        modifications = []

        # Remove null bytes
        if "\x00" in value:
            value = value.replace("\x00", "")
            modifications.append("removed_null_bytes")

        # Remove control characters (except common whitespace)
        control_chars = "".join(chr(i) for i in range(32) if i not in [9, 10, 13])
        for char in control_chars:
            if char in value:
                value = value.replace(char, "")
                modifications.append("removed_control_chars")

        return value, modifications

    async def sanitize_request_data(self, data: Dict[str, Any]) -> SanitizationResult:
        """Sanitize dictionary data from request."""
        sanitized_data = {}
        all_modifications = []
        was_modified = False

        for key, value in data.items():
            if isinstance(value, str):
                # Determine input type based on key name and content
                input_type = "text"
                if "password" in key.lower():
                    input_type = "text"  # Don't sanitize passwords, just validate
                elif (
                    "html" in key.lower()
                    or "content" in key.lower()
                    or "comment" in key.lower()
                ):
                    input_type = "html"
                elif "path" in key.lower() or "file" in key.lower():
                    input_type = "path"
                elif "sql" in key.lower() or "query" in key.lower():
                    input_type = "sql"
                elif "username" in key.lower() or "user" in key.lower():
                    # Username fields often contain SQL injection attempts
                    input_type = "sql"

                result = await self.sanitize_input(value, input_type)
                sanitized_data[key] = result.sanitized_value
                if result.was_modified:
                    was_modified = True
                    all_modifications.extend(
                        [f"{key}:{mod}" for mod in result.modifications]
                    )
            else:
                sanitized_data[key] = value

        return SanitizationResult(
            sanitized_value="",  # Not applicable for dict
            was_modified=was_modified,
            modifications=all_modifications,
            sanitized_data=sanitized_data,
        )
