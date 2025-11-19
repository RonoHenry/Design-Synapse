"""API router for knowledge service."""
import sys
from pathlib import Path

from fastapi import APIRouter

# Add packages to path for common imports
packages_path = Path(__file__).parent.parent.parent.parent.parent / "packages"
sys.path.insert(0, str(packages_path))

from common.database.health import check_database_health

from ...core.config import settings
from .bookmarks import router as bookmarks_router
from .citations import router as citations_router
from .resources import router as resources_router
from .search import router as search_router
from .health import router as health_router
from .content_analysis import router as content_analysis_router
from .enhanced_resources import router as enhanced_resources_router
from .cache_management import router as cache_management_router
from .recommendations import router as recommendations_router
from .recommendations import router as recommendations_router

api_router = APIRouter()

# Include sub-routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(resources_router, prefix="/resources", tags=["resources"])
api_router.include_router(enhanced_resources_router, tags=["enhanced-resources"])
api_router.include_router(content_analysis_router, tags=["content-analysis"])
api_router.include_router(cache_management_router, tags=["cache-management"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(bookmarks_router, prefix="/bookmarks", tags=["bookmarks"])
api_router.include_router(citations_router, prefix="/citations", tags=["citations"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])


# Health check is now handled by the dedicated health router
