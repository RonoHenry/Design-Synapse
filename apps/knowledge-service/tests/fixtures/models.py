"""Test fixtures for external service models."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Mock User model for testing."""
    id: int
    username: str
    email: str
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


@dataclass
class Project:
    """Mock Project model for testing."""
    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()