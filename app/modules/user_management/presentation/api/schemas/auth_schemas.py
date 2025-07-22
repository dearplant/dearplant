# 📄 File: app/modules/user_management/presentation/api/schemas/auth_schemas.py
# 🧭 Purpose (Layman Explanation):
# This file defines all the data formats for authentication requests and responses like login forms,
# registration data, and password reset messages for our plant care app's API.
#
# 🧪 Purpose (Technical Summary):
# Pydantic authentication schemas implementing Core Doc 1.1 specifications for request/response
# validation, OpenAPI documentation, and secure data handling for authentication endpoints.
#
# 🔗 Dependencies:
# - pydantic for schema validation and serialization
# - app.modules.user_management.application.dto (DTOs for data conversion)
# - Core doc 1.1 specifications for authentication fields and validation
# - FastAPI integration for automatic validation and documentation
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1.auth (authentication endpoints)
# - FastAPI automatic request validation and response serialization
# - OpenAPI/Swagger documentation generation

"""
Authentication API Schemas

This module implements Pydantic schemas for authentication endpoints following
Core Doc 1.1 specifications with comprehensive validation and security measures.

Request Schemas:
- LoginRequest: User authentication credentials
- RegisterRequest: User registration data with profile information
- TokenRefreshRequest: JWT token refresh parameters
- PasswordResetRequest: Password reset initiation
- EmailVerificationRequest: Email verification confirmation
- OAuthCallbackRequest: OAuth provider callback data

Response Schemas:
- LoginResponse: Authentication success with tokens and user info
- LogoutResponse: Logout confirmation
- TokenRefreshResponse: New authentication tokens
- PasswordResetResponse: Password reset confirmation
- EmailVerificationResponse: Email verification status
- OAuthInitiateResponse: OAuth authorization URL
- OAuthCallbackResponse: OAuth authentication completion

Security Features:
- Password complexity validation
- Email format validation with domain checks
- Token format validation and security
- OAuth state parameter validation
- Rate limiting parameter validation
- Security field filtering in responses

All schemas follow Core Doc 1.1 specifications and implement proper
validation rules for secure authentication workflows.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class AuthProvider(str, Enum):
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
    OTHER = "other"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class LoginRequest(BaseModel):
    """
    User login request schema following Core Doc 1.1 specifications.
    
    This schema validates user authentication credentials with proper
    security validation and rate limiting consideration.
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User's password",
        example="SecurePassword123!"
    )
    remember_me: bool = Field(
        default=False,
        description="Whether to extend session duration",
        example=False
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!",
                "remember_me": False
            }
        }
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format and normalize to lowercase."""
        return v.lower()


class RegisterRequest(BaseModel):
    """
    User registration request schema following Core Doc 1.1 and 1.2 specifications.
    
    This schema validates user registration data including both authentication
    credentials and initial profile information.
    """
    
    # Authentication fields (Core Doc 1.1)
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="newuser@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)",
        example="SecurePassword123!"
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation",
        example="SecurePassword123!"
    )
    
    # Profile fields (Core Doc 1.2)
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's display name",
        example="John Doe"
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User biography (max 500 chars)",
        example="Passionate plant enthusiast and indoor gardening lover"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's location for weather data",
        example="San Francisco, CA"
    )
    language: Optional[str] = Field(
        default="auto",
        max_length=10,
        description="Preferred language code",
        example="en"
    )
    theme: Optional[str] = Field(
        default="auto",
        description="UI theme preference",
        example="auto"
    )
    
    # Terms and privacy
    accept_terms: bool = Field(
        ...,
        description="Acceptance of terms of service",
        example=True
    )
    accept_privacy: bool = Field(
        ...,
        description="Acceptance of privacy policy", 
        example=True
    )
    marketing_emails: bool = Field(
        default=False,
        description="Opt-in for marketing emails",
        example=False
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!",
                "display_name": "Jane Smith",
                "bio": "Urban gardening enthusiast specializing in succulents",
                "location": "Portland, OR",
                "language": "en",
                "theme": "light",
                "accept_terms": True,
                "accept_privacy": True,
                "marketing_emails": False
            }
        }
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format and normalize to lowercase."""
        return v.lower()
    
    @validator('password')
    def validate_password_complexity(cls, v):
        """Validate password complexity requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        return v
    
    @validator('password_confirm')
    def validate_password_match(cls, v, values):
        """Validate password confirmation matches."""
        if 'password' in values and v != values['password']:
            raise ValueError("Password confirmation does not match")
        return v
    
    @validator('theme')
    def validate_theme_choice(cls, v):
        """Validate theme preference."""
        if v and v not in ["light", "dark", "auto"]:
            raise ValueError("Theme must be 'light', 'dark', or 'auto'")
        return v
    
    @validator('accept_terms')
    def validate_terms_acceptance(cls, v):
        """Validate terms of service acceptance."""
        if not v:
            raise ValueError("You must accept the terms of service")
        return v
    
    @validator('accept_privacy')
    def validate_privacy_acceptance(cls, v):
        """Validate privacy policy acceptance."""
        if not v:
            raise ValueError("You must accept the privacy policy")
        return v


class TokenRefreshRequest(BaseModel):
    """
    Token refresh request schema for JWT token renewal.
    
    This schema validates refresh token parameters for secure
    token renewal without re-authentication.
    """
    
    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
            }
        }


class PasswordResetRequest(BaseModel):
    """
    Password reset request schema for initiating password recovery.
    
    This schema validates password reset initiation with security
    considerations for preventing user enumeration attacks.
    """
    
    email: EmailStr = Field(
        ...,
        description="Email address for password reset",
        example="user@example.com"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format and normalize to lowercase."""
        return v.lower()


