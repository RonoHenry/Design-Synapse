"""Main FastAPI application module."""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add packages to path for shared error handling
packages_path = Path(__file__).parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.errors import register_error_handlers

from .api.v1 import api_router

app = FastAPI(
    title="Knowledge Service",
    description="Service for managing knowledge resources and citations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to the Knowledge Service",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "knowledge-service"}