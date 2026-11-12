"""
Vendor Product Service - Main Application Entry Point

This service provides marketplace functionality for the DesignSynapse platform,
enabling vendors to manage product catalogs and customers to discover, compare,
and order construction materials and services with project staging capabilities.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.error_handlers import get_error_handlers
from src.api.v1.routes import (health, orders, products, reviews, staging,
                               vendors)
from src.core.config import get_settings
from src.core.database import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Vendor Product Service...")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Vendor Product Service...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="Vendor Product Service",
        description="Marketplace functionality with product staging capabilities for DesignSynapse",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add error handlers
    error_handlers = get_error_handlers()
    for exception_type, handler in error_handlers.items():
        app.add_exception_handler(exception_type, handler)

    # Include API routes
    app.include_router(health.router, tags=["health"])
    app.include_router(vendors.router, prefix="/api/v1/vendors", tags=["vendors"])
    app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
    app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
    app.include_router(staging.router, prefix="/api/v1", tags=["staging"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "vendor-product-service"}

    return app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info",
    )
