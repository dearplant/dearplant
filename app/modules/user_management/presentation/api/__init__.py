# 📄 File: app/modules/user_management/presentation/api/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes all the API endpoints for user management, making it easy to find and use
# all the web services that handle user accounts, logins, and profile management in our plant care app.
#
# 🧪 Purpose (Technical Summary):
# API package initialization providing FastAPI router organization for user management endpoints,
# version management, and API documentation structure following REST conventions.
#
# 🔗 Dependencies:
# - FastAPI routers and APIRouter classes
# - app.modules.user_management.presentation.api.v1 (versioned API endpoints)
# - app.modules.user_management.presentation.api.schemas (Pydantic request/response schemas)
# - HTTP status codes and exception handling
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.__init__ (API router registration)
# - app.main (FastAPI application includes API routers)
# - Frontend applications (mobile app, web interface, API consumers)

"""
User Management API

This module contains the API layer implementation for user management,
providing RESTful endpoints organized by version and resource type.

API Structure:
- Version 1 (/api/v1): Current stable API version
  - Authentication (/auth): Login, register, logout, password reset
  - Users (/users): User account management and administration
  - Profiles (/profiles): Profile management and social features

API Features:
- RESTful design following HTTP conventions
- Comprehensive request/response validation
- OpenAPI/Swagger documentation generation
- Proper HTTP status codes and error handling
- Authentication and authorization middleware
- Rate limiting for sensitive endpoints

All endpoints implement proper security measures and follow
Core Doc specifications for data handling and business rules.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Version 1 API Routers
    from app.modules.user_management.presentation.api.v1.auth import auth_router
    from app.modules.user_management.presentation.api.v1.users import users_router
    from app.modules.user_management.presentation.api.v1.profiles import profiles_router
    
    # Combined router for the entire API
    from fastapi import APIRouter

__all__ = [
    "auth_router",
    "users_router", 
    "profiles_router",
    "create_user_management_router",
]


def create_user_management_router() -> "APIRouter":
    """
    Create the main user management API router.
    
    This function combines all user management API routers into a single
    router that can be included in the main FastAPI application.
    
    Returns:
        APIRouter: Combined router for all user management endpoints
    """
    from fastapi import APIRouter
    from app.modules.user_management.presentation.api.v1.auth import auth_router
    from app.modules.user_management.presentation.api.v1.users import users_router
    from app.modules.user_management.presentation.api.v1.profiles import profiles_router
    
    # Create main router for user management
    main_router = APIRouter(
        prefix="/api/v1",
        tags=["User Management"],
        responses={
            400: {"description": "Bad Request - Invalid input data"},
            401: {"description": "Unauthorized - Authentication required"},
            403: {"description": "Forbidden - Insufficient permissions"},
            404: {"description": "Not Found - Resource does not exist"},
            422: {"description": "Unprocessable Entity - Validation error"},
            429: {"description": "Too Many Requests - Rate limit exceeded"},
            500: {"description": "Internal Server Error - System error"},
        }
    )
    
    # Include versioned routers
    main_router.include_router(
        auth_router,
        prefix="/auth",
        tags=["Authentication"]
    )
    
    main_router.include_router(
        users_router,
        prefix="/users", 
        tags=["Users"]
    )
    
    main_router.include_router(
        profiles_router,
        prefix="/profiles",
        tags=["Profiles"]
    )
    
    return main_router