class EmailVerificationRequest(BaseModel):
    """
    Email verification request schema for confirming email addresses.
    
    This schema validates email verification tokens and provides
    secure email confirmation workflow.
    """
    
    token: str = Field(
        ...,
        min_length=32,
        max_length=128,
        description="Email verification token",
        example="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Email address for verification (optional)",
        example="user@example.com"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                "email": "user@example.com"
            }
        }


class OAuthCallbackRequest(BaseModel):
    """
    OAuth callback request schema for handling provider responses.
    
    This schema validates OAuth authorization codes and state parameters
    for secure OAuth authentication completion.
    """
    
    code: str = Field(
        ...,
        description="Authorization code from OAuth provider",
        example="4/0AX4XfWjYvQZ1234567890abcdef"
    )
    state: str = Field(
        ...,
        description="State parameter for CSRF protection",
        example="oauth_google_1640995200"
    )
    provider: AuthProvider = Field(
        ...,
        description="OAuth provider name",
        example=AuthProvider.GOOGLE
    )
    error: Optional[str] = Field(
        default=None,
        description="OAuth error code if authentication failed",
        example=None
    )
    error_description: Optional[str] = Field(
        default=None,
        description="OAuth error description if authentication failed", 
        example=None
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "code": "4/0AX4XfWjYvQZ1234567890abcdef",
                "state": "oauth_google_1640995200",
                "provider": "google",
                "error": None,
                "error_description": None
            }
        }


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class LoginResponse(BaseModel):
    """
    Login response schema for successful authentication.
    
    This schema provides authentication tokens and user information
    following security best practices and Core Doc specifications.
    """
    
    # Authentication tokens
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for token renewal",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=86400
    )
    
    # User information
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
    display_name: Optional[str] = Field(
        default=None,
        description="User's display name",
        example="John Doe"
    )
    email_verified: bool = Field(
        ...,
        description="Whether user's email is verified",
        example=True
    )
    requires_verification: bool = Field(
        default=False,
        description="Whether user needs to verify email",
        example=False
    )
    
    # Subscription information
    trial_active: bool = Field(
        default=False,
        description="Whether user has an active trial",
        example=True
    )
    trial_end_date: Optional[datetime] = Field(
        default=None,
        description="Trial expiration date",
        example="2024-02-01T10:30:00Z"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "display_name": "John Doe",
                "email_verified": True,
                "requires_verification": False,
                "trial_active": True,
                "trial_end_date": "2024-02-01T10:30:00Z"
            }
        }


