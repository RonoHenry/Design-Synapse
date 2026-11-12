"""API v1 router — aggregates all route modules."""

from fastapi import APIRouter
from src.api.v1.routes import health, structural

router = APIRouter()

router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

router.include_router(
    structural.router,
    prefix="/structural",
    tags=["Structural Engineering"],
)
