"""User profile model for extended user information."""

import re
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import urlparse

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.infrastructure.database import Base


class UserProfile(Base):
    """User profile model for storing additional user information."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    display_name = Column(String)
    bio = Column(String)
    organization = Column(String)
    phone_number = Column(String)
    location = Column(String)
    social_links = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship with User model
    user = relationship("User", back_populates="profile", uselist=False)

    def __init__(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        organization: Optional[str] = None,
        phone_number: Optional[str] = None,
        location: Optional[str] = None,
        social_links: Optional[Dict[str, str]] = None,
        preferences: Optional[Dict[str, any]] = None,
    ):
        """Initialize a new user profile."""
        self.user_id = user_id
        self.display_name = display_name
        self.bio = bio
        self.organization = organization
        if phone_number:
            self.phone_number = self._validate_phone(phone_number)
        self.location = location
        if social_links:
            self.social_links = self._validate_social_links(social_links)
        self.preferences = preferences
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    @staticmethod
    def _validate_phone(phone: str) -> str:
        """Validate phone number format."""
        # Basic phone validation - should be enhanced based on requirements
        pattern = r"^\+?[\d\-\s]+$"
        if not re.match(pattern, phone) or len(phone) < 10:
            raise ValueError("Invalid phone number format")
        return phone

    @staticmethod
    def _validate_url(url: str) -> str:
        """Validate URL format."""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
        except Exception as e:
            raise ValueError("Invalid URL format") from e
        return url

    def _validate_social_links(self, links: Dict[str, str]) -> Dict[str, str]:
        """Validate social media links."""
        validated = {}
        for platform, url in links.items():
            validated[platform] = self._validate_url(url)
        return validated

    def update_preferences(self, new_preferences: Dict[str, any]) -> None:
        """Update user preferences."""
        self.preferences.update(new_preferences)
        self.updated_at = datetime.now(timezone.utc)
