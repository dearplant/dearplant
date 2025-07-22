# 📄 File: app/modules/user_management/presentation/api/schemas/user_schemas.py
# 🧭 Purpose (Layman Explanation):
# This file defines all the data formats for user account requests and responses like user profiles,
# account updates, security information, and admin functions for our plant care app's API.
#
# 🧪 Purpose (Technical Summary):
# Pydantic user management schemas implementing Core Doc 1.1 specifications for request/response
# validation, security filtering, admin operations, and comprehensive user account management.
#
# 🔗 Dependencies:
# - pydantic for schema validation and serialization
# - app.modules.user_management.application.dto.user_dto (DTOs for data conversion)
# - Core doc 1.1 specifications for user account fields and validation
# - FastAPI integration for automatic validation and documentation
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1.users (user management endpoints)
# - FastAPI automatic request validation and response serialization
# - Admin dashboard and user management interfaces

"""
User Management API Schemas

This module implements Pydantic schemas for user account management endpoints
following Core Doc 1.1 specifications with comprehensive validation and security.

Request Schemas:
- UserUpdateRequest: User account information updates
- UserDeleteRequest: User account deletion with confirmation
- UserSearchRequest: User search and filtering parameters

Response Schemas:
- UserResponse: User account information with access-level filtering
- UserListResponse: Paginated user list with metadata
- UserSecurityResponse: Admin-only security information
- UserDeleteResponse: Account deletion confirmation
- EmailVerificationResponse: Email verification status updates
- AccountUnlockResponse: Account unlock confirmation

Security Features:
- Multi-level access control (public, self, admin)
- Security field filtering based on requester permissions
- Admin-only operations and information access
- Comprehensive audit logging for administrative actions
- Privacy-aware user information display

All schemas follow Core Doc 1.1 specifications and implement proper
security measures for user account management operations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class UserStatus(str, Enum):
    """User account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


class UserProvider(str, Enum):
    """Authentication provider enumeration."""
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"


