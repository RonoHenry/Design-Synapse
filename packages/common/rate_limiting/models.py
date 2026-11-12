"""Rate limiting data models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class RateLimitStrategy(str, Enum):
    """Rate limiting algorithm strategies."""

    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_window: int
    window_size_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_capacity: Optional[int] = None  # For token bucket
    refill_rate: Optional[float] = None  # For token bucket


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None


class RateLimitStatus(BaseModel):
    """Rate limit status response model."""

    allowed: bool = Field(..., description="Whether the request is allowed")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset_time: datetime = Field(..., description="When the rate limit resets")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


@dataclass
class ClientQuota:
    """Client-specific rate limit quota."""

    client_id: str
    requests_made: int
    window_start: datetime
    last_request: datetime
    tokens: float = 0.0  # For token bucket
    last_refill: Optional[datetime] = None  # For token bucket


class RateLimitHeaders:
    """Standard rate limit HTTP headers."""

    LIMIT = "X-RateLimit-Limit"
    REMAINING = "X-RateLimit-Remaining"
    RESET = "X-RateLimit-Reset"
    RETRY_AFTER = "Retry-After"
