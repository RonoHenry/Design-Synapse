"""
Request and response models for authentication.
"""
from typing import List

from pydantic import BaseModel, Field, ConfigDict


class Token(BaseModel):
    """Model for token response."""
    
    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(
        ..., description="JWT refresh token for obtaining new access tokens"
    )
    token_type: str = Field("bearer", description="Token type, always 'bearer'")
    roles: List[str] = Field(..., description="List of user's roles")


class TokenRefresh(BaseModel):
    """Model for token refresh request."""
    
    model_config = ConfigDict(from_attributes=True)

    refresh_token: str = Field(..., description="The refresh token to use")


class TokenResponse(BaseModel):
    """Model for refresh token response."""
    
    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer'")
    roles: List[str] = Field(..., description="List of user's roles")
