"""FastAPI application setup for User Service."""

import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.database.health import check_database_health
# Import shared error handlers
from common.errors.handlers import register_error_handlers

from .api.v1 import auth, health, roles
from .core.config import settings
from .core.constants import V1_PREFIX
from .core.versioning import get_api_version

app = FastAPI(
    title="User Service",
    description="User authentication and management service for DesignSynapse",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register shared error handlers
register_error_handlers(app)

# Register routers with versioning
app.include_router(
    auth.router, prefix=V1_PREFIX, dependencies=[Depends(get_api_version)]
)
app.include_router(
    roles.router, prefix=V1_PREFIX, dependencies=[Depends(get_api_version)]
)
app.include_router(
    health.router,
    prefix=V1_PREFIX,
    dependencies=[Depends(get_api_version)],
    tags=["health"],
)


@app.get("/")
def read_root():
    """Root endpoint with database health check."""
    # Check database connectivity
    db_health = check_database_health(
        connection_url=settings.get_database_url(),
        ssl_ca=settings.database.ssl_ca,
        ssl_verify_cert=settings.database.ssl_verify_cert,
        ssl_verify_identity=settings.database.ssl_verify_identity,
    )

    return {
        "message": "Welcome to the User Service",
        "version": "1.0.0",
        "status": "healthy" if db_health.is_healthy else "degraded",
        "database": {
            "status": "connected" if db_health.is_healthy else "disconnected",
            "response_time_ms": db_health.response_time_ms,
            "version": db_health.database_version,
            "ssl_enabled": db_health.ssl_enabled,
            "error": db_health.error,
        },
    }
