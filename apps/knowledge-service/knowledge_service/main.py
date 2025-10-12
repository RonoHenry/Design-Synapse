"""Main FastAPI application module."""
from fastapi import FastAPI
from .api.v1 import api_router

app = FastAPI(
    title="Knowledge Service",
    description="Service for managing knowledge resources and citations",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")