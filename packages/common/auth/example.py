"""Example usage of authentication middleware."""

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from .middleware import (AuthMiddleware, get_current_user, require_permissions,
                         require_roles)
from .models import UserContext
from .service_auth import ServiceAuthenticator

# Example FastAPI application with authentication middleware
app = FastAPI(title="Example Service with Auth")

# Add authentication middleware
app.add_middleware(
    AuthMiddleware,
    secret_key="your-secret-key",  # In production, use environment variable
    service_secret_key="your-service-secret-key",
    excluded_paths=["/health", "/docs", "/redoc", "/openapi.json"],
    require_auth=True,
)


@app.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/v1/profile")
async def get_profile(user: UserContext = Depends(get_current_user)):
    """Get current user profile - requires authentication."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "roles": user.roles,
        "permissions": user.permissions,
    }


@app.get("/api/v1/admin/users")
async def list_users(user: UserContext = Depends(require_roles("admin"))):
    """List all users - requires admin role."""
    return {"message": "Admin endpoint accessed successfully", "user": user.user_id}


@app.post("/api/v1/projects")
async def create_project(
    user: UserContext = Depends(require_permissions("write:projects")),
):
    """Create project - requires write:projects permission."""
    return {"message": "Project creation endpoint accessed", "user": user.user_id}


@app.get("/api/v1/service-info")
async def service_info():
    """Example of service-to-service authentication."""
    service_auth = ServiceAuthenticator()

    # Generate service token
    service_token = service_auth.generate_service_token("example-service")

    # Get headers for service requests
    headers = service_auth.get_service_headers("example-service")

    return {
        "service_token_expires": service_token.expires_at.isoformat(),
        "headers": headers,
    }


# Error handlers
@app.exception_handler(401)
async def unauthorized_handler(request, exc):
    """Handle authentication errors."""
    return JSONResponse(
        status_code=401,
        content={
            "error": "Authentication failed",
            "detail": str(exc.detail) if hasattr(exc, "detail") else "Unauthorized",
        },
    )


@app.exception_handler(403)
async def forbidden_handler(request, exc):
    """Handle authorization errors."""
    return JSONResponse(
        status_code=403,
        content={
            "error": "Authorization failed",
            "detail": str(exc.detail) if hasattr(exc, "detail") else "Forbidden",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
