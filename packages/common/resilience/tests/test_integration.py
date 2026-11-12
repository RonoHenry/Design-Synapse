"""
Integration tests for resilience patterns working together.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from ..circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from ..retry import retry_with_backoff
