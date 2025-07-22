# 📄 File: app/modules/user_management/application/dto/user_dto.py
# 🧭 Purpose (Layman Explanation):
# This file defines standardized data packages for user account information that can be safely
# sent between different parts of our plant care app while hiding sensitive data like passwords.
#
# 🧪 Purpose (Technical Summary):
# User data transfer objects implementing Core Doc 1.1 Authentication specifications with
# security filtering, validation, and serialization for safe data exchange between layers.
#
# 🔗 Dependencies:
# - pydantic for DTO validation and serialization
# - app.modules.user_management.domain.models.user (User domain entity)
# - Core doc 1.1 specifications for all user fields and security requirements
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers (handlers return user DTOs)
# - app.modules.user_management.presentation.api.v1 (API endpoints use user DTOs)
# - app.modules.user_management.presentation.api.schemas (API schema conversion)

"""
User Data Transfer Objects (DTOs)

This module implements DTOs for user management following Core Doc 1.1
(Authentication) specifications with proper security filtering and validation.

DTO Classes:
- UserDTO: Complete user data representation
- CreateUserDTO: Input validation for user creation
- UpdateUserDTO: Input validation for user updates
- UserResponseDTO: API response formatting with security filtering
- UserListResponseDTO: Paginated user list responses
- UserSecurityDTO: Admin-only security information

Security Features:
- Password hash never exposed in any DTO
- Reset tokens filtered based on access level
- Login attempts visible only to authorized users
- Account status information for admin users
- Email verification status handling

All DTOs follow Core Doc 1.1 field specifications and implement
proper validation and serialization for safe data transfer.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


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


class UserDTO(BaseModel):
    """
    Complete user data transfer object following Core Doc 1.1.
    
    This DTO represents the full user entity data structure
    for internal application use with all security fields.
    """
    
    # Core Doc 1.1 Authentication Fields
    user_id: UUID = Field(
        ...,
        description="Unique identifier for each user",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: str = Field(
        ...,
        description="User's email address (validated format)",
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
    login_attempts: int = Field(
        ...,
        ge=0,
        description="Failed login attempt counter",
        example=0
    )
    account_locked: bool = Field(
        ...,
        description="Account lock status",
        example=False
    )
    provider: UserProvider = Field(
        ...,
        description="Authentication provider (email/google/apple)",
        example=UserProvider.EMAIL
    )
    provider_id: Optional[str] = Field(
        default=None,
        description="External provider ID",
        example="google_123456789"
    )
    
    # Security fields (filtered in responses)
    reset_token: Optional[str] = Field(
        default=None,
        description="Password reset token (admin only)",
        example=None
    )
    reset_token_expires: Optional[datetime] = Field(
        default=None,
        description="Reset token expiration (admin only)",
        example=None
    )
    
    class Config:
        """Pydantic configuration."""
        # Use enum values in schema
        use_enum_values = True
        # Allow JSON serialization of datetime
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        # Example for API documentation
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "created_at": "2024-01-15T10:30:00Z",
                "last_login": "2024-01-20T14:25:00Z",
                "email_verified": True,
                "login_attempts": 0,
                "account_locked": False,
                "provider": "email",
                "provider_id": None,
                "reset_token": None,
                "reset_token_expires": None
            }
        }
    
    def get_status(self) -> UserStatus:
        """
        Get user account status based on current state.
        
        Returns:
            UserStatus: Current account status
        """
        if self.account_locked:
            return UserStatus.LOCKED
        
        if not self.email_verified:
            return UserStatus.PENDING_VERIFICATION
        
        return UserStatus.ACTIVE
    
    def is_oauth_user(self) -> bool:
        """
        Check if user uses OAuth authentication.
        
        Returns:
            bool: True if OAuth user
        """
        return self.provider != UserProvider.EMAIL
    
    def has_recent_login(self, days: int = 30) -> bool:
        """
        Check if user has logged in recently.
        
        Args:
            days: Number of days to consider as recent
            
        Returns:
            bool: True if logged in within the specified days
        """
        if not self.last_login:
            return False
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.last_login > cutoff_date


class CreateUserDTO(BaseModel):
    """
    Input DTO for user creation requests.
    
    This DTO validates input data for user registration
    following Core Doc 1.1 specifications.
    """
    
    email: str = Field(
        ...,
        description="User's email address",
        example="newuser@example.com"
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's display name",
        example="John Doe"
    )
    provider: UserProvider = Field(
        default=UserProvider.EMAIL,
        description="Authentication provider",
        example=UserProvider.EMAIL
    )
    provider_id: Optional[str] = Field(
        default=None,
        description="External provider ID",
        example=None
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "display_name": "John Doe",
                "provider": "email",
                "provider_id": None
            }
        }


class UpdateUserDTO(BaseModel):
    """
    Input DTO for user update requests.
    
    This DTO validates input data for user updates
    with optional field support.
    """
    
    email: Optional[str] = Field(
        default=None,
        description="Updated email address",
        example="updated@example.com"
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
                "email": "updated@example.com",
                "email_verified": True,
                "account_locked": False
            }
        }


class UserResponseDTO(BaseModel):
    """
    API response DTO for user data with security filtering.
    
    This DTO provides safe user data for API responses
    with field filtering based on access level.
    """
    
    user_id: UUID = Field(
        ...,
        description="User identifier",
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
    def from_domain(cls, user: "User", access_level: str = "public") -> "UserResponseDTO":
        """
        Create response DTO from domain User entity.
        
        Args:
            user: User domain entity
            access_level: Access level for field filtering ("public", "self", "admin")
            
        Returns:
            UserResponseDTO: Response DTO with appropriate filtering
        """
        # Determine status from user state
        if user.account_locked:
            status = UserStatus.LOCKED
        elif not user.email_verified:
            status = UserStatus.PENDING_VERIFICATION
        else:
            status = UserStatus.ACTIVE
        
        # Base response data
        response_data = {
            "user_id": user.user_id,
            "email": user.email,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "email_verified": user.email_verified,
            "provider": UserProvider(user.provider),
            "status": status,
        }
        
        # Add fields based on access level
        if access_level in ["self", "admin"]:
            response_data["login_attempts"] = user.login_attempts
        
        if access_level == "admin":
            response_data["account_locked"] = user.account_locked
        
        return cls(**response_data)


class UserListResponseDTO(BaseModel):
    """
    Paginated user list response DTO.
    
    This DTO provides paginated user data for list endpoints
    with metadata for navigation.
    """
    
    users: List[UserResponseDTO] = Field(
        ...,
        description="List of users",
        example=[]
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of users",
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
                "has_previous": False
            }
        }


class UserSecurityDTO(BaseModel):
    """
    Admin-only security information DTO.
    
    This DTO provides sensitive security information
    for administrative use only.
    """
    
    user_id: UUID = Field(
        ...,
        description="User identifier",
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
    last_password_change: Optional[datetime] = Field(
        default=None,
        description="Last password change timestamp",
        example="2024-01-10T09:15:00Z"
    )
    security_events: List[dict] = Field(
        default_factory=list,
        description="Recent security events",
        example=[]
    )
    
    class Config:
        """Pydantic configuration."""
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
                "last_password_change": "2024-01-10T09:15:00Z",
                "security_events": []
            }
        }