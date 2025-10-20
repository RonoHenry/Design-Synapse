"""FastAPI application setup for Design Service."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.database.health import check_database_health
from common.errors import register_error_handlers

# Import routers
from .api.v1.routes import designs, validations, optimizations, files, comments, export
from .core.config import get_settings

app = FastAPI(
    title="Design Service",
    description="AI-powered architectural design generation, validation, and optimization service for DesignSynapse",
    version="1.0.0",
)

# Register error handlers
register_error_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(designs.router, prefix="/api/v1")
app.include_router(validations.router, prefix="/api/v1")
app.include_router(optimizations.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(comments.router)
app.include_router(export.router, prefix="/api/v1")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to the Design Service",
        "version": "1.0.0",
        "status": "healthy",
    }


def check_ai_service_health() -> Dict[str, Any]:
    """
    Check AI service availability.
    
    Returns:
        Dictionary with health status of AI service
    """
    try:
        # Check if OpenAI API key is configured
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            return {
                "healthy": False,
                "message": "AI service unavailable",
                "error": "API key not configured",
            }
        
        # Basic validation that API key looks valid
        if not openai_api_key.startswith("sk-"):
            return {
                "healthy": False,
                "message": "AI service unavailable",
                "error": "Invalid API key format",
            }
        
        # If we get here, basic checks passed
        return {
            "healthy": True,
            "message": "AI service available",
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "message": "AI service check failed",
            "error": str(e),
        }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "design-service",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def readiness_check(response: Response):
    """
    Readiness check endpoint.
    
    Checks database connectivity and AI service availability.
    Returns 200 if all checks pass, 503 if any check fails.
    """
    checks = {}
    all_healthy = True
    
    # Check database connectivity
    try:
        config = get_settings()
        db_url = config.get_database_url()
        ssl_ca = getattr(config.database, 'ssl_ca', None)
        
        db_health = check_database_health(
            connection_url=db_url,
            ssl_ca=ssl_ca,
            timeout=5,
            max_retries=1,
        )
        
        db_check = {
            "healthy": db_health.is_healthy,
            "message": db_health.message,
        }
        
        # Use getattr to safely access optional attributes
        response_time = getattr(db_health, 'response_time_ms', None)
        if response_time is not None:
            db_check["response_time_ms"] = response_time
        
        db_version = getattr(db_health, 'database_version', None)
        if db_version:
            db_check["database_version"] = db_version
        
        ssl_enabled = getattr(db_health, 'ssl_enabled', None)
        if ssl_enabled is not None:
            db_check["ssl_enabled"] = ssl_enabled
        
        if not db_health.is_healthy:
            error = getattr(db_health, 'error', None)
            if error:
                db_check["error"] = error
            all_healthy = False
        
        checks["database"] = db_check
            
    except Exception as e:
        checks["database"] = {
            "healthy": False,
            "message": "Database check failed",
            "error": str(e),
        }
        all_healthy = False
    
    # Check AI service availability
    ai_health = check_ai_service_health()
    checks["ai_service"] = dict(ai_health)  # Convert to dict to avoid any Mock issues
    
    if not ai_health["healthy"]:
        all_healthy = False
    
    # Set response status code
    if not all_healthy:
        response.status_code = 503
        status = "unhealthy"
    else:
        status = "ready"
    
    return {
        "status": status,
        "service": "design-service",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
