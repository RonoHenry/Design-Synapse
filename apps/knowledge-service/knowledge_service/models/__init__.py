"""
Knowledge service models package.

This module provides a clean interface for importing models while avoiding circular dependencies.
"""

# Import association tables first
from .resource import resource_topics

# Import models in dependency order
from .resource import Resource, Topic, Citation
from .bookmark import Bookmark

# Public API exports
__all__ = [
    "Resource",
    "Topic", 
    "Citation",
    "Bookmark",
    "resource_topics",
]