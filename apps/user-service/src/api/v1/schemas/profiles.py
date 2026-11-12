"""Schema definitions for user profile API endpoints."""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr


class UserProfileBase(BaseModel):
    """Base model for user profile data."""

    display_name: Optional[str] = None
    bio: Optional[str] = None
    organization: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    preferences: Optional[Dict] = None
    social_links: Optional[Dict] = None


class UserProfileUpdate(UserProfileBase):
    """Model for updating a user profile."""

    pass


class UserProfileResponse(UserProfileBase):
    """Response model for user profile data."""

    id: int
    user_id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class UserProfilePreferencesUpdate(BaseModel):
    """Model for updating user preferences."""

    preferences: Dict
