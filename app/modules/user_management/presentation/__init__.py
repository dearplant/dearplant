# 📄 File: app/modules/user_management/presentation/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes the presentation layer for user management, which contains all the API endpoints
# and web interfaces that users interact with to manage their accounts and profiles in our plant care app.
#
# 🧪 Purpose (Technical Summary):
# Presentation layer initialization providing FastAPI routers, Pydantic schemas, and dependency
# injection setup for user management HTTP endpoints and API documentation.
#
# 🔗 Dependencies:
# - FastAPI for HTTP endpoint routing and OpenAPI documentation
# - app.modules.user_management.application (handlers and DTOs)
# - app.modules.user_management.domain (domain models for validation)
# - Pydantic schemas for request/response validation
#
# 🔄 Connected Modules / Calls From:
# - app.main (FastAPI application includes presentation routers)
# - API gateway (routes requests to user management endpoints)
# - Frontend applications (mobile app, web dashboard)

"""
User Management Presentation Layer

This module contains the presentation layer implementation for user management,
providing FastAPI routers and Pydantic schemas for HTTP API endpoints.

Presentation Components:
- API Routers: RESTful endpoints for user and profile operations
- Pydantic Schemas: Request/response validation and documentation
- Dependencies: Authentication, authorization, and request validation
- Error Handling: HTTP exception handling and error responses
- Documentation: OpenAPI/Swagger documentation generation

API Structure:
- /api/v1/auth: Authentication endpoints (login, register, logout)
- /api/v1/users: User account management endpoints
- /api/v1/profiles: Profile management endpoints

All endpoints follow REST conventions and provide comprehensive
OpenAPI documentation for API consumers.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # API Routers
    from app.modules.user_management.presentation.api.v1.auth import auth_router
    from app.modules.user_management.presentation.api.v1.users import users_router
    from app.modules.user_management.presentation.api.v1.profiles import profiles_router
    
    # Pydantic Schemas
    from app.modules.user_management.presentation.api.schemas.auth_schemas import (
        LoginRequest,
        RegisterRequest,
        LoginResponse,
        LogoutResponse,
        TokenRefreshRequest,
        TokenRefreshResponse,
        PasswordResetRequest,
        PasswordResetResponse,
    )
    from app.modules.user_management.presentation.api.schemas.user_schemas import (
        UserResponse,
        UserListResponse,
        UserUpdateRequest,
        UserSecurityResponse,
    )
    from app.modules.user_management.presentation.api.schemas.profile_schemas import (
        ProfileResponse,
        ProfileListResponse,
        ProfileCreateRequest,
        ProfileUpdateRequest,
        ProfileCompletenessResponse,
        ProfilePrivacyRequest,
        ProfilePrivacyResponse,
    )
    
    # Dependencies and utilities
    from app.modules.user_management.presentation.dependencies import (
        get_current_user,
        get_current_active_user,
        get_current_admin_user,
        get_user_from_token,
        verify_user_access,
    )

__all__ = [
    # API Routers
    "auth_router",
    "users_router",
    "profiles_router",
    
    # Auth Schemas
    "LoginRequest",
    "RegisterRequest",
    "LoginResponse",
    "LogoutResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "PasswordResetRequest",
    "PasswordResetResponse",
    
    # User Schemas
    "UserResponse",
    "UserListResponse",
    "UserUpdateRequest",
    "UserSecurityResponse",
    
    # Profile Schemas
    "ProfileResponse",
    "ProfileListResponse",
    "ProfileCreateRequest",
    "ProfileUpdateRequest",
    "ProfileCompletenessResponse",
    "ProfilePrivacyRequest",
    "ProfilePrivacyResponse",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_user_from_token",
    "verify_user_access",
]


def configure_presentation_layer():
    """
    Configure presentation layer routers and dependencies.
    
    This function should be called during application startup to register
    API routers with the main FastAPI application instance.
    
    Configuration includes:
    - Router registration with proper prefixes
    - CORS configuration for API endpoints
    - Rate limiting setup for authentication endpoints
    - OpenAPI documentation configuration
    - Error handler registration
    """
    # This will be implemented when we set up the main FastAPI app
    pass