"""Main FastAPI application."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from src.api.middleware import (MetricsMiddleware, RequestIDMiddleware,
                                ResponseHeadersMiddleware)
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.exceptions import (ArchitecturalServiceException, ConflictError,
                                 ExternalServiceError, ForbiddenError,
                                 NotFoundError, UnauthorizedError,
                                 ValidationError)
from starlette.exceptions import HTTPException


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Architectural Service API",
    version="1.0.0",
    description="""
## Architectural Service API

The Architectural Service provides comprehensive architectural design management,
building code compliance checking, structural analysis, and material specification capabilities.

### Features

* **Design Management**: Create, update, and version architectural design documents
* **Building Code Compliance**: Automated compliance checking against IBC, IRC, and local codes
* **Structural Analysis**: Load calculations and structural integrity validation
* **Material Specifications**: Material management with vendor integration
* **Space Planning**: Layout optimization and space utilization analysis
* **Accessibility Compliance**: ADA and ANSI A117.1 compliance checking
* **Energy Analysis**: Building envelope performance and energy efficiency analysis
* **Real-time Collaboration**: Multi-user design collaboration with conflict resolution

### Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Error Handling

All errors follow a consistent format:

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {},
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "uuid"
    }
}
```

### Pagination

List endpoints use cursor-based pagination for efficient navigation:

* Use `limit` parameter to control page size (1-100, default: 20)
* Use `cursor` from response to fetch next page
* Use `sort_field` and `sort_direction` to control ordering

### Versioning

Design documents use automatic versioning:

* New designs start at version 1.0
* Updates increment version number automatically
* All versions are preserved for audit trail
* Retrieve specific versions using version parameter

### Rate Limiting

API requests are rate-limited per user:

* Standard tier: 100 requests per minute
* Premium tier: 1000 requests per minute

Rate limit information is included in response headers.
    """,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    contact={
        "name": "DesignSynapse Support",
        "url": "https://designsynapse.com/support",
        "email": "support@designsynapse.com",
    },
    license_info={"name": "Proprietary", "url": "https://designsynapse.com/license"},
    openapi_tags=[
        {
            "name": "designs",
            "description": "Design document management operations including creation, updates, and versioning",
        },
        {
            "name": "drawings",
            "description": "Architectural drawing upload and management (floor plans, elevations, sections)",
        },
        {
            "name": "compliance",
            "description": "Building code compliance checking against IBC, IRC, and local codes",
        },
        {
            "name": "structural-analysis",
            "description": "Structural analysis including load calculations and integrity validation",
        },
        {
            "name": "materials",
            "description": "Material specification management with vendor integration",
        },
        {
            "name": "space-planning",
            "description": "Space planning and layout optimization operations",
        },
        {
            "name": "accessibility",
            "description": "Accessibility compliance checking (ADA, ANSI A117.1)",
        },
        {
            "name": "energy-analysis",
            "description": "Energy efficiency analysis and building envelope performance",
        },
        {
            "name": "collaboration",
            "description": "Real-time collaboration and multi-user design editing",
        },
        {"name": "projects", "description": "Project-level operations and summaries"},
        {"name": "health", "description": "Service health checks and monitoring"},
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(ResponseHeadersMiddleware)
app.add_middleware(MetricsMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors (400 Bad Request)."""
    request_id = str(uuid.uuid4())

    # Extract field-level validation errors
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {"validation_errors": errors, "error_count": len(errors)},
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
):
    """Handle Pydantic validation errors from business logic."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Data validation failed",
                "details": {
                    "validation_errors": exc.errors(),
                    "error_count": len(exc.errors()),
                },
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(ValidationError)
async def custom_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle custom validation errors (400 Bad Request)."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedError):
    """Handle authentication errors (401 Unauthorized)."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(ForbiddenError)
async def forbidden_exception_handler(request: Request, exc: ForbiddenError):
    """Handle authorization errors (403 Forbidden)."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "FORBIDDEN",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError):
    """Handle not found errors (404 Not Found)."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(ConflictError)
async def conflict_exception_handler(request: Request, exc: ConflictError):
    """Handle conflict errors (409 Conflict)."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "CONFLICT",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(ExternalServiceError)
async def external_service_exception_handler(
    request: Request, exc: ExternalServiceError
):
    """Handle external service errors (502 Bad Gateway, 503 Service Unavailable)."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "EXTERNAL_SERVICE_ERROR",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity constraint violations."""
    request_id = str(uuid.uuid4())

    # Parse common constraint violations
    error_message = str(exc.orig) if exc.orig else str(exc)

    if "Duplicate entry" in error_message:
        message = "Resource already exists"
        code = "DUPLICATE_RESOURCE"
        status_code = status.HTTP_409_CONFLICT
    elif "foreign key constraint" in error_message.lower():
        message = "Referenced resource does not exist"
        code = "INVALID_REFERENCE"
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        message = "Data integrity constraint violation"
        code = "INTEGRITY_ERROR"
        status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {
                    "constraint_error": (
                        error_message
                        if settings.debug
                        else "Database constraint violation"
                    )
                },
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    """Handle database operational errors."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database service temporarily unavailable",
                "details": {
                    "database_error": (
                        str(exc) if settings.debug else "Database connection error"
                    )
                },
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle Starlette HTTP exceptions."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": {},
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(ArchitecturalServiceException)
async def architectural_service_exception_handler(
    request: Request, exc: ArchitecturalServiceException
):
    """Handle custom service exceptions."""
    request_id = str(uuid.uuid4())

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "SERVICE_ERROR",
                "message": exc.message,
                "details": exc.details,
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions (500 Internal Server Error)."""
    request_id = str(uuid.uuid4())

    # Log the full exception for debugging
    logger = logging.getLogger(__name__)
    logger.exception(f"Unhandled exception: {exc}", extra={"request_id": request_id})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {
                    "exception_type": type(exc).__name__,
                    "exception_message": (
                        str(exc) if settings.debug else "Internal server error"
                    ),
                },
                "timestamp": get_utc_timestamp(),
                "request_id": request_id,
            }
        },
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
    }


# Include API routers
from src.api.v1.routes import collaboration  # noqa: E402
from src.api.v1.routes import (accessibility, compliance, designs, drawings,
                               energy_analysis, health, materials, projects,
                               space_planning, structural_analysis)

app.include_router(designs.router, prefix=f"{settings.api_v1_prefix}", tags=["designs"])
app.include_router(
    drawings.router, prefix=f"{settings.api_v1_prefix}", tags=["drawings"]
)
app.include_router(
    collaboration.router, prefix=f"{settings.api_v1_prefix}", tags=["collaboration"]
)
app.include_router(
    projects.router, prefix=f"{settings.api_v1_prefix}", tags=["projects"]
)
app.include_router(
    compliance.router, prefix=f"{settings.api_v1_prefix}", tags=["compliance"]
)
app.include_router(
    structural_analysis.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["structural-analysis"],
)
app.include_router(
    materials.router, prefix=f"{settings.api_v1_prefix}", tags=["materials"]
)
app.include_router(
    space_planning.router, prefix=f"{settings.api_v1_prefix}", tags=["space-planning"]
)
app.include_router(
    accessibility.router, prefix=f"{settings.api_v1_prefix}", tags=["accessibility"]
)
app.include_router(
    energy_analysis.router, prefix=f"{settings.api_v1_prefix}", tags=["energy-analysis"]
)
app.include_router(health.router, prefix=f"{settings.api_v1_prefix}", tags=["health"])
