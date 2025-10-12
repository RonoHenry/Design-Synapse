"""FastAPI application setup for Design Service."""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.database.health import check_database_health

app = FastAPI(
    title="Design Service",
    description="AI-powered architectural design generation, validation, and optimization service for DesignSynapse",
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


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to the Design Service",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "design-service",
        "version": "1.0.0",
    }


@app.get("/ready")
def readiness_check():
    """Readiness check endpoint."""
    # TODO: Add database connectivity check once database is configured
    return {
        "status": "ready",
        "service": "design-service",
        "version": "1.0.0",
    }
