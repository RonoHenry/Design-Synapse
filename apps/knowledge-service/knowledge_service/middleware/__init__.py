"""Middleware package for the Knowledge Service."""

from .logging import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware"]
