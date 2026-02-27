"""
Input validation utilities for Labor Services Marketplace API

Provides common validation functions for API inputs,
sanitization, and security checks.
"""

import re
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status
from pydantic import BaseModel, validator


class ValidationError(Exception):
    """Custom validation error."""

    pass


def validate_email(email: str) -> str:
    """Validate email format."""
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format")
    return email.lower().strip()


def validate_phone(phone: str) -> str:
    """Validate phone number format."""
    # Remove all non-digit characters
    digits_only = re.sub(r"\D", "", phone)

    # Check if it's a valid length (10-15 digits)
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError("Phone number must be 10-15 digits")

    return digits_only


def validate_postal_code(postal_code: str, country: str = "US") -> str:
    """Validate postal code format based on country."""
    postal_code = postal_code.strip().upper()

    if country == "US":
        # US ZIP code: 12345 or 12345-6789
        if not re.match(r"^\d{5}(-\d{4})?$", postal_code):
            raise ValidationError("Invalid US ZIP code format")
    elif country == "CA":
        # Canadian postal code: A1A 1A1
        if not re.match(r"^[A-Z]\d[A-Z] \d[A-Z]\d$", postal_code):
            raise ValidationError("Invalid Canadian postal code format")

    return postal_code


def validate_coordinates(latitude: float, longitude: float) -> tuple:
    """Validate geographic coordinates."""
    if not (-90 <= latitude <= 90):
        raise ValidationError("Latitude must be between -90 and 90")

    if not (-180 <= longitude <= 180):
        raise ValidationError("Longitude must be between -180 and 180")

    return latitude, longitude


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize text input by removing potentially harmful content."""
    if not text:
        return ""

    # Strip whitespace
    text = text.strip()

    # Check length
    if len(text) > max_length:
        raise ValidationError(f"Text exceeds maximum length of {max_length} characters")

    # Remove potentially harmful patterns
    # Remove script tags
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove javascript: URLs
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

    # Remove on* event handlers
    text = re.sub(r"\bon\w+\s*=", "", text, flags=re.IGNORECASE)

    return text


def validate_rating(rating: Union[int, float]) -> float:
    """Validate rating value (1-5 scale)."""
    try:
        rating = float(rating)
    except (ValueError, TypeError):
        raise ValidationError("Rating must be a number")

    if not (1 <= rating <= 5):
        raise ValidationError("Rating must be between 1 and 5")

    return round(rating, 1)


def validate_price(price: Union[int, float]) -> float:
    """Validate price value."""
    try:
        price = float(price)
    except (ValueError, TypeError):
        raise ValidationError("Price must be a number")

    if price < 0:
        raise ValidationError("Price cannot be negative")

    if price > 1000000:  # $1M limit
        raise ValidationError("Price exceeds maximum allowed value")

    return round(price, 2)


def validate_date_range(start_date: str, end_date: str) -> tuple:
    """Validate date range."""
    from datetime import datetime

    try:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(
            "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
        )

    if start >= end:
        raise ValidationError("Start date must be before end date")

    return start, end


def validate_skill_level(level: str) -> str:
    """Validate skill proficiency level."""
    valid_levels = ["beginner", "intermediate", "advanced", "expert"]
    level = level.lower().strip()

    if level not in valid_levels:
        raise ValidationError(f"Skill level must be one of: {', '.join(valid_levels)}")

    return level


def validate_urgency_level(urgency: str) -> str:
    """Validate request urgency level."""
    valid_urgencies = ["low", "normal", "high", "urgent", "emergency"]
    urgency = urgency.lower().strip()

    if urgency not in valid_urgencies:
        raise ValidationError(f"Urgency must be one of: {', '.join(valid_urgencies)}")

    return urgency


class BaseValidationSchema(BaseModel):
    """Base schema with common validation methods."""

    @validator("*", pre=True)
    def sanitize_strings(cls, v):
        """Sanitize all string inputs."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        str_strip_whitespace = True
        anystr_lower = False  # Don't auto-lowercase all strings


def validate_api_input(
    data: Dict[str, Any], required_fields: List[str]
) -> Dict[str, Any]:
    """Validate API input data."""
    # Check required fields
    missing_fields = [
        field for field in required_fields if field not in data or data[field] is None
    ]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required fields: {', '.join(missing_fields)}",
        )

    # Sanitize string values
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            try:
                sanitized_data[key] = sanitize_text(value)
            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid value for field '{key}': {str(e)}",
                )
        else:
            sanitized_data[key] = value

    return sanitized_data
