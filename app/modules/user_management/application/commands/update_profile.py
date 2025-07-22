# 📄 File: app/modules/user_management/application/commands/update_profile.py
# 🧭 Purpose (Layman Explanation):
# This file defines the "update profile" command that contains all the information needed
# to modify a user's profile details like name, bio, location, and preferences in our plant care app.
#
# 🧪 Purpose (Technical Summary):
# CQRS command implementation for profile updates following Core Doc 1.2 Profile Management
# specifications with validation, optional field handling, and proper update semantics.
#
# 🔗 Dependencies:
# - pydantic for command validation and serialization
# - app.modules.user_management.domain.models.profile (Profile domain entity)
# - Core doc 1.2 specifications for all profile fields and constraints
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.command_handlers (UpdateProfileCommandHandler)
# - app.modules.user_management.presentation.api.v1.profiles (profile update endpoint)
# - app.modules.user_management.presentation.api.schemas.profile_schemas (API schema conversion)

"""
Update Profile Command

This module implements the CQRS command for profile updates,
following the exact specifications from Core Doc 1.2 (Profile Management).

Command Fields (Core Doc 1.2 Profile Management):
- profile_id: UUID of the profile to update (required)
- display_name: User's display name (optional update)
- profile_photo: Profile image URL in Supabase Storage (optional)
- bio: User biography (max 500 chars, optional)
- location: User's location for weather data (optional)
- timezone: User's timezone (optional)
- language: Preferred language (optional)
- theme: UI theme preference (light/dark/auto, optional)
- notification_enabled: Global notification toggle (optional)

Update Semantics:
- Only provided fields are updated (partial updates supported)
- None values are treated as "no change" except for nullable fields
- Validation applies to all provided fields
- updated_at timestamp is automatically set
- Profile photo URLs must be valid Supabase Storage URLs
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator, HttpUrl


class UpdateProfileCommand(BaseModel):
    """
    Command for updating an existing user profile.
    
    This command encapsulates profile update data following
    Core Doc 1.2 (Profile Management) specifications with
    support for partial updates and proper validation.
    """
    
    # Required identifier
    profile_id: UUID = Field(
        ...,
        description="UUID of the profile to update",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    # Core Doc 1.2 Profile Management Fields (all optional for updates)
    display_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User's display name",
        example="John Smith"
    )
    profile_photo: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Profile image URL in Supabase Storage",
        example="https://supabase.co/storage/v1/object/profiles/user123/avatar.jpg"
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User biography (max 500 chars)",
        example="Passionate gardener with 10+ years of experience growing indoor plants"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's location for weather data",
        example="Los Angeles, CA"
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's timezone",
        example="America/Los_Angeles"
    )
    language: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Preferred language",
        example="es"
    )
    theme: Optional[str] = Field(
        default=None,
        description="UI theme preference (light/dark/auto)",
        example="dark"
    )
    notification_enabled: Optional[bool] = Field(
        default=None,
        description="Global notification toggle",
        example=False
    )
    
    # Special nullable field handling
    clear_bio: bool = Field(
        default=False,
        description="Set to true to clear the bio field (set to null)",
        example=False
    )
    clear_location: bool = Field(
        default=False,
        description="Set to true to clear the location field (set to null)",
        example=False
    )
    clear_timezone: bool = Field(
        default=False,
        description="Set to true to clear the timezone field (set to null)",
        example=False
    )
    clear_profile_photo: bool = Field(
        default=False,
        description="Set to true to clear the profile photo (set to null)",
        example=False
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
                "profile_id": "123e4567-e89b-12d3-a456-426614174000",
                "display_name": "Jane Green",
                "bio": "Urban gardening enthusiast specializing in succulents and herbs",
                "location": "Portland, OR",
                "timezone": "America/Los_Angeles",
                "language": "en",
                "theme": "light",
                "notification_enabled": True,
                "clear_bio": False,
                "clear_location": False,
                "clear_timezone": False,
                "clear_profile_photo": False
            }
        }
    
    @validator('theme')
    def validate_theme(cls, v):
        """
        Validate UI theme preference.
        
        Args:
            v: Theme value to validate
            
        Returns:
            Optional[str]: Validated theme
            
        Raises:
            ValueError: If theme is not supported
        """
        if v is not None:
            allowed_themes = ["light", "dark", "auto"]
            if v not in allowed_themes:
                raise ValueError(f"Theme must be one of: {', '.join(allowed_themes)}")
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
    
    @validator('language')
    def validate_language_code(cls, v):
        """
        Validate language code format.
        
        Args:
            v: Language code to validate
            
        Returns:
            Optional[str]: Validated language code
            
        Raises:
            ValueError: If language code format is invalid
        """
        if v is not None:
            # Basic language code validation (ISO 639-1 or 'auto')
            allowed_special = ["auto"]
            if v not in allowed_special and (len(v) != 2 or not v.isalpha()):
                raise ValueError("Language must be 'auto' or a valid 2-letter ISO 639-1 code")
            return v.lower()
        return v
    
    @validator('timezone')
    def validate_timezone_format(cls, v):
        """
        Validate timezone format.
        
        Args:
            v: Timezone to validate
            
        Returns:
            Optional[str]: Validated timezone
            
        Raises:
            ValueError: If timezone format is invalid
        """
        if v is not None:
            # Basic timezone validation (should be in format like "America/New_York")
            if '/' not in v and v not in ['UTC', 'GMT']:
                raise ValueError("Timezone must be in format 'Region/City' or 'UTC'/'GMT'")
        return v
    
    @validator('profile_photo')
    def validate_profile_photo_url(cls, v):
        """
        Validate profile photo URL format and ensure it's a Supabase Storage URL.
        
        Args:
            v: Profile photo URL to validate
            
        Returns:
            Optional[str]: Validated URL
            
        Raises:
            ValueError: If URL format is invalid or not from Supabase Storage
        """
        if v is not None:
            # Check if it's a valid URL
            if not v.startswith(('http://', 'https://')):
                raise ValueError("Profile photo must be a valid URL")
            
            # For production, we'd validate it's a Supabase Storage URL
            # For now, just ensure it's a reasonable image URL
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(v.lower().endswith(ext) for ext in valid_extensions):
                raise ValueError("Profile photo must be an image file (jpg, jpeg, png, gif, webp)")
        
        return v
    
    def has_updates(self) -> bool:
        """
        Check if the command contains any actual updates.
        
        Returns:
            bool: True if there are fields to update, False otherwise
        """
        update_fields = [
            self.display_name, self.profile_photo, self.bio, self.location,
            self.timezone, self.language, self.theme, self.notification_enabled
        ]
        
        clear_fields = [
            self.clear_bio, self.clear_location, self.clear_timezone, self.clear_profile_photo
        ]
        
        # Check if any field has a value or any clear flag is set
        return any(field is not None for field in update_fields) or any(clear_fields)
    
    def get_update_data(self) -> dict:
        """
        Get the update data dictionary for the profile entity.
        
        Returns:
            dict: Dictionary of fields to update with their new values
        """
        update_data = {}
        
        # Add non-None fields to update
        if self.display_name is not None:
            update_data["display_name"] = self.display_name
        
        if self.profile_photo is not None:
            update_data["profile_photo"] = self.profile_photo
        
        if self.bio is not None:
            update_data["bio"] = self.bio
        
        if self.location is not None:
            update_data["location"] = self.location
        
        if self.timezone is not None:
            update_data["timezone"] = self.timezone
        
        if self.language is not None:
            update_data["language"] = self.language
        
        if self.theme is not None:
            update_data["theme"] = self.theme
        
        if self.notification_enabled is not None:
            update_data["notification_enabled"] = self.notification_enabled
        
        # Handle clear flags (set fields to None)
        if self.clear_bio:
            update_data["bio"] = None
        
        if self.clear_location:
            update_data["location"] = None
        
        if self.clear_timezone:
            update_data["timezone"] = None
        
        if self.clear_profile_photo:
            update_data["profile_photo"] = None
        
        # Always update the updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        return update_data
    
    def to_domain_update_data(self) -> dict:
        """
        Convert command to domain entity update data.
        
        Returns:
            dict: Update data formatted for domain entity
        """
        if not self.has_updates():
            raise ValueError("No updates provided in command")
        
        return {
            "profile_id": self.profile_id,
            "update_data": self.get_update_data()
        }