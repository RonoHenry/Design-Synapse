"""
Project service models package.

This module provides a clean interface for importing models while avoiding circular dependencies.
"""

# Import models in dependency order
from .project import Project, project_collaborators
from .comment import Comment

# Public API exports
__all__ = [
    "Project",
    "Comment",
    "project_collaborators",
]