"""FastAPI application setup for User Service."""

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from src.api.v1 import auth, roles
from src.core.constants import V1_PREFIX
from src.core.exceptions import (APIError, api_error_handler,
                                 general_exception_handler,
                                 sqlalchemy_error_handler,
                                 validation_error_handler)
from src.core.versioning import get_api_version

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

# Register error handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Register routers with versioning
app.include_router(
    auth.router, prefix=V1_PREFIX, dependencies=[Depends(get_api_version)]
)
app.include_router(
    roles.router, prefix=V1_PREFIX, dependencies=[Depends(get_api_version)]
)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to the User Service",
        "version": "1.0.0",
        "status": "healthy",
    }
