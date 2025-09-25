"""
API constants and configuration values.
"""
from src.core.versioning import ApiVersion

# API versioning
LATEST_VERSION = ApiVersion.V1
API_VERSION_PREFIX = "/api"

# Version-specific prefixes
V1_PREFIX = f"{API_VERSION_PREFIX}/v1"