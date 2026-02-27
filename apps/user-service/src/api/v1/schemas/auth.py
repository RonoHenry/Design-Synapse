"""Request and response models for authentication endpoints."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    """Model for token response."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(
        ...,
        description="JWT access token",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for access token renewal",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwicmVmcmVzaCI6dHJ1ZSwiaWF0IjoxNTE2MjM5MDIyfQ.abc123def456ghi789"
        ],
    )
    token_type: str = Field(
        "bearer", description="Token type, always 'bearer'", examples=["bearer"]
    )
    roles: List[str] = Field(
        ...,
        description="List of user's roles",
        examples=[["admin", "user"], ["user"], ["admin", "moderator"]],
    )


class TokenRefresh(BaseModel):
    """Model for token refresh request."""

    model_config = ConfigDict(from_attributes=True)

    refresh_token: str = Field(
        ...,
        description="The refresh token to use",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwicmVmcmVzaCI6dHJ1ZSwiaWF0IjoxNTE2MjM5MDIyfQ.abc123def456ghi789"
        ],
    )


class TokenResponse(BaseModel):
    """Model for refresh token response."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(
        ...,
        description="New JWT access token",
        examples=[
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        ],
    )
    token_type: str = Field(
        "bearer", description="Token type, always 'bearer'", examples=["bearer"]
    )
    roles: List[str] = Field(
        ...,
        description="List of user's roles",
        examples=[["admin", "user"], ["user"], ["admin", "moderator"]],
    )
