"""API versioning functionality."""

from fastapi import Header, HTTPException


async def get_api_version(
    accept: str = Header(None, description="API version header")
) -> str:
    """Extract and validate the API version from the Accept header."""
    if not accept or "application/vnd.design-synapse.v1+json" in accept:
        return "1.0"
    raise HTTPException(
        status_code=406,
        detail="Unsupported API version. Please use: application/vnd.design-synapse.v1+json"
    )