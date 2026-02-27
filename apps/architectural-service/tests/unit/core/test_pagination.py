"""Unit tests for pagination functionality."""

import json
import uuid
from datetime import datetime

import pytest
from src.core.pagination import (PaginationCursor, PaginationParams,
                                 create_pagination_params, decode_cursor,
                                 encode_cursor)


class TestPaginationCursor:
    """Unit tests for PaginationCursor."""

    def test_cursor_encode_decode_string(self):
        """Test cursor encoding/decoding with string sort value."""
        sort_value = "test_string"
        item_id = uuid.uuid4()

        cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
        encoded = cursor.encode()

        assert isinstance(encoded, str)
        assert len(encoded) > 0

        decoded = PaginationCursor.decode(encoded)
        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_encode_decode_datetime(self):
        """Test cursor encoding/decoding with datetime sort value."""
        sort_value = datetime(2024, 1, 15, 10, 30, 0)
        item_id = uuid.uuid4()

        cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
        encoded = cursor.encode()

        decoded = PaginationCursor.decode(encoded)
        # Datetime gets serialized as string
        assert str(decoded.sort_value) == str(sort_value)
        assert decoded.id == str(item_id)

    def test_cursor_encode_decode_integer(self):
        """Test cursor encoding/decoding with integer sort value."""
        sort_value = 12345
        item_id = uuid.uuid4()

        cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
        encoded = cursor.encode()

        decoded = PaginationCursor.decode(encoded)
        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_encode_decode_float(self):
        """Test cursor encoding/decoding with float sort value."""
        sort_value = 123.456
        item_id = uuid.uuid4()

        cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
        encoded = cursor.encode()

        decoded = PaginationCursor.decode(encoded)
        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_decode_invalid_base64(self):
        """Test cursor decoding with invalid base64."""
        with pytest.raises(ValueError, match="Invalid cursor format"):
            PaginationCursor.decode("invalid_base64!@#")

    def test_cursor_decode_invalid_json(self):
        """Test cursor decoding with invalid JSON."""
        import base64

        invalid_json = base64.b64encode(b"not json").decode()

        with pytest.raises(ValueError, match="Invalid cursor format"):
            PaginationCursor.decode(invalid_json)

    def test_cursor_decode_missing_fields(self):
        """Test cursor decoding with missing required fields."""
        import base64

        incomplete_data = base64.b64encode(
            json.dumps({"sort_value": "test"}).encode()
        ).decode()

        with pytest.raises(ValueError):
            PaginationCursor.decode(incomplete_data)

    def test_cursor_decode_empty_string(self):
        """Test cursor decoding with empty string."""
        with pytest.raises(ValueError, match="Invalid cursor format"):
            PaginationCursor.decode("")


class TestPaginationParams:
    """Unit tests for PaginationParams."""

    def test_pagination_params_defaults(self):
        """Test PaginationParams with default values."""
        params = PaginationParams()

        assert params.limit == 20
        assert params.cursor is None
        assert params.sort_field == "created_at"
        assert params.sort_direction == "desc"

    def test_pagination_params_custom_values(self):
        """Test PaginationParams with custom values."""
        params = PaginationParams(
            limit=50, cursor="test_cursor", sort_field="name", sort_direction="asc"
        )

        assert params.limit == 50
        assert params.cursor == "test_cursor"
        assert params.sort_field == "name"
        assert params.sort_direction == "asc"

    def test_pagination_params_limit_validation(self):
        """Test PaginationParams limit validation."""
        # Valid limits
        params = PaginationParams(limit=1)
        assert params.limit == 1

        params = PaginationParams(limit=100)
        assert params.limit == 100

        # Invalid limits should raise validation error
        with pytest.raises(ValueError):
            PaginationParams(limit=0)

        with pytest.raises(ValueError):
            PaginationParams(limit=101)

    def test_pagination_params_sort_direction_validation(self):
        """Test PaginationParams sort direction validation."""
        # Valid directions
        params = PaginationParams(sort_direction="asc")
        assert params.sort_direction == "asc"

        params = PaginationParams(sort_direction="desc")
        assert params.sort_direction == "desc"

        # Invalid direction should raise validation error
        with pytest.raises(ValueError):
            PaginationParams(sort_direction="invalid")


