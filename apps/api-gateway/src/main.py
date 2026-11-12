"""
API Gateway main application module.
Provides centralized routing and service discovery for DesignSynapse microservices.
"""

import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors.handlers import register_error_handlers

from .api.v1.routes import gateway, health
from .core.config import get_settings
from .core.exceptions import GatewayError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="DesignSynapse API Gateway",
        description="Centralized API Gateway for DesignSynapse microservices",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    # Include gateway router (must be last to catch all remaining routes)
    app.include_router(gateway.router, tags=["gateway"])

    # Register shared error handlers
    register_error_handlers(app)

    # Additional exception handler for Gateway-specific errors
    @app.exception_handler(GatewayError)
    async def gateway_exception_handler(request: Request, exc: GatewayError):
        """Handle Gateway-specific exceptions."""
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        content = {
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return JSONResponse(status_code=exc.status_code, content=content)

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
