"""
Main application file.
"""
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .api.v1.routes.comments import router as comments_router
from .api.v1.routes.projects import router as projects_router
from .core.constants import V1_PREFIX
from .core.exceptions import (
    APIError,
    api_error_handler,
    general_exception_handler,
    sqlalchemy_error_handler,
    validation_error_handler,
)
from .core.versioning import get_api_version

app = FastAPI(
    title="Project Service",
    description="Project management service for DesignSynapse",
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

# Register error handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routers
app.include_router(
    projects_router,
    prefix=V1_PREFIX,
    dependencies=[Depends(get_api_version)]
)

app.include_router(
    comments_router,
    prefix=V1_PREFIX,
    dependencies=[Depends(get_api_version)]
)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to the Project Service",
        "version": "1.0.0",
        "status": "healthy",
    }