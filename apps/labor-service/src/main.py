"""
Labor Services Marketplace FastAPI Application

Main application entry point for the Labor Services Marketplace.
Handles service provider and seeker connections, job matching,
booking management, and payment processing.
"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.handlers import register_error_handlers

from .core.config import get_settings
from .core.database import create_tables, health_check
from .core.exceptions import LaborServiceException

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Labor Services Marketplace...")

    # Create database tables
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Perform health checks
    health_status = await health_check()
    if health_status.get("database") != "healthy":
        logger.error("Database health check failed")
        raise Exception("Database connection failed")

    logger.info("Labor Services Marketplace started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Labor Services Marketplace...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Labor Services Marketplace - Connect skilled professionals with clients",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add middleware
from .api.middleware import (ErrorHandlingMiddleware, RateLimitMiddleware,
                             RequestLoggingMiddleware,
                             SecurityHeadersMiddleware)

# Security and performance middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting (configurable)
if not settings.debug:
    app.add_middleware(RateLimitMiddleware, calls_per_minute=100)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Register shared error handlers
register_error_handlers(app)

# Override validation error handler to match test expectations
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with expected format"""
    return JSONResponse(
        status_code=422, content={"detail": f"Validation error: {str(exc)}"}
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with expected format"""
    return JSONResponse(
        status_code=422, content={"detail": f"Validation error: {str(exc)}"}
    )


# Additional exception handler for Labor Service specific exceptions
@app.exception_handler(LaborServiceException)
async def labor_service_exception_handler(request: Request, exc: LaborServiceException):
    """Handle custom Labor Service exceptions"""
    logger.error(f"Labor Service Exception: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code or "LABOR_SERVICE_ERROR",
            "message": exc.message,
            "detail": exc.details,  # Use 'detail' instead of 'details'
        },
    )


# Health check endpoints
@app.get("/health")
async def health_check_endpoint():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database"""
    health_status = await health_check()
    return {
        "status": "healthy"
        if health_status.get("database") == "healthy"
        else "unhealthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": health_status,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Labor Services Marketplace API",
        "version": settings.app_version,
        "docs": "/docs"
        if settings.debug
        else "Documentation not available in production",
    }


# API routes
from .api.v1.routes import (bookings, matching, providers, quotes, requests,
                            reviews, search)

# Include API routers
app.include_router(providers.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
