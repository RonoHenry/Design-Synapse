"""Health check endpoints for the User Service."""
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.config import settings
from ...infrastructure.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "user-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check that verifies database connectivity."""
    try:
        # Check database connection
        db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "service": "user-service",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": {
                    "status": "healthy",
                    "message": "Database connection successful",
                }
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "service": "user-service",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "database": {
                        "status": "unhealthy",
                        "message": f"Database connection failed: {str(e)}",
                    }
                },
            },
        )


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with dependency status."""
    health_data = {
        "service": "user-service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {},
    }

    overall_healthy = True

    # Database health check
    try:
        result = db.execute(text("SELECT version()"))
        db_version = result.scalar() if result else "unknown"
        health_data["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
            "version": db_version,
        }
    except Exception as e:
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }
        overall_healthy = False

    # JWT configuration check
    try:
        if settings.jwt_secret_key:
            health_data["checks"]["jwt_config"] = {
                "status": "healthy",
                "message": "JWT configuration available",
            }
        else:
            health_data["checks"]["jwt_config"] = {
                "status": "unhealthy",
                "message": "JWT secret key not configured",
            }
            overall_healthy = False
    except Exception as e:
        health_data["checks"]["jwt_config"] = {
            "status": "unhealthy",
            "message": f"JWT configuration check failed: {str(e)}",
        }
        overall_healthy = False

    # Set overall status
    health_data["status"] = "healthy" if overall_healthy else "unhealthy"

    # Return appropriate HTTP status
    if not overall_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_data
        )

    return health_data


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get service metrics."""
    try:
        # Get basic database metrics
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        role_count = db.execute(text("SELECT COUNT(*) FROM roles")).scalar()

        return {
            "service": "user-service",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "users_total": user_count,
                "roles_total": role_count,
                "uptime_seconds": 0,  # This would be calculated from service start time
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}",
        )