class TestPaginationHelpers:
    """Unit tests for pagination helper functions."""

    def test_create_pagination_params_defaults(self):
        """Test create_pagination_params with defaults."""
        params = create_pagination_params()

        assert params.limit == 20
        assert params.cursor is None
        assert params.sort_field == "created_at"
        assert params.sort_direction == "desc"

    def test_create_pagination_params_custom(self):
        """Test create_pagination_params with custom values."""
        params = create_pagination_params(
            limit=30,
            cursor="test_cursor",
            sort_field="updated_at",
            sort_direction="asc",
        )

        assert params.limit == 30
        assert params.cursor == "test_cursor"
        assert params.sort_field == "updated_at"
        assert params.sort_direction == "asc"

    def test_encode_cursor_helper(self):
        """Test encode_cursor helper function."""
        sort_value = "test_value"
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

        # Verify it can be decoded
        decoded = decode_cursor(encoded)
        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_decode_cursor_helper(self):
        """Test decode_cursor helper function."""
        sort_value = 42
        item_id = uuid.uuid4()

        # Create a cursor manually
        cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
        encoded = cursor.encode()

        # Decode using helper
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)


class TestPaginationEdgeCases:
    """Unit tests for pagination edge cases."""

    def test_cursor_with_special_characters(self):
        """Test cursor with special characters in sort value."""
        sort_value = "test with spaces & special chars!@#$%"
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_with_unicode(self):
        """Test cursor with unicode characters."""
        sort_value = "测试 unicode 字符串 🚀"
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_with_very_long_string(self):
        """Test cursor with very long sort value."""
        sort_value = "x" * 1000  # Very long string
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_with_none_values(self):
        """Test cursor behavior with None values."""
        # sort_value can be None in some cases
        sort_value = None
        item_id = uuid.uuid4()

        cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
        encoded = cursor.encode()
        decoded = PaginationCursor.decode(encoded)

        assert decoded.sort_value is None
        assert decoded.id == str(item_id)

    def test_cursor_with_zero_values(self):
        """Test cursor with zero/empty values."""
        # Test with zero
        sort_value = 0
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == 0
        assert decoded.id == str(item_id)

        # Test with empty string
        sort_value = ""
        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == ""
        assert decoded.id == str(item_id)

    def test_cursor_stability(self):
        """Test that cursor encoding is stable (same input = same output)."""
        sort_value = "stable_test"
        item_id = uuid.uuid4()

        encoded1 = encode_cursor(sort_value, item_id)
        encoded2 = encode_cursor(sort_value, item_id)

        assert encoded1 == encoded2

    def test_pagination_params_edge_limits(self):
        """Test pagination params with edge case limits."""
        # Minimum limit
        params = PaginationParams(limit=1)
        assert params.limit == 1

        # Maximum limit
        params = PaginationParams(limit=100)
        assert params.limit == 100

    def test_pagination_params_with_none_optional_fields(self):
        """Test pagination params with None for optional fields."""
        params = PaginationParams(
            limit=25,
            cursor=None,
            sort_field="created_at",  # sort_field is required
            sort_direction="asc",
        )

        assert params.limit == 25
        assert params.cursor is None
        assert params.sort_field == "created_at"
        assert params.sort_direction == "asc"

    def test_cursor_with_datetime_edge_cases(self):
        """Test cursor with datetime edge cases."""
        # Test with epoch time
        sort_value = datetime(1970, 1, 1, 0, 0, 0)
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert str(decoded.sort_value) == str(sort_value)
        assert decoded.id == str(item_id)

        # Test with far future date
        sort_value = datetime(2099, 12, 31, 23, 59, 59)
        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert str(decoded.sort_value) == str(sort_value)
        assert decoded.id == str(item_id)

    def test_cursor_with_large_numbers(self):
        """Test cursor with very large numbers."""
        # Large integer
        sort_value = 9223372036854775807  # Max 64-bit signed int
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

        # Large float
        sort_value = 1.7976931348623157e308  # Close to max float
        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

    def test_cursor_with_negative_numbers(self):
        """Test cursor with negative numbers."""
        # Negative integer
        sort_value = -12345
        item_id = uuid.uuid4()

        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)

        # Negative float
        sort_value = -123.456
        encoded = encode_cursor(sort_value, item_id)
        decoded = decode_cursor(encoded)

        assert decoded.sort_value == sort_value
        assert decoded.id == str(item_id)
