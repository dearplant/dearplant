# 📄 File: app/api/__init__.py
# 🧭 Purpose (Layman Explanation): 
# This file marks the api folder as a Python package so other parts of the app can import and use
# the API functionality, like a table of contents for all our API features.
# 🧪 Purpose (Technical Summary): 
# Package initialization for the API layer, providing centralized imports and version management
# for the FastAPI application's API endpoints and middleware.
# 🔗 Dependencies: 
# None (package initialization)
# 🔄 Connected Modules / Calls From: 
# app.main.py, all API route imports, middleware imports

"""
Plant Care Application API Package

This package contains all API-related modules including:
- API versioning (v1, v2, etc.)
- Middleware for authentication, rate limiting, logging
- Health check endpoints
- Route management and organization

Structure:
    api/
    ├── __init__.py          # This file
    ├── middleware/          # API middleware components
    │   ├── authentication.py
    │   ├── rate_limiting.py
    │   ├── logging.py
    │   └── error_handling.py
    └── v1/                  # API version 1
        ├── __init__.py
        ├── router.py        # Main v1 router
        ├── health.py        # Health check endpoints
        └── [module routers] # Individual module API routes
"""

# API package metadata
__version__ = "1.0.0"
__author__ = "Plant Care Team"
__description__ = "Plant Care Application REST API"

# API configuration constants
API_PREFIX = "/api"
CURRENT_VERSION = "v1"
SUPPORTED_VERSIONS = ["v1"]

# API response headers
DEFAULT_HEADERS = {
    "X-API-Version": CURRENT_VERSION,
    "X-App-Name": "PlantCare",
}

# Import exceptions for API-wide error handling
from app.shared.core.exceptions import (
    PlantCareException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
)

# Re-export commonly used exceptions for convenience
__all__ = [
    "PlantCareException",
    "ValidationError", 
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "RateLimitError",
    "API_PREFIX",
    "CURRENT_VERSION",
    "SUPPORTED_VERSIONS",
    "DEFAULT_HEADERS",
]