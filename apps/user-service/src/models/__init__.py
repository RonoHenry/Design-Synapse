"""
User service models package.

This module provides a clean interface for importing models while avoiding circular dependencies.
"""

# Import the association table first
from .role import user_roles

# Import models in dependency order
from .role import Role
from .user import User

# Public API exports
__all__ = [
    "User",
    "Role", 
    "user_roles",
]