class DeletionReason(str, Enum):
    """Account deletion reason enumeration."""
    USER_REQUEST = "user_request"
    PRIVACY_CONCERNS = "privacy_concerns"
    NOT_USING_APP = "not_using_app"
    FOUND_ALTERNATIVE = "found_alternative"
    TOO_COMPLICATED = "too_complicated"
    PERFORMANCE_ISSUES = "performance_issues"
    ADMIN_DELETION = "admin_deletion"
    SPAM_VIOLATION = "spam_violation"
    TERMS_VIOLATION = "terms_violation"
    OTHER = "other"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class UserUpdateRequest(BaseModel):
    """
    User account update request schema following Core Doc 1.1 specifications.
    
    This schema validates user account updates with proper security
    validation and field-level permissions.
    """
    
    email: Optional[EmailStr] = Field(
        default=None,
        description="Updated email address",
        example="newemail@example.com"
    )
    email_verified: Optional[bool] = Field(
        default=None,
        description="Email verification status (admin only)",
        example=True
    )
    account_locked: Optional[bool] = Field(
        default=None,
        description="Account lock status (admin only)",
        example=False
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "email_verified": True,
                "account_locked": False
            }
        }
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format and normalize to lowercase."""
        if v:
            return v.lower()
        return v


class UserDeleteRequest(BaseModel):
    """
    User account deletion request schema with security confirmation.
    
    This schema validates account deletion requests with proper security
    measures and audit information following Core Doc 1.1 requirements.
    """
    
    # Security confirmation (Core Doc 1.1)
    confirmation_token: str = Field(
        ...,
        min_length=32,
        max_length=128,
        description="Security confirmation token",
        example="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
    )
    password_confirmation: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password for confirmation",
        example="CurrentPassword123!"
    )
    
    # Deletion metadata
    reason: Optional[DeletionReason] = Field(
        default=DeletionReason.USER_REQUEST,
        description="Reason for account deletion",
        example=DeletionReason.USER_REQUEST
    )
    reason_details: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional details about deletion reason",
        example="Moving to a different platform for plant care"
    )
    
    # Deletion options
    hard_delete: bool = Field(
        default=False,
        description="Whether to permanently delete (true) or soft delete (false)",
        example=False
    )
    immediate_deletion: bool = Field(
        default=False,
        description="Skip grace period and delete immediately",
        example=False
    )
    
    # Cleanup options
    delete_user_data: bool = Field(
        default=True,
        description="Delete user profile and personal data",
        example=True
    )
    delete_subscription_data: bool = Field(
        default=True,
        description="Cancel and delete subscription information",
        example=True
    )
    delete_uploaded_files: bool = Field(
        default=True,
        description="Delete profile photos and uploaded files",
        example=True
    )
    revoke_all_sessions: bool = Field(
        default=True,
        description="Revoke all active sessions and tokens",
        example=True
    )
    
    # Admin fields
    admin_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Admin reason for deletion (admin only)",
        example="Account violated terms of service"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "confirmation_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                "password_confirmation": "CurrentPassword123!",
                "reason": "not_using_app",
                "reason_details": "Switching to manual plant care tracking",
                "hard_delete": False,
                "immediate_deletion": False,
                "delete_user_data": True,
                "delete_subscription_data": True,
                "delete_uploaded_files": True,
                "revoke_all_sessions": True,
                "admin_reason": None
            }
        }


class UserSearchRequest(BaseModel):
    """
    User search request schema for admin user management.
    
    This schema validates user search and filtering parameters
    for administrative user discovery and management.
    """
    
    # Search parameters
    search_term: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Search term for email or display name",
        example="john"
    )
    email_filter: Optional[str] = Field(
        default=None,
        description="Filter by email domain or pattern",
        example="@gmail.com"
    )
    
    # Status filters
    status_filter: Optional[UserStatus] = Field(
        default=None,
        description="Filter by user account status",
        example=UserStatus.ACTIVE
    )
    provider_filter: Optional[UserProvider] = Field(
        default=None,
        description="Filter by authentication provider",
        example=UserProvider.EMAIL
    )
    email_verified_filter: Optional[bool] = Field(
        default=None,
        description="Filter by email verification status",
        example=True
    )
    
    # Date filters
    created_after: Optional[datetime] = Field(
        default=None,
        description="Filter users created after this date",
        example="2024-01-01T00:00:00Z"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Filter users created before this date",
        example="2024-12-31T23:59:59Z"
    )
    last_login_after: Optional[datetime] = Field(
        default=None,
        description="Filter users with last login after this date",
        example="2024-01-01T00:00:00Z"
    )
    
    # Pagination
    page: int = Field(
        default=1,
        ge=1,
        description="Page number",
        example=1
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page",
        example=20
    )
    
    # Sorting
    sort_by: str = Field(
        default="created_at",
        description="Sort field (created_at, email, last_login)",
        example="created_at"
    )
    sort_order: str = Field(
        default="desc",
        description="Sort order (asc, desc)",
        example="desc"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "search_term": "john",
                "status_filter": "active",
                "provider_filter": "email",
                "email_verified_filter": True,
                "created_after": "2024-01-01T00:00:00Z",
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }
    
    @validator('sort_by')
    def validate_sort_field(cls, v):
        """Validate sort field options."""
        allowed_fields = ["created_at", "email", "last_login", "display_name"]
        if v not in allowed_fields:
            raise ValueError(f"Sort field must be one of: {', '.join(allowed_fields)}")
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order options."""
        if v not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class UserResponse(BaseModel):
    """
    User account response schema with access-level filtering.
    
    This schema provides user account information with appropriate
    field filtering based on the requester's access level.
    """
    
    user_id: UUID = Field(
        ...,
        description="User's unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: str = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )
    created_at: datetime = Field(
        ...,
        description="Account creation date",
        example="2024-01-15T10:30:00Z"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last login timestamp",
        example="2024-01-20T14:25:00Z"
    )
    email_verified: bool = Field(
        ...,
        description="Email verification status",
        example=True
    )
    provider: UserProvider = Field(
        ...,
        description="Authentication provider",
        example=UserProvider.EMAIL
    )
    status: UserStatus = Field(
        ...,
        description="Account status",
        example=UserStatus.ACTIVE
    )
    
    # Optional fields based on access level
    login_attempts: Optional[int] = Field(
        default=None,
        description="Failed login attempts (self/admin only)",
        example=0
    )
    account_locked: Optional[bool] = Field(
        default=None,
        description="Account locked status (admin only)",
        example=False
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "created_at": "2024-01-15T10:30:00Z",
                "last_login": "2024-01-20T14:25:00Z",
                "email_verified": True,
                "provider": "email",
                "status": "active",
                "login_attempts": 0,
                "account_locked": False
            }
        }
    
    @classmethod
    def from_domain_data(cls, user_data: Dict, access_level: str = "public") -> "UserResponse":
        """
        Create response from domain user data with access level filtering.
        
        Args:
            user_data: User data from domain layer
            access_level: Access level for field filtering ("public", "self", "admin")
            
        Returns:
            UserResponse: Filtered user response
        """
        # Determine status from user state
        if user_data.get("account_locked", False):
            status = UserStatus.LOCKED
        elif not user_data.get("email_verified", True):
            status = UserStatus.PENDING_VERIFICATION
        else:
            status = UserStatus.ACTIVE
        
        # Base response data
        response_data = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "created_at": user_data["created_at"],
            "last_login": user_data.get("last_login"),
            "email_verified": user_data.get("email_verified", False),
            "provider": UserProvider(user_data.get("provider", "email")),
            "status": status,
        }
        
        # Add fields based on access level
        if access_level in ["self", "admin"]:
            response_data["login_attempts"] = user_data.get("login_attempts", 0)
        
        if access_level == "admin":
            response_data["account_locked"] = user_data.get("account_locked", False)
        
        return cls(**response_data)


