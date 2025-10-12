"""API router for knowledge service."""
import sys
from pathlib import Path

from fastapi import APIRouter

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.database.health import check_database_health

from ...core.config import settings
from .resources import router as resources_router
from .citations import router as citations_router
from .search import router as search_router

api_router = APIRouter()

# Include sub-routers
api_router.include_router(resources_router, prefix="/resources", tags=["resources"])
api_router.include_router(citations_router, prefix="/citations", tags=["citations"])
api_router.include_router(search_router, prefix="/search", tags=["search"])

@api_router.get("/health")
def health_check():
    """Health check endpoint with database connectivity check."""
    # Check database connectivity
    db_health = check_database_health(
        connection_url=settings.get_database_url(),
        ssl_ca=settings.database.ssl_ca,
        ssl_verify_cert=settings.database.ssl_verify_cert,
        ssl_verify_identity=settings.database.ssl_verify_identity,
    )
    
    return {
        "status": "healthy" if db_health.is_healthy else "degraded",
        "version": "1.0.0",
        "database": {
            "status": "connected" if db_health.is_healthy else "disconnected",
            "response_time_ms": db_health.response_time_ms,
            "version": db_health.database_version,
            "ssl_enabled": db_health.ssl_enabled,
            "error": db_health.error,
        },
    }