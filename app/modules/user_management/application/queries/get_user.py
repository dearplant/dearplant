# 📄 File: app/modules/user_management/application/queries/get_user.py
# 🧭 Purpose (Layman Explanation):
# This file defines the "get user" query that contains all the information needed
# to retrieve a user's account details safely, with proper security checks and filtering.
#
# 🧪 Purpose (Technical Summary):
# CQRS query implementation for user data retrieval following Core Doc 1.1 Authentication
# specifications with security validation, filtering options, and proper data access control.
#
# 🔗 Dependencies:
# - pydantic for query validation and serialization
# - app.modules.user_management.domain.models.user (User domain entity)
# - Core doc 1.1 specifications for user fields and access control
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.query_handlers (GetUserQueryHandler)
# - app.modules.user_management.presentation.api.v1.users (user retrieval endpoints)
# - app.modules.user_management.presentation.api.schemas.user_schemas (API schema conversion)

"""
Get User Query

This module implements the CQRS query for user data retrieval,
following the exact specifications from Core Doc 1.1 (Authentication)
with proper security controls and data access validation.

Query Fields:
- user_id: UUID of the user to retrieve (optional if using other identifiers)
- email: Email address lookup (optional, admin/self only)
- provider_lookup: OAuth provider lookup (provider + provider_id)
- include_security_data: Include sensitive fields (admin only)
- include_login_history: Include login attempt data (admin/self only)
- requesting_user_id: UUID of user making the request (for security)

Security Controls (Core Doc 1.1):
- Users can only access their own data unless admin
- Email lookup restricted to admin or self
- Security data (login attempts, tokens) restricted to admin
- Account locked status visible to admin only
- Provider information filtered based on access level

Response Filtering:
- Sensitive fields filtered based on requester permissions
- Password hash never included in response
- Reset tokens filtered out for security
- Login attempts visible only to authorized users
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class UserLookupType(str, Enum):
    """Enumeration of user lookup methods."""
    BY_ID = "by_id"
    BY_EMAIL = "by_email"
    BY_PROVIDER = "by_provider"


class SecurityLevel(str, Enum):
    """Security access levels for data filtering."""
    PUBLIC = "public"          # Basic user info only
    SELF = "self"             # User's own data
    ADMIN = "admin"           # Full administrative access


class GetUserQuery(BaseModel):
    """
    Query for retrieving user account information.
    
    This query encapsulates user lookup parameters following
    Core Doc 1.1 (Authentication) specifications with proper
    security controls and access validation.
    """
    
    # Primary lookup fields (at least one required)
    user_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the user to retrieve",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: Optional[str] = Field(
        default=None,
        description="Email address lookup (admin/self only)",
        example="user@example.com"
    )
    
    # OAuth provider lookup
    provider: Optional[str] = Field(
        default=None,
        description="OAuth provider for lookup",
        example="google"
    )
    provider_id: Optional[str] = Field(
        default=None,
        description="OAuth provider ID for lookup",
        example="google_123456789"
    )
    
    # Security and access control
    requesting_user_id: UUID = Field(
        ...,
        description="UUID of user making the request (for security)",
        example="987fcdeb-51a2-43d1-9876-ba0987654321"
    )
    is_admin_request: bool = Field(
        default=False,
        description="Whether request is from admin user",
        example=False
    )
    
    # Data inclusion options
    include_security_data: bool = Field(
        default=False,
        description="Include sensitive security fields (admin only)",
        example=False
    )
    include_login_history: bool = Field(
        default=False,
        description="Include login attempt data (admin/self only)",
        example=False
    )
    include_provider_data: bool = Field(
        default=True,
        description="Include OAuth provider information",
        example=True
    )
    include_timestamps: bool = Field(
        default=True,
        description="Include creation and login timestamps",
        example=True
    )
    
    # Response filtering
    exclude_sensitive_fields: bool = Field(
        default=True,
        description="Exclude sensitive fields from response",
        example=True
    )
    
    class Config:
        """Pydantic configuration."""
        # Allow arbitrary types for complex validations
        arbitrary_types_allowed = True
        # Use enum values in schema
        use_enum_values = True
        # Example for API documentation
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "requesting_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "is_admin_request": False,
                "include_security_data": False,
                "include_login_history": False,
                "include_provider_data": True,
                "include_timestamps": True,
                "exclude_sensitive_fields": True
            }
        }
    
    @validator('email')
    def validate_email_format(cls, v):
        """
        Validate email format for lookup.
        
        Args:
            v: Email to validate
            
        Returns:
            Optional[str]: Validated email (lowercase)
        """
        if v is not None:
            # Convert to lowercase for consistent lookup
            email_lower = v.lower()
            
            # Basic email format validation
            if '@' not in email_lower or '.' not in email_lower.split('@')[1]:
                raise ValueError("Invalid email format for lookup")
            
            return email_lower
        return v
    
    @validator('provider')
    def validate_provider_name(cls, v):
        """
        Validate OAuth provider name.
        
        Args:
            v: Provider to validate
            
        Returns:
            Optional[str]: Validated provider
        """
        if v is not None:
            allowed_providers = ["email", "google", "apple"]
            if v not in allowed_providers:
                raise ValueError(f"Provider must be one of: {', '.join(allowed_providers)}")
        return v
    
    @validator('provider_id')
    def validate_provider_dependency(cls, v, values):
        """
        Validate that provider_id is only provided with provider.
        
        Args:
            v: Provider ID to validate
            values: Other field values
            
        Returns:
            Optional[str]: Validated provider ID
        """
        if v is not None and values.get('provider') is None:
            raise ValueError("provider_id requires provider to be specified")
        return v
    
    def get_lookup_type(self) -> UserLookupType:
        """
        Determine the type of user lookup being performed.
        
        Returns:
            UserLookupType: Type of lookup operation
            
        Raises:
            ValueError: If no valid lookup parameters provided
        """
        if self.user_id is not None:
            return UserLookupType.BY_ID
        
        if self.email is not None:
            return UserLookupType.BY_EMAIL
        
        if self.provider is not None and self.provider_id is not None:
            return UserLookupType.BY_PROVIDER
        
        raise ValueError("Must provide user_id, email, or provider+provider_id for lookup")
    
    def get_security_level(self) -> SecurityLevel:
        """
        Determine the security access level for this request.
        
        Returns:
            SecurityLevel: Access level for data filtering
        """
        if self.is_admin_request:
            return SecurityLevel.ADMIN
        
        # Check if user is requesting their own data
        if self.user_id == self.requesting_user_id:
            return SecurityLevel.SELF
        
        return SecurityLevel.PUBLIC
    
    def is_authorized_for_email_lookup(self) -> bool:
        """
        Check if request is authorized for email-based lookup.
        
        Returns:
            bool: True if authorized for email lookup
        """
        security_level = self.get_security_level()
        return security_level in [SecurityLevel.ADMIN, SecurityLevel.SELF]
    
    def is_authorized_for_security_data(self) -> bool:
        """
        Check if request is authorized for security data access.
        
        Returns:
            bool: True if authorized for security data
        """
        return self.get_security_level() == SecurityLevel.ADMIN
    
    def is_authorized_for_login_history(self) -> bool:
        """
        Check if request is authorized for login history access.
        
        Returns:
            bool: True if authorized for login history
        """
        security_level = self.get_security_level()
        return security_level in [SecurityLevel.ADMIN, SecurityLevel.SELF]
    
    def get_filtered_fields(self) -> List[str]:
        """
        Get list of fields that should be excluded from response.
        
        Returns:
            List[str]: List of field names to exclude
        """
        excluded_fields = []
        security_level = self.get_security_level()
        
        # Always exclude password hash
        excluded_fields.append("password_hash")
        
        # Security data filtering
        if not self.is_authorized_for_security_data():
            excluded_fields.extend([
                "reset_token",
                "reset_token_expires",
            ])
        
        # Login history filtering
        if not self.is_authorized_for_login_history():
            excluded_fields.extend([
                "login_attempts",
            ])
        
        # Admin-only fields
        if security_level != SecurityLevel.ADMIN:
            excluded_fields.extend([
                "account_locked",
            ])
        
        # Provider data filtering
        if not self.include_provider_data:
            excluded_fields.extend([
                "provider",
                "provider_id",
            ])
        
        # Timestamp filtering
        if not self.include_timestamps:
            excluded_fields.extend([
                "created_at",
                "last_login",
            ])
        
        return excluded_fields
    
    def validate_authorization(self) -> None:
        """
        Validate that the request is authorized based on lookup type and security level.
        
        Raises:
            ValueError: If request is not authorized
        """
        lookup_type = self.get_lookup_type()
        security_level = self.get_security_level()
        
        # Email lookup authorization
        if lookup_type == UserLookupType.BY_EMAIL:
            if not self.is_authorized_for_email_lookup():
                raise ValueError("Email lookup requires admin privileges or self-access")
        
        # Security data authorization
        if self.include_security_data and not self.is_authorized_for_security_data():
            raise ValueError("Security data access requires admin privileges")
        
        # Login history authorization
        if self.include_login_history and not self.is_authorized_for_login_history():
            raise ValueError("Login history access requires admin privileges or self-access")
    
    def to_domain_lookup_params(self) -> dict:
        """
        Convert query to domain lookup parameters.
        
        Returns:
            dict: Lookup parameters for repository
            
        Raises:
            ValueError: If query validation fails
        """
        # Validate authorization first
        self.validate_authorization()
        
        lookup_type = self.get_lookup_type()
        
        lookup_params = {
            "lookup_type": lookup_type.value,
            "requesting_user_id": self.requesting_user_id,
            "security_level": self.get_security_level().value,
            "filtered_fields": self.get_filtered_fields(),
        }
        
        # Add lookup-specific parameters
        if lookup_type == UserLookupType.BY_ID:
            lookup_params["user_id"] = self.user_id
        
        elif lookup_type == UserLookupType.BY_EMAIL:
            lookup_params["email"] = self.email
        
        elif lookup_type == UserLookupType.BY_PROVIDER:
            lookup_params.update({
                "provider": self.provider,
                "provider_id": self.provider_id,
            })
        
        return lookup_params