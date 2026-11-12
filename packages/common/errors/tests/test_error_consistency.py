"""Tests for error response consistency across services."""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..base import (APIError, AuthenticationError, AuthorizationError,
                    CircuitBreakerError, ConflictError, ExternalServiceError,
                    LLMServiceError, NotFoundError, RateLimitError,
                    ServiceUnavailableError, TimeoutError, VectorSearchError)
from ..handlers import register_error_handlers
from ..responses import ErrorType


class TestErrorResponseConsistency:
    """Test consistent error response formats across all error types"""