class UserListResponse(BaseModel):
    """
    Paginated user list response schema for admin user management.
    
    This schema provides paginated user data with navigation metadata
    and filtering information for administrative interfaces.
    """
    
    users: List[UserResponse] = Field(
        ...,
        description="List of users",
        example=[]
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of users matching criteria",
        example=150
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
        example=1
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of users per page",
        example=20
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        example=8
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page",
        example=True
    )
    has_previous: bool = Field(
        ...,
        description="Whether there is a previous page",
        example=False
    )
    
    # Filter summary
    applied_filters: Dict = Field(
        default_factory=dict,
        description="Summary of applied filters",
        example={"status_filter": "active", "email_verified_filter": True}
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "users": [
                    {
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user1@example.com",
                        "created_at": "2024-01-15T10:30:00Z",
                        "email_verified": True,
                        "provider": "email",
                        "status": "active"
                    }
                ],
                "total_count": 150,
                "page": 1,
                "page_size": 20,
                "total_pages": 8,
                "has_next": True,
                "has_previous": False,
                "applied_filters": {"status_filter": "active", "email_verified_filter": True}
            }
        }


class UserSecurityResponse(BaseModel):
    """
    User security information response schema (admin only).
    
    This schema provides detailed security information for administrative
    monitoring and user account security management.
    """
    
    user_id: UUID = Field(
        ...,
        description="User's unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    login_attempts: int = Field(
        ...,
        ge=0,
        description="Failed login attempt counter",
        example=2
    )
    account_locked: bool = Field(
        ...,
        description="Account lock status",
        example=False
    )
    has_reset_token: bool = Field(
        ...,
        description="Whether user has active reset token",
        example=False
    )
    reset_token_expires: Optional[datetime] = Field(
        default=None,
        description="Reset token expiration",
        example=None
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last successful login",
        example="2024-01-20T14:25:00Z"
    )
    created_at: datetime = Field(
        ...,
        description="Account creation date",
        example="2024-01-15T10:30:00Z"
    )
    email_verified: bool = Field(
        ...,
        description="Email verification status",
        example=True
    )
    provider: UserProvider = Field(
        ...,
        description="Authentication provider",
        example=UserProvider.EMAIL
    )
    security_events: List[Dict] = Field(
        default_factory=list,
        description="Recent security events",
        example=[]
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "login_attempts": 0,
                "account_locked": False,
                "has_reset_token": False,
                "reset_token_expires": None,
                "last_login": "2024-01-20T14:25:00Z",
                "created_at": "2024-01-15T10:30:00Z",
                "email_verified": True,
                "provider": "email",
                "security_events": []
            }
        }


