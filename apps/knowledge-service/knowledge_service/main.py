"""Main FastAPI application module."""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.common.auth.middleware import AuthMiddleware
from packages.common.rate_limiting.middleware import RateLimitMiddleware
from packages.common.rate_limiting.models import RateLimitConfig, RateLimitStrategy
from packages.common.security.middleware import SecurityHardeningMiddleware
from packages.common.errors.handlers import register_error_handlers
from .core.logging import setup_logging, get_logger
from .middleware import RequestLoggingMiddleware
from .api.v1 import api_router
from .api.error_handlers import register_knowledge_service_error_handlers

# Setup logging first
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Knowledge Service",
    description="Service for managing knowledge resources and citations",
    version="1.0.0",
)

logger.info("Starting Knowledge Service application")

# Register error handlers
register_error_handlers(app)
register_knowledge_service_error_handlers(app)
logger.info("Error handlers registered")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security hardening middleware
app.add_middleware(SecurityHardeningMiddleware)

# Add rate limiting middleware
rate_limit_config = RateLimitConfig(
    requests_per_window=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
    window_size_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "3600")),
    strategy=RateLimitStrategy.SLIDING_WINDOW
)

endpoint_configs = {
    "/api/v1/resources/upload": RateLimitConfig(
        requests_per_window=10,
        window_size_seconds=3600,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    ),
    "/api/v1/resources/upload/batch": RateLimitConfig(
        requests_per_window=5,
        window_size_seconds=3600,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    ),
    "POST": RateLimitConfig(
        requests_per_window=50,
        window_size_seconds=3600,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    )
}

app.add_middleware(
    RateLimitMiddleware,
    default_config=rate_limit_config,
    endpoint_configs=endpoint_configs,
    skip_paths=["/health", "/docs", "/redoc", "/openapi.json", "/api/v1/health"]
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add authentication middleware
app.add_middleware(
    AuthMiddleware,
    secret_key=os.getenv("JWT_SECRET_KEY"),
    service_secret_key=os.getenv("SERVICE_SECRET_KEY"),
    excluded_paths=[
        "/health",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/health"
    ],
    require_auth=True
)

app.include_router(api_router, prefix="/api/v1")

logger.info("Knowledge Service application startup complete")
