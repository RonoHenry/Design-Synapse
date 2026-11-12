"""Example usage of the rate limiting system."""

from fastapi import FastAPI, Request

from packages.common.errors import register_error_handlers
from packages.common.rate_limiting import (InMemoryStorage, RateLimitConfig,
                                           RateLimitMiddleware,
                                           RateLimitStrategy)


def create_app_with_rate_limiting():
    """Create FastAPI app with rate limiting configured."""
    app = FastAPI(title="Rate Limited API")

    # Register error handlers
    register_error_handlers(app)

    # Configure rate limiting
    default_config = RateLimitConfig(
        requests_per_window=100,
        window_size_seconds=3600,  # 1 hour
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    )

    # Per-endpoint configurations
    endpoint_configs = {
        # Upload endpoint - strict limits
        "POST:/api/v1/upload": RateLimitConfig(
            requests_per_window=5,
            window_size_seconds=60,  # 1 minute
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            burst_capacity=8,
            refill_rate=0.1,
        ),
        # Search endpoint - moderate limits
        "/api/v1/search": RateLimitConfig(
            requests_per_window=50,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        ),
        # All POST requests - general limits
        "POST": RateLimitConfig(
            requests_per_window=20,
            window_size_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        ),
    }

    # Custom client ID extractor
    def extract_client_id(request: Request) -> str:
        """Extract client ID from request."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Try authenticated user
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        storage=InMemoryStorage(),  # Use Redis in production
        default_config=default_config,
        endpoint_configs=endpoint_configs,
        client_id_extractor=extract_client_id,
        skip_paths=["/health", "/metrics", "/docs", "/openapi.json"],
    )

    # Example endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint (not rate limited)."""
        return {"status": "healthy"}

    @app.get("/api/v1/search")
    async def search_endpoint():
        """Search endpoint with moderate rate limits."""
        return {"results": ["item1", "item2", "item3"]}

    @app.post("/api/v1/upload")
    async def upload_endpoint():
        """Upload endpoint with strict rate limits."""
        return {"message": "File uploaded successfully"}

    @app.get("/api/v1/data")
    async def data_endpoint():
        """General endpoint using default rate limits."""
        return {"data": "some data"}

    return app


# Example with Redis storage (for production)
def create_production_app():
    """Create production app with Redis storage."""
    import redis.asyncio as redis

    from packages.common.rate_limiting import RedisStorage

    app = FastAPI(title="Production Rate Limited API")
    register_error_handlers(app)

    # Redis client
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    # Production rate limiting config
    production_config = RateLimitConfig(
        requests_per_window=1000,
        window_size_seconds=3600,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    )

    app.add_middleware(
        RateLimitMiddleware,
        storage=RedisStorage(redis_client),
        default_config=production_config,
        endpoint_configs={
            "POST:/api/v1/upload": RateLimitConfig(
                requests_per_window=10,
                window_size_seconds=60,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                burst_capacity=15,
                refill_rate=0.2,
            )
        },
    )

    return app


if __name__ == "__main__":
    import uvicorn

    # Create app
    app = create_app_with_rate_limiting()

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)
