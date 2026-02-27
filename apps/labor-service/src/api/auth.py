"""
Authentication and Authorization utilities for Labor Services Marketplace
Provides JWT token handling, role-based access control, and security utilities
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Configuration - in production, use environment variables
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()


class UserRole(str, Enum):
    """User roles enumeration"""

    ADMIN = "admin"
    PROVIDER = "provider"
    SEEKER = "seeker"
    MODERATOR = "moderator"


class Permission(str, Enum):
    """Permission enumeration"""

    READ_PROVIDERS = "read:providers"
    WRITE_PROVIDERS = "write:providers"
    READ_REQUESTS = "read:requests"
    WRITE_REQUESTS = "write:requests"
    READ_QUOTES = "read:quotes"
    WRITE_QUOTES = "write:quotes"
    READ_BOOKINGS = "read:bookings"
    WRITE_BOOKINGS = "write:bookings"
    READ_REVIEWS = "read:reviews"
    WRITE_REVIEWS = "write:reviews"
    MODERATE_CONTENT = "moderate:content"
    ADMIN_ACCESS = "admin:access"


class TokenData(BaseModel):
    """Token payload data"""

    user_id: int
    email: str
    role: UserRole
    permissions: List[Permission]
    exp: datetime


class AuthUser(BaseModel):
    """Authenticated user model"""

    id: int
    email: str
    role: UserRole
    permissions: List[Permission]
    is_active: bool = True
    is_verified: bool = True


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.READ_PROVIDERS,
        Permission.WRITE_PROVIDERS,
        Permission.READ_REQUESTS,
        Permission.WRITE_REQUESTS,
        Permission.READ_QUOTES,
        Permission.WRITE_QUOTES,
        Permission.READ_BOOKINGS,
        Permission.WRITE_BOOKINGS,
        Permission.READ_REVIEWS,
        Permission.WRITE_REVIEWS,
        Permission.MODERATE_CONTENT,
        Permission.ADMIN_ACCESS,
    ],
    UserRole.PROVIDER: [
        Permission.READ_PROVIDERS,
        Permission.WRITE_PROVIDERS,
        Permission.READ_REQUESTS,
        Permission.READ_QUOTES,
        Permission.WRITE_QUOTES,
        Permission.READ_BOOKINGS,
        Permission.WRITE_BOOKINGS,
        Permission.READ_REVIEWS,
        Permission.WRITE_REVIEWS,
    ],
    UserRole.SEEKER: [
        Permission.READ_PROVIDERS,
        Permission.READ_REQUESTS,
        Permission.WRITE_REQUESTS,
        Permission.READ_QUOTES,
        Permission.READ_BOOKINGS,
        Permission.WRITE_BOOKINGS,
        Permission.READ_REVIEWS,
        Permission.WRITE_REVIEWS,
    ],
    UserRole.MODERATOR: [
        Permission.READ_PROVIDERS,
        Permission.READ_REQUESTS,
        Permission.READ_QUOTES,
        Permission.READ_BOOKINGS,
        Permission.READ_REVIEWS,
        Permission.MODERATE_CONTENT,
    ],
}


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int, email: str, role: UserRole) -> str:
    """Create JWT access token"""
    permissions = ROLE_PERMISSIONS.get(role, [])
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "user_id": user_id,
        "email": email,
        "role": role.value,
        "permissions": [p.value for p in permissions],
        "exp": expire,
        "type": "access",
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {"user_id": user_id, "exp": expire, "type": "refresh"}

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """Get current authenticated user from token"""
    try:
        payload = decode_token(credentials.credentials)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user = AuthUser(
            id=payload["user_id"],
            email=payload["email"],
            role=UserRole(payload["role"]),
            permissions=[Permission(p) for p in payload["permissions"]],
        )

        return user

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token payload: missing {e}",
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthUser]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_permissions(*required_permissions: Permission):
    """Decorator to require specific permissions"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_permissions = set(current_user.permissions)
            required_perms = set(required_permissions)

            if not required_perms.issubset(user_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(*required_roles: UserRole):
    """Decorator to require specific roles"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if current_user.role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient role permissions",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_owner_or_admin(resource_user_id_field: str = "user_id"):
    """Decorator to require resource ownership or admin role"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Admin can access anything
            if current_user.role == UserRole.ADMIN:
                return await func(*args, **kwargs)

            # Check resource ownership
            resource_user_id = kwargs.get(resource_user_id_field)
            if resource_user_id and resource_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: not resource owner",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
