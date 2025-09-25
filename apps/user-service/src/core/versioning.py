"""
API versioning configuration and utilities.
"""
from enum import Enum
from typing import Optional

from fastapi import Header, HTTPException, status


class ApiVersion(str, Enum):
    """API version enumeration."""

    V1 = "v1"
    V2 = "v2"


def get_api_version(
    accept_version: Optional[str] = Header(
        None,
        description="API version to use. If not specified, latest version is used.",
        example="v1",
    )
) -> ApiVersion:
    """
    Get and validate the API version from the Accept-Version header.

    Args:
        accept_version: API version from Accept-Version header

    Returns:
        ApiVersion enum value

    Raises:
        HTTPException: If version is invalid
    """
    if accept_version is None:
        # Default to latest version
        return ApiVersion.V1

    try:
        return ApiVersion(accept_version.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"API version {accept_version} is not supported. Supported versions: {[v.value for v in ApiVersion]}",
        )
