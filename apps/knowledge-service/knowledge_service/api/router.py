"""API router for the knowledge service."""

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["knowledge"]
)

# Import sub-routers
from .resources import router as resource_router
from .citations import router as citation_router
from .search import router as search_router

# Include sub-routers
router.include_router(resource_router)
router.include_router(citation_router)
router.include_router(search_router)