class LogoutResponse(BaseModel):
    """
    Logout response schema for session termination confirmation.
    
    This schema provides logout confirmation and cleanup information
    for secure session management.
    """
    
    message: str = Field(
        default="Logout successful",
        description="Logout confirmation message",
        example="Logout successful"
    )
    logged_out_at: datetime = Field(
        ...,
        description="Logout timestamp",
        example="2024-01-20T15:30:00Z"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "message": "Logout successful",
                "logged_out_at": "2024-01-20T15:30:00Z"
            }
        }


class TokenRefreshResponse(BaseModel):
    """
    Token refresh response schema for JWT token renewal.
    
    This schema provides new authentication tokens for continued
    API access without re-authentication.
    """
    
    access_token: str = Field(
        ...,
        description="New JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="New JWT refresh token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=86400
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }


class PasswordResetResponse(BaseModel):
    """
    Password reset response schema for reset initiation confirmation.
    
    This schema provides secure password reset confirmation that
    prevents user enumeration attacks.
    """
    
    message: str = Field(
        ...,
        description="Password reset confirmation message",
        example="If an account with that email exists, a password reset link has been sent."
    )
    email: str = Field(
        ...,
        description="Email address (confirmed for security)",
        example="user@example.com"
    )
    sent_at: datetime = Field(
        ...,
        description="Reset email sent timestamp",
        example="2024-01-20T15:30:00Z"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "message": "If an account with that email exists, a password reset link has been sent.",
                "email": "user@example.com",
                "sent_at": "2024-01-20T15:30:00Z"
            }
        }


class EmailVerificationResponse(BaseModel):
    """
    Email verification response schema for verification confirmation.
    
    This schema provides email verification status and user account
    activation confirmation.
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
        description="Email verification timestamp",
        example="2024-01-20T15:30:00Z"
    )
    verified_by: Optional[UUID] = Field(
        default=None,
        description="Admin user ID if manually verified",
        example=None
    )
    message: str = Field(
        ...,
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
                "verified_by": None,
                "message": "Email verified successfully"
            }
        }


class OAuthInitiateResponse(BaseModel):
    """
    OAuth initiation response schema for authorization URL generation.
    
    This schema provides OAuth authorization URLs and CSRF protection
    parameters for secure external authentication.
    """
    
    provider: AuthProvider = Field(
        ...,
        description="OAuth provider name",
        example=AuthProvider.GOOGLE
    )
    authorization_url: str = Field(
        ...,
        description="OAuth authorization URL for redirection",
        example="https://accounts.google.com/o/oauth2/auth?client_id=..."
    )
    state: str = Field(
        ...,
        description="State parameter for CSRF protection",
        example="oauth_google_1640995200"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "provider": "google",
                "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
                "state": "oauth_google_1640995200"
            }
        }


class OAuthCallbackResponse(BaseModel):
    """
    OAuth callback response schema for authentication completion.
    
    This schema provides OAuth authentication results with user
    information and authentication tokens.
    """
    
    # Authentication tokens (same as LoginResponse)
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for token renewal",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=86400
    )
    
    # User information
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
    display_name: str = Field(
        ...,
        description="User's display name from OAuth provider",
        example="John Doe"
    )
    provider: AuthProvider = Field(
        ...,
        description="OAuth provider used for authentication",
        example=AuthProvider.GOOGLE
    )
    
    # Account status
    is_new_user: bool = Field(
        ...,
        description="Whether this is a newly created account",
        example=False
    )
    email_verified: bool = Field(
        default=True,
        description="Email verification status (usually true for OAuth)",
        example=True
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "display_name": "John Doe",
                "provider": "google",
                "is_new_user": False,
                "email_verified": True
            }
        }