class UserDeleteResponse(BaseModel):
    """
    User account deletion response schema with audit information.
    
    This schema provides account deletion confirmation and audit
    information for security and compliance tracking.
    """
    
    user_id: UUID = Field(
        ...,
        description="Deleted user's identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    deletion_type: str = Field(
        ...,
        description="Type of deletion performed (hard/soft)",
        example="soft"
    )
    deleted_at: datetime = Field(
        ...,
        description="Deletion timestamp",
        example="2024-01-20T15:30:00Z"
    )
    cleanup_completed: Dict = Field(
        ...,
        description="Summary of cleanup operations performed",
        example={
            "delete_user_data": True,
            "delete_subscription_data": True,
            "delete_uploaded_files": True,
            "revoke_all_sessions": True
        }
    )
    message: str = Field(
        default="User account deleted successfully",
        description="Deletion confirmation message",
        example="User account deleted successfully"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "deletion_type": "soft",
                "deleted_at": "2024-01-20T15:30:00Z",
                "cleanup_completed": {
                    "delete_user_data": True,
                    "delete_subscription_data": True,
                    "delete_uploaded_files": True,
                    "revoke_all_sessions": True
                },
                "message": "User account deleted successfully"
            }
        }


class EmailVerificationResponse(BaseModel):
    """
    Email verification response schema for admin operations.
    
    This schema provides email verification confirmation for
    administrative email verification operations.
    """
    
    user_id: UUID = Field(
        ...,
        description="User's unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email_verified: bool = Field(
        ...,
        description="Email verification status",
        example=True
    )
    verified_at: datetime = Field(
        ...,
        description="Verification timestamp",
        example="2024-01-20T15:30:00Z"
    )
    verified_by: UUID = Field(
        ...,
        description="Admin user who performed verification",
        example="987fcdeb-51a2-43d1-9876-ba0987654321"
    )
    message: str = Field(
        default="Email verified successfully",
        description="Verification confirmation message",
        example="Email verified successfully"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email_verified": True,
                "verified_at": "2024-01-20T15:30:00Z",
                "verified_by": "987fcdeb-51a2-43d1-9876-ba0987654321",
                "message": "Email verified successfully"
            }
        }


class AccountUnlockResponse(BaseModel):
    """
    Account unlock response schema for admin operations.
    
    This schema provides account unlock confirmation for
    administrative account security management.
    """
    
    user_id: UUID = Field(
        ...,
        description="User's unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    account_locked: bool = Field(
        ...,
        description="Account lock status after operation",
        example=False
    )
    login_attempts_reset: bool = Field(
        ...,
        description="Whether login attempts were reset",
        example=True
    )
    unlocked_at: datetime = Field(
        ...,
        description="Unlock timestamp",
        example="2024-01-20T15:30:00Z"
    )
    unlocked_by: UUID = Field(
        ...,
        description="Admin user who performed unlock",
        example="987fcdeb-51a2-43d1-9876-ba0987654321"
    )
    message: str = Field(
        default="Account unlocked successfully",
        description="Unlock confirmation message",
        example="Account unlocked successfully"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "account_locked": False,
                "login_attempts_reset": True,
                "unlocked_at": "2024-01-20T15:30:00Z",
                "unlocked_by": "987fcdeb-51a2-43d1-9876-ba0987654321",
                "message": "Account unlocked successfully"
            }
        }