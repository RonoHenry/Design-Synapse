"""API dependencies for authentication and database access."""
from typing import Optional
from fastapi import Depends, Request

from packages.common.auth.middleware import get_current_user, get_optional_user
from packages.common.auth.models import UserContext

# Re-export auth dependencies for use in routes
__all__ = ["get_current_user", "get_optional_user", "get_user_context"]

async def get_user_context(request: Request) -> Optional[UserContext]:
    """Get user context from request state (set by auth middleware)."""
    return getattr(request.state, "user", None)