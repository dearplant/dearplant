# 📄 File: app/modules/user_management/application/commands/create_user.py
# 🧭 Purpose (Layman Explanation):
# This file defines the "create user" command that contains all the information needed
# to register a new user account in our plant care app, including email, password, and profile details.
#
# 🧪 Purpose (Technical Summary):
# CQRS command implementation for user registration following Core Doc 1.1 Authentication
# and 1.2 Profile specifications with validation, security rules, and proper field mapping.
#
# 🔗 Dependencies:
# - pydantic for command validation and serialization
# - app.modules.user_management.domain.models.user (User domain entity)
# - app.modules.user_management.domain.models.profile (Profile domain entity)
# - Core doc specifications for all required and optional fields
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.command_handlers (CreateUserCommandHandler)
# - app.modules.user_management.presentation.api.v1.auth (registration endpoint)
# - app.modules.user_management.presentation.api.schemas.auth_schemas (API schema conversion)

"""
Create User Command

This module implements the CQRS command for user registration,
following the exact specifications from Core Doc 1.1 (Authentication)
and Core Doc 1.2 (Profile Management).

Command Fields (Core Doc 1.1 Authentication):
- email: User's email address (validated format)
- password: Raw password (will be hashed with bcrypt)
- provider: Authentication provider (email/google/apple)
- provider_id: External provider ID (nullable)

Command Fields (Core Doc 1.2 Profile):
- display_name: User's display name
- bio: User biography (max 500 chars, nullable)
- location: User's location for weather data (nullable)
- timezone: User's timezone (nullable)
- language: Preferred language (default: auto-detect)
- theme: UI theme preference (light/dark/auto, default: auto)
- notification_enabled: Global notification toggle (default: True)

Security and Validation:
- Email format validation and uniqueness
- Password complexity requirements
- Provider validation for OAuth flows
- Bio length limits (500 chars as per core doc)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, validator


class CreateUserCommand(BaseModel):
    """
    Command for creating a new user account with profile.
    
    This command encapsulates all data needed for user registration
    following Core Doc 1.1 (Authentication) and 1.2 (Profile) specifications.
    """
    
    # Core Doc 1.1 Authentication Fields
    email: EmailStr = Field(
        ...,
        description="User's email address (validated format)",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Raw password (will be hashed with bcrypt)",
        example="SecurePassword123!"
    )
    provider: str = Field(
        default="email",
        description="Authentication provider (email/google/apple)",
        example="email"
    )
    provider_id: Optional[str] = Field(
        default=None,
        description="External provider ID (nullable)",
        example="google_123456789"
    )
    
    # Core Doc 1.2 Profile Management Fields
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
        description="User biography (max 500 chars, nullable)",
        example="Plant enthusiast and gardening lover"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's location for weather data (nullable)",
        example="New York, NY"
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's timezone (nullable)",
        example="America/New_York"
    )
    language: str = Field(
        default="auto",
        max_length=10,
        description="Preferred language (default: auto-detect)",
        example="en"
    )
    theme: str = Field(
        default="auto",
        description="UI theme preference (light/dark/auto)",
        example="auto"
    )
    notification_enabled: bool = Field(
        default=True,
        description="Global notification toggle (default: True)",
        example=True
    )
    
    # Optional metadata
    user_agent: Optional[str] = Field(
        default=None,
        description="User agent for registration tracking",
        example="Mozilla/5.0..."
    )
    ip_address: Optional[str] = Field(
        default=None,
        description="IP address for security logging",
        example="192.168.1.1"
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
                "email": "john.doe@example.com",
                "password": "SecurePassword123!",
                "provider": "email",
                "provider_id": None,
                "display_name": "John Doe",
                "bio": "Passionate about plant care and sustainable gardening",
                "location": "San Francisco, CA",
                "timezone": "America/Los_Angeles",
                "language": "en",
                "theme": "auto",
                "notification_enabled": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "ip_address": "192.168.1.100"
            }
        }
    
    @validator('provider')
    def validate_provider(cls, v):
        """
        Validate authentication provider.
        
        Args:
            v: Provider value to validate
            
        Returns:
            str: Validated provider
            
        Raises:
            ValueError: If provider is not supported
        """
        allowed_providers = ["email", "google", "apple"]
        if v not in allowed_providers:
            raise ValueError(f"Provider must be one of: {', '.join(allowed_providers)}")
        return v
    
    @validator('theme')
    def validate_theme(cls, v):
        """
        Validate UI theme preference.
        
        Args:
            v: Theme value to validate
            
        Returns:
            str: Validated theme
            
        Raises:
            ValueError: If theme is not supported
        """
        allowed_themes = ["light", "dark", "auto"]
        if v not in allowed_themes:
            raise ValueError(f"Theme must be one of: {', '.join(allowed_themes)}")
        return v
    
    @validator('password')
    def validate_password_complexity(cls, v):
        """
        Validate password complexity requirements.
        
        Args:
            v: Password to validate
            
        Returns:
            str: Validated password
            
        Raises:
            ValueError: If password doesn't meet complexity requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for required character types
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        
        return v
    
    @validator('bio')
    def validate_bio_length(cls, v):
        """
        Validate bio length according to Core Doc 1.2 (max 500 chars).
        
        Args:
            v: Bio text to validate
            
        Returns:
            Optional[str]: Validated bio
            
        Raises:
            ValueError: If bio exceeds 500 characters
        """
        if v is not None and len(v) > 500:
            raise ValueError("Bio must not exceed 500 characters")
        return v
    
    @validator('email')
    def validate_email_format(cls, v):
        """
        Additional email validation beyond EmailStr.
        
        Args:
            v: Email to validate
            
        Returns:
            str: Validated email (lowercase)
        """
        # Convert to lowercase for consistency
        email_lower = v.lower()
        
        # Basic domain validation
        domain = email_lower.split('@')[1]
        if '.' not in domain:
            raise ValueError("Invalid email domain format")
        
        return email_lower
    
    def to_domain_entities(self) -> tuple:
        """
        Convert command to domain entities for creation.
        
        Returns:
            tuple: (User domain entity data, Profile domain entity data)
        """
        # Generate UUIDs for new entities
        user_id_obj = uuid4()
        profile_id_obj = uuid4()
        now = datetime.utcnow()
        
        # User entity data (Core Doc 1.1)
        user_data = {
            # ✅ FIX: Convert the UUID object to a string
            "user_id": str(user_id_obj),
            "email": self.email,
            "password_hash": None,  # Will be set by auth service
            "created_at": now,
            "last_login_at": None,
            "email_verified": False,  # Requires verification
            "reset_token": None,
            "reset_token_expires": None,
            "failed_login_attempts": 0,
            "account_locked": None,
            "provider": self.provider,
            "provider_id": self.provider_id,
            "account_locked":False,
            "notification_enabled":self.notification_enabled
        }
        
        # Profile entity data (Core Doc 1.2)
        profile_data = {
            # ✅ FIX: Convert both UUID objects to strings
            "profile_id": str(profile_id_obj),
            "user_id": str(user_id_obj),
            "display_name": self.display_name,
            "profile_photo": None,  # Set during photo upload
            "bio": self.bio,
            "location": self.location,
            "timezone": self.timezone,
            "language": self.language,
            "theme": self.theme,
            "notification_enabled": self.notification_enabled,
            "created_at": now,
            "updated_at": now,
            "experience_level": "beginner"
        }
        
        return user_data, profile_data
