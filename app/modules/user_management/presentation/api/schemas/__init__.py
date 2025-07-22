# 📄 File: app/modules/user_management/presentation/api/schemas/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes all the data validation schemas for our user management API, making sure
# that incoming requests and outgoing responses have the correct format and required information.
#
# 🧪 Purpose (Technical Summary):
# API schemas package initialization providing Pydantic request/response models for user management
# endpoints with comprehensive validation, serialization, and OpenAPI documentation generation.
#
# 🔗 Dependencies:
# - pydantic models for request/response validation
# - app.modules.user_management.application.dto (DTOs for data conversion)
# - Core Doc specifications for field validation and constraints
# - OpenAPI/Swagger documentation generation
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1 (API endpoints use schemas)
# - FastAPI automatic validation and documentation generation
# - Frontend applications (API client generation from schemas)

"""
User Management API Schemas

This module contains all Pydantic schemas for user management API endpoints,
providing comprehensive request/response validation and OpenAPI documentation.

Schema Categories:
- Authentication Schemas: Login, register, token refresh, password reset
- User Schemas: User data requests, responses, and administrative operations
- Profile Schemas: Profile management, privacy settings, and social features

Schema Features:
- Comprehensive validation using Pydantic models
- Core Doc compliance for all field specifications
- OpenAPI/Swagger documentation generation
- Request/response serialization and deserialization
- Error response standardization
- Security field filtering and privacy controls

All schemas follow REST conventions and integrate with the application
layer DTOs for proper data transformation and business logic validation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Authentication Schemas
    from app.modules.user_management.presentation.api.schemas.auth_schemas import (
        LoginRequest,
        RegisterRequest,
        LoginResponse,
        LogoutResponse,
        TokenRefreshRequest,
        TokenRefreshResponse,
        PasswordResetRequest,
        PasswordResetResponse,
        EmailVerificationRequest,
        EmailVerificationResponse,
        OAuthInitiateResponse,
        OAuthCallbackRequest,
        OAuthCallbackResponse,
    )
    
    # User Schemas
    from app.modules.user_management.presentation.api.schemas.user_schemas import (
        UserResponse,
        UserListResponse,
        UserUpdateRequest,
        UserSecurityResponse,
        UserDeleteRequest,
        UserDeleteResponse,
        EmailVerificationResponse,
        AccountUnlockResponse,
    )
    
    # Profile Schemas
    from app.modules.user_management.presentation.api.schemas.profile_schemas import (
        ProfileResponse,
        ProfileListResponse,
        ProfileCreateRequest,
        ProfileUpdateRequest,
        ProfileCompletenessResponse,
        ProfilePrivacyRequest,
        ProfilePrivacyResponse,
        ProfilePhotoResponse,
        ProfileSearchRequest,
        ProfileSearchResponse,
    )

__all__ = [
    # Authentication Schemas
    "LoginRequest",
    "RegisterRequest",
    "LoginResponse",
    "LogoutResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "PasswordResetRequest",
    "PasswordResetResponse",
    "EmailVerificationRequest",
    "EmailVerificationResponse",
    "OAuthInitiateResponse",
    "OAuthCallbackRequest",
    "OAuthCallbackResponse",
    
    # User Schemas
    "UserResponse",
    "UserListResponse",
    "UserUpdateRequest",
    "UserSecurityResponse",
    "UserDeleteRequest",
    "UserDeleteResponse",
    "EmailVerificationResponse",
    "AccountUnlockResponse",
    
    # Profile Schemas
    "ProfileResponse",
    "ProfileListResponse",
    "ProfileCreateRequest",
    "ProfileUpdateRequest",
    "ProfileCompletenessResponse",
    "ProfilePrivacyRequest",
    "ProfilePrivacyResponse",
    "ProfilePhotoResponse",
    "ProfileSearchRequest",
    "ProfileSearchResponse",
]


def get_schema_info() -> dict:
    """
    Get schema information for API documentation.
    
    Returns:
        dict: Schema metadata and documentation information
    """
    return {
        "authentication_schemas": {
            "description": "Schemas for user authentication and session management",
            "schemas": [
                "LoginRequest", "RegisterRequest", "LoginResponse", "LogoutResponse",
                "TokenRefreshRequest", "TokenRefreshResponse", "PasswordResetRequest",
                "PasswordResetResponse", "EmailVerificationRequest", "EmailVerificationResponse",
                "OAuthInitiateResponse", "OAuthCallbackRequest", "OAuthCallbackResponse"
            ]
        },
        "user_schemas": {
            "description": "Schemas for user account management and administration",
            "schemas": [
                "UserResponse", "UserListResponse", "UserUpdateRequest", "UserSecurityResponse",
                "UserDeleteRequest", "UserDeleteResponse", "EmailVerificationResponse",
                "AccountUnlockResponse"
            ]
        },
        "profile_schemas": {
            "description": "Schemas for profile management and social features",
            "schemas": [
                "ProfileResponse", "ProfileListResponse", "ProfileCreateRequest",
                "ProfileUpdateRequest", "ProfileCompletenessResponse", "ProfilePrivacyRequest", 
                "ProfilePrivacyResponse", "ProfilePhotoResponse", "ProfileSearchRequest",
                "ProfileSearchResponse"
            ]
        },
        "validation_features": [
            "Core Doc field compliance",
            "Security field filtering",
            "Privacy setting validation",
            "File upload validation",
            "Pagination parameters",
            "Search and filtering criteria"
        ],
        "documentation_features": [
            "OpenAPI/Swagger integration",
            "Comprehensive field descriptions",
            "Example values for all fields",
            "Error response schemas",
            "Security requirement documentation"
        ]
    }


def get_common_response_schemas() -> dict:
    """
    Get common response schemas used across multiple endpoints.
    
    Returns:
        dict: Common response schema definitions
    """
    return {
        "error_response": {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "description": "Error message"},
                "error_code": {"type": "string", "description": "Machine-readable error code"},
                "timestamp": {"type": "string", "format": "date-time", "description": "Error timestamp"},
                "path": {"type": "string", "description": "Request path where error occurred"}
            },
            "required": ["detail"]
        },
        "success_response": {
            "type": "object", 
            "properties": {
                "message": {"type": "string", "description": "Success message"},
                "timestamp": {"type": "string", "format": "date-time", "description": "Response timestamp"},
                "data": {"type": "object", "description": "Response data"}
            },
            "required": ["message"]
        },
        "pagination_response": {
            "type": "object",
            "properties": {
                "page": {"type": "integer", "minimum": 1, "description": "Current page number"},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Items per page"},
                "total_count": {"type": "integer", "minimum": 0, "description": "Total number of items"},
                "total_pages": {"type": "integer", "minimum": 0, "description": "Total number of pages"},
                "has_next": {"type": "boolean", "description": "Whether there is a next page"},
                "has_previous": {"type": "boolean", "description": "Whether there is a previous page"}
            },
            "required": ["page", "page_size", "total_count", "total_pages", "has_next", "has_previous"]
        }
    }