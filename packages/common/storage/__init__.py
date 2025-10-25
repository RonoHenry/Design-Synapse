"""
Common storage utilities for file upload and management.

This package provides storage clients for different cloud providers
with a unified interface for file operations.
"""

from .client import StorageClient

__all__ = ["StorageClient"]