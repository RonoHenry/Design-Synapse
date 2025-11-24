"""
Labor Services Marketplace FastAPI Application

Main application entry point for the Labor Services Marketplace.
Handles service provider and seeker connections, job matching,
booking management, and payment processing.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import create_tables, health_check
from .core.exceptions import LaborServiceException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Labor Services Marketplace...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Perform health checks
    health_status = await health_check()
    if health_status.get("database") != "healthy":
        logger.error("Database health check failed")
        raise Exception("Database connection failed")
    
    logger.info("Labor Services Marketplace started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Labor Services Marketplace...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Labor Services Marketplace - Connect skilled professionals with clients",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(LaborServiceException)
async def labor_service_exception_handler(request: Request, exc: LaborServiceException):
    """Handle custom Labor Service exceptions"""
    logger.error(f"Labor Service Exception: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code or "LABOR_SERVICE_ERROR",
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred"
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check_endpoint():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database"""
    health_status = await health_check()
    return {
        "status": "healthy" if health_status.get("database") == "healthy" else "unhealthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": health_status
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Labor Services Marketplace API",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation not available in production"
    }


# API routes will be added here as we implement them
# TODO: Add API routers for:
# - /api/v1/providers
# - /api/v1/requests
# - /api/v1/quotes
# - /api/v1/bookings
# - /api/v1/payments
# - /api/v1/reviews
# - /api/v1/matching
# - /api/v1/search


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )