"""Health check endpoints for Engineering Service."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", summary="Basic health check")
async def health() -> dict:
    """Check basic liveness."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", summary="Readiness check")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness check — verifies database connectivity."""
    checks: dict = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        checks["database"] = "error"

    overall = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return {
        "status": overall,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live", summary="Liveness check")
async def liveness() -> dict:
    """Liveness check — always returns healthy if the process is running."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
