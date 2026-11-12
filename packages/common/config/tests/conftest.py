"""Test configuration and fixtures for config management tests."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
            "user": "test_user",
        },
        "redis": {"host": "localhost", "port": 6379, "db": 0},
        "api": {"host": "0.0.0.0", "port": 8000, "debug": False},
    }


@pytest.fixture
def env_vars():
    """Environment variables for testing."""
    return {
        "DATABASE_HOST": "prod-db.example.com",
        "DATABASE_PORT": "5432",
        "DATABASE_PASSWORD": "secret123",
        "REDIS_URL": "redis://prod-redis:6379/0",
        "API_SECRET_KEY": "super-secret-key",
        "ENVIRONMENT": "production",
    }


@pytest.fixture
def mock_env(env_vars):
    """Mock environment variables."""
    original_env = dict(os.environ)
    os.environ.update(env_vars)
    yield
    os.environ.clear()
    os.environ.update(original_env)
