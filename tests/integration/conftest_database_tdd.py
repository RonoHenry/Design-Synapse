"""Pytest configuration for database integration TDD tests."""
import os
import sys

import pytest

# Add the project root to the Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# Import fixtures from the common testing module
from packages.common.testing.database import (DatabaseTestManager,
                                              db_test_manager,
                                              knowledge_db_session,
                                              project_db_session,
                                              user_db_session)

# Re-export fixtures so they're available to tests
__all__ = [
    "db_test_manager",
    "user_db_session",
    "knowledge_db_session",
    "project_db_session",
]
