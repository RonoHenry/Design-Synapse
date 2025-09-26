"""
Core application settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Project service specific settings
    MAX_PROJECTS_PER_USER: int = 100
    MAX_PROJECT_NAME_LENGTH: int = 255
    MAX_PROJECT_DESCRIPTION_LENGTH: int = 5000
    ALLOWED_PROJECT_STATUSES: list[str] = [
        "draft",
        "in_progress",
        "review",
        "completed",
        "archived",
    ]

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="APP_", extra="allow"
    )


settings = Settings()