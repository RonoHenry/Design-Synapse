# Authentication Middleware

This package provides comprehensive authentication and authorization middleware for cross-service validation in the DesignSynapse platform.

## Features

- **JWT Token Validation**: Validates user JWT tokens with proper error handling
- **Service-to-Service Authentication**: Secure authentication between internal services
- **Role-Based Access Control (RBAC)**: Endpoint-specific authorization based on user roles and permissions
- **User Context Extraction**: Extracts user information and injects it into request headers
- **FastAPI Integration**: Seamless integration with FastAPI applications

## Components

### AuthMiddleware

Main middleware class that handles authentication and authorization for all requests.

```python
from fastapi import FastAPI
from packages.common.auth import AuthMiddleware

app = FastAPI()

app.add_middleware(
    AuthMiddleware,
    secret_key="your-jwt-secret",
    service_secret_key="your-service-secret",
    excluded_paths=["/health", "/docs"],
    require_auth=True
)
```

### JWTValidator

Validates and decodes JWT tokens.

```python
from packages.common.auth import JWTValidator

validator = JWTValidator(secret_key="your-secret")
auth_result = validator.validate_token("Bearer your-jwt-token")
```

### ServiceAuthenticator

Handles service-to-service authentication.

```python
from packages.common.auth import ServiceAuthenticator

service_auth = ServiceAuthenticator()
service_token = service_auth.generate_service_token("my-service")
headers = service_auth.get_service_headers("my-service")
```

### RoleBasedAccessControl

Manages role-based permissions and endpoint access control.

```python
from packages.common.auth import RoleBasedAccessControl, PermissionRule

rbac = RoleBasedAccessControl()
rbac.add_permission_rule(PermissionRule(
    endpoint_pattern="/api/v1/admin/*",
    required_roles=["admin"],
    required_permissions=["manage:users"]
))
```

## FastAPI Dependencies

### get_current_user

Extracts authenticated user from request.

```python
from fastapi import Depends
from packages.common.auth import get_current_user, UserContext

@app.get("/profile")
async def get_profile(user: UserContext = Depends(get_current_user)):
    return {"user_id": user.user_id, "roles": user.roles}
```

### require_roles

Requires specific roles for endpoint access.

```python
from packages.common.auth import require_roles

@app.get("/admin")
async def admin_endpoint(user: UserContext = Depends(require_roles("admin"))):
    return {"message": "Admin access granted"}
```

### require_permissions

Requires specific permissions for endpoint access.

```python
from packages.common.auth import require_permissions

@app.post("/projects")
async def create_project(user: UserContext = Depends(require_permissions("write:projects"))):
    return {"message": "Project created"}
```

## Configuration

### Environment Variables

- `SECRET_KEY`: JWT secret key for user token validation
- `SERVICE_SECRET_KEY`: Secret key for service-to-service authentication (falls back to SECRET_KEY)
- `SERVICE_TOKEN_EXPIRY_HOURS`: Service token expiration time in hours (default: 24)

### Default Roles and Permissions

The system includes default roles with predefined permissions:

- **admin**: Full system access
- **project_manager**: Project and design management
- **designer**: Design creation and modification
- **viewer**: Read-only access
- **service**: Internal service operations

### Default Permission Rules

Default rules are automatically configured for common endpoints:

- `/api/v1/admin/*` - Requires admin role
- `/api/v1/users/*` - Requires admin or project_manager role
- `/api/v1/projects/*` - Role-based access (read/write permissions)
- `/api/v1/designs/*` - Role-based access (read/write permissions)
- `/health` - Public access

## Error Codes

- `AUTH_001`: Authentication failed (invalid token, missing header)
- `AUTH_002`: Authorization failed (insufficient permissions/roles)
- `AUTH_003`: Token expired
- `AUTH_004`: Invalid token signature

## Usage Examples

### Basic FastAPI Application

```python
from fastapi import FastAPI, Depends
from packages.common.auth import (
    AuthMiddleware,
    get_current_user,
    require_roles,
    UserContext
)

app = FastAPI()

# Add authentication middleware
app.add_middleware(
    AuthMiddleware,
    secret_key="your-secret-key",
    require_auth=True
)

@app.get("/protected")
async def protected_endpoint(user: UserContext = Depends(get_current_user)):
    return {"message": f"Hello {user.email}"}

@app.get("/admin-only")
async def admin_endpoint(user: UserContext = Depends(require_roles("admin"))):
    return {"message": "Admin access granted"}
```

### Service-to-Service Communication

```python
import httpx
from packages.common.auth import ServiceAuthenticator

# Service A calling Service B
service_auth = ServiceAuthenticator()
headers = service_auth.get_service_headers("service-a")

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://service-b/api/v1/data",
        headers=headers
    )
```

### Custom Permission Rules

```python
from packages.common.auth import RoleBasedAccessControl, PermissionRule

rbac = RoleBasedAccessControl()

# Add custom rule
rbac.add_permission_rule(PermissionRule(
    endpoint_pattern="/api/v1/reports/{id}",
    required_roles=["admin", "analyst"],
    required_permissions=["read:reports"],
    allow_service_auth=True,
    description="Report access for analysts and admins"
))
```

## Testing

The authentication middleware includes comprehensive error handling and logging. All authentication and authorization events are logged with appropriate context for monitoring and debugging.

For testing, you can create mock user contexts:

```python
from packages.common.auth import UserContext

test_user = UserContext(
    user_id="test-user",
    email="test@example.com",
    roles=["designer"],
    permissions=["read:projects", "write:designs"]
)
```

## Security Considerations

- Always use strong secret keys in production
- Rotate service tokens regularly
- Monitor authentication logs for suspicious activity
- Use HTTPS for all communications
- Validate all input data in endpoints
- Implement rate limiting for authentication endpoints
