"""Health check routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db_session

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "vendor-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/db")
async def database_health_check(db: AsyncSession = Depends(get_db_session)):
    """Database health check."""
    try:
        # Simple query to check database connectivity
        result = await db.execute("SELECT 1")
        result.fetchone()

        return {
            "status": "healthy",
            "service": "vendor-service",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "vendor-service",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
