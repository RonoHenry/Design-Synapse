"""API router for knowledge service."""
from fastapi import APIRouter
from .resources import router as resources_router
from .citations import router as citations_router
from .search import router as search_router

api_router = APIRouter()

# Include sub-routers
api_router.include_router(resources_router, prefix="/resources", tags=["resources"])
api_router.include_router(citations_router, prefix="/citations", tags=["citations"])
api_router.include_router(search_router, prefix="/search", tags=["search"])

@api_router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}