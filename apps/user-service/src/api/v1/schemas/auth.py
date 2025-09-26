"""Request and response models for authentication endpoints."""

from typing import List

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Model for token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(
        ..., description="JWT refresh token for access token renewal"
    )
    token_type: str = Field("bearer", description="Token type, always 'bearer'")
    roles: List[str] = Field(..., description="List of user's roles")


class TokenRefresh(BaseModel):
    """Model for token refresh request."""

    refresh_token: str = Field(..., description="The refresh token to use")


class TokenResponse(BaseModel):
    """Model for refresh token response."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer'")
    roles: List[str] = Field(..., description="List of user's roles")
