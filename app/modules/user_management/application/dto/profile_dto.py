# 📄 File: app/modules/user_management/application/dto/profile_dto.py
# 🧭 Purpose (Layman Explanation):
# This file defines standardized data packages for user profile information that can be safely
# sent between different parts of our plant care app while respecting privacy settings and preferences.
#
# 🧪 Purpose (Technical Summary):
# Profile data transfer objects implementing Core Doc 1.2 Profile Management specifications with
# privacy filtering, validation, and serialization for safe data exchange between layers.
#
# 🔗 Dependencies:
# - pydantic for DTO validation and serialization
# - app.modules.user_management.domain.models.profile (Profile domain entity)
# - Core doc 1.2 specifications for all profile fields and privacy requirements
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers (handlers return profile DTOs)
# - app.modules.user_management.presentation.api.v1 (API endpoints use profile DTOs)
# - app.modules.user_management.presentation.api.schemas (API schema conversion)

"""
Profile Data Transfer Objects (DTOs)

This module implements DTOs for profile management following Core Doc 1.2
(Profile Management) specifications with proper privacy filtering and validation.

DTO Classes:
- ProfileDTO: Complete profile data representation
- CreateProfileDTO: Input validation for profile creation
- UpdateProfileDTO: Input validation for profile updates
- ProfileResponseDTO: API response formatting with privacy filtering
- ProfileListResponseDTO: Paginated profile list responses
- ProfileCompletenessDTO: Profile completion information
- ProfilePrivacyDTO: Privacy settings management

Privacy Features:
- Bio visibility controlled by privacy settings
- Location data filtered based on user preferences
- Notification settings visible only to owner
- Social data filtering for community features
- Profile completeness calculation

All DTOs follow Core Doc 1.2 field specifications and implement
proper validation and serialization for safe data transfer.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ThemePreference(str, Enum):
    """UI theme preference enumeration."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class VisibilityLevel(str, Enum):
    """Privacy visibility level enumeration."""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class LanguageCode(str, Enum):
    """Supported language codes."""
    AUTO = "auto"
    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    RU = "ru"
    ZH = "zh"
    JA = "ja"
    KO = "ko"


class ProfileDTO(BaseModel):
    """
    Complete profile data transfer object following Core Doc 1.2.
    
    This DTO represents the full profile entity data structure
    for internal application use with all fields.
    """
    
    # Core Doc 1.2 Profile Management Fields
    profile_id: UUID = Field(
        ...,
        description="Unique profile identifier",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    user_id: UUID = Field(
        ...,
        description="Foreign key to user authentication",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's display name",
        example="John Green"
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
        example="San Francisco, CA"
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's timezone",
        example="America/Los_Angeles"
    )
    language: LanguageCode = Field(
        default=LanguageCode.AUTO,
        description="Preferred language (default: auto-detect)",
        example=LanguageCode.EN
    )
    theme: ThemePreference = Field(
        default=ThemePreference.AUTO,
        description="UI theme preference (light/dark/auto)",
        example=ThemePreference.AUTO
    )
    notification_enabled: bool = Field(
        default=True,
        description="Global notification toggle",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="Profile creation date",
        example="2024-01-15T10:30:00Z"
    )
    updated_at: datetime = Field(
        ...,
        description="Last profile update",
        example="2024-01-20T15:45:00Z"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "profile_id": "456e7890-f12a-34b5-c678-901234567890",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "display_name": "John Green",
                "profile_photo": "https://supabase.co/storage/v1/object/profiles/user123/avatar.jpg",
                "bio": "Passionate indoor gardener and plant enthusiast",
                "location": "Portland, OR",
                "timezone": "America/Los_Angeles",
                "language": "en",
                "theme": "auto",
                "notification_enabled": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T15:45:00Z"
            }
        }
    
    @validator('bio')
    def validate_bio_length(cls, v):
        """Validate bio length according to Core Doc 1.2 (max 500 chars)."""
        if v is not None and len(v) > 500:
            raise ValueError("Bio must not exceed 500 characters")
        return v
    
    def get_completeness_percentage(self) -> float:
        """
        Calculate profile completeness percentage.
        
        Returns:
            float: Completeness percentage (0.0 to 100.0)
        """
        required_fields = ["display_name"]  # Always required
        optional_fields = ["profile_photo", "bio", "location", "timezone"]
        
        total_fields = len(required_fields) + len(optional_fields)
        completed_fields = len(required_fields)  # Required fields are always present
        
        # Check optional fields
        for field in optional_fields:
            field_value = getattr(self, field, None)
            if field_value is not None and field_value != "":
                completed_fields += 1
        
        return (completed_fields / total_fields) * 100.0
    
    def get_missing_fields(self) -> List[str]:
        """
        Get list of missing optional fields.
        
        Returns:
            List[str]: List of missing field names
        """
        optional_fields = ["profile_photo", "bio", "location", "timezone"]
        missing = []
        
        for field in optional_fields:
            field_value = getattr(self, field, None)
            if field_value is None or field_value == "":
                missing.append(field)
        
        return missing


class CreateProfileDTO(BaseModel):
    """
    Input DTO for profile creation requests.
    
    This DTO validates input data for profile creation
    following Core Doc 1.2 specifications.
    """
    
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's display name",
        example="Jane Smith"
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User biography",
        example="Urban gardening enthusiast specializing in herbs and succulents"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's location",
        example="Seattle, WA"
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's timezone",
        example="America/Los_Angeles"
    )
    language: LanguageCode = Field(
        default=LanguageCode.AUTO,
        description="Preferred language",
        example=LanguageCode.EN
    )
    theme: ThemePreference = Field(
        default=ThemePreference.AUTO,
        description="UI theme preference",
        example=ThemePreference.LIGHT
    )
    notification_enabled: bool = Field(
        default=True,
        description="Global notification toggle",
        example=True
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "display_name": "Jane Smith",
                "bio": "Urban gardening enthusiast specializing in herbs and succulents",
                "location": "Seattle, WA",
                "timezone": "America/Los_Angeles",
                "language": "en",
                "theme": "light",
                "notification_enabled": True
            }
        }


class UpdateProfileDTO(BaseModel):
    """
    Input DTO for profile update requests.
    
    This DTO validates input data for profile updates
    with optional field support and clear flags.
    """
    
    display_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated display name",
        example="Jane Green"
    )
    profile_photo: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Updated profile photo URL",
        example="https://supabase.co/storage/v1/object/profiles/user456/new_avatar.jpg"
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Updated biography",
        example="Experienced urban gardener with focus on sustainable practices"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated location",
        example="Portland, OR"
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Updated timezone",
        example="America/Los_Angeles"
    )
    language: Optional[LanguageCode] = Field(
        default=None,
        description="Updated language preference",
        example=LanguageCode.ES
    )
    theme: Optional[ThemePreference] = Field(
        default=None,
        description="Updated theme preference",
        example=ThemePreference.DARK
    )
    notification_enabled: Optional[bool] = Field(
        default=None,
        description="Updated notification setting",
        example=False
    )
    
    # Clear flags for nullable fields
    clear_bio: bool = Field(
        default=False,
        description="Set to true to clear bio field",
        example=False
    )
    clear_location: bool = Field(
        default=False,
        description="Set to true to clear location field",
        example=False
    )
    clear_timezone: bool = Field(
        default=False,
        description="Set to true to clear timezone field",
        example=False
    )
    clear_profile_photo: bool = Field(
        default=False,
        description="Set to true to clear profile photo",
        example=False
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "display_name": "Jane Green",
                "bio": "Experienced urban gardener with focus on sustainable practices",
                "location": "Portland, OR",
                "language": "es",
                "theme": "dark",
                "notification_enabled": False,
                "clear_bio": False,
                "clear_location": False,
                "clear_timezone": False,
                "clear_profile_photo": False
            }
        }


class ProfileResponseDTO(BaseModel):
    """
    API response DTO for profile data with privacy filtering.
    
    This DTO provides safe profile data for API responses
    with field filtering based on privacy level.
    """
    
    profile_id: UUID = Field(
        ...,
        description="Profile identifier",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    user_id: UUID = Field(
        ...,
        description="User identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    display_name: str = Field(
        ...,
        description="User's display name",
        example="John Green"
    )
    profile_photo: Optional[str] = Field(
        default=None,
        description="Profile photo URL",
        example="https://supabase.co/storage/v1/object/profiles/user123/avatar.jpg"
    )
    bio: Optional[str] = Field(
        default=None,
        description="User biography (privacy controlled)",
        example="Passionate indoor gardener"
    )
    location: Optional[str] = Field(
        default=None,
        description="User location (privacy controlled)",
        example="San Francisco, CA"
    )
    timezone: Optional[str] = Field(
        default=None,
        description="User timezone (privacy controlled)",
        example="America/Los_Angeles"
    )
    language: Optional[LanguageCode] = Field(
        default=None,
        description="Language preference (self/admin only)",
        example=LanguageCode.EN
    )
    theme: Optional[ThemePreference] = Field(
        default=None,
        description="Theme preference (self/admin only)",
        example=ThemePreference.AUTO
    )
    notification_enabled: Optional[bool] = Field(
        default=None,
        description="Notification setting (self/admin only)",
        example=True
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Profile creation date",
        example="2024-01-15T10:30:00Z"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp",
        example="2024-01-20T15:45:00Z"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "profile_id": "456e7890-f12a-34b5-c678-901234567890",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "display_name": "John Green",
                "profile_photo": "https://supabase.co/storage/v1/object/profiles/user123/avatar.jpg",
                "bio": "Passionate indoor gardener",
                "location": "San Francisco, CA",
                "timezone": "America/Los_Angeles",
                "language": "en",
                "theme": "auto",
                "notification_enabled": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T15:45:00Z"
            }
        }
    
    @classmethod
    def from_domain(
        cls, 
        profile: "Profile", 
        privacy_level: str = "public",
        privacy_settings: Optional[Dict] = None
    ) -> "ProfileResponseDTO":
        """
        Create response DTO from domain Profile entity.
        
        Args:
            profile: Profile domain entity
            privacy_level: Privacy level for field filtering ("public", "self", "admin")
            privacy_settings: User's privacy settings
            
        Returns:
            ProfileResponseDTO: Response DTO with appropriate filtering
        """
        settings = privacy_settings or {}
        
        # Base response data (always visible)
        response_data = {
            "profile_id": profile.profile_id,
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "profile_photo": profile.profile_photo,
        }
        
        # Bio visibility filtering
        if profile.bio and settings.get("bio_visibility", "public") == "public":
            response_data["bio"] = profile.bio
        elif privacy_level in ["self", "admin"]:
            response_data["bio"] = profile.bio
        
        # Location data filtering
        location_visible = (
            settings.get("location_visibility", "public") == "public" or
            privacy_level in ["self", "admin"]
        )
        if location_visible:
            response_data["location"] = profile.location
            response_data["timezone"] = profile.timezone
        
        # Preferences (self/admin only)
        if privacy_level in ["self", "admin"]:
            response_data.update({
                "language": LanguageCode(profile.language),
                "theme": ThemePreference(profile.theme),
                "notification_enabled": profile.notification_enabled,
            })
        
        # Timestamps
        if privacy_level in ["self", "admin"]:
            response_data.update({
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            })
        
        return cls(**response_data)


class ProfileListResponseDTO(BaseModel):
    """
    Paginated profile list response DTO.
    
    This DTO provides paginated profile data for list endpoints
    with metadata for navigation.
    """
    
    profiles: List[ProfileResponseDTO] = Field(
        ...,
        description="List of profiles",
        example=[]
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of profiles",
        example=75
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
        description="Number of profiles per page",
        example=20
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        example=4
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
                "profiles": [],
                "total_count": 75,
                "page": 1,
                "page_size": 20,
                "total_pages": 4,
                "has_next": True,
                "has_previous": False
            }
        }


class ProfileCompletenessDTO(BaseModel):
    """
    Profile completeness information DTO.
    
    This DTO provides profile completion status and
    suggestions for improving the profile.
    """
    
    profile_id: UUID = Field(
        ...,
        description="Profile identifier",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    completeness_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Profile completeness percentage",
        example=75.0
    )
    completed_fields: int = Field(
        ...,
        ge=0,
        description="Number of completed fields",
        example=6
    )
    total_fields: int = Field(
        ...,
        ge=0,
        description="Total number of fields",
        example=8
    )
    missing_fields: List[str] = Field(
        ...,
        description="List of missing field names",
        example=["bio", "location"]
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Improvement suggestions",
        example=[
            "Add a bio to tell others about your gardening interests",
            "Set your location to get personalized weather data"
        ]
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "profile_id": "456e7890-f12a-34b5-c678-901234567890",
                "completeness_percentage": 75.0,
                "completed_fields": 6,
                "total_fields": 8,
                "missing_fields": ["bio", "location"],
                "suggestions": [
                    "Add a bio to tell others about your gardening interests",
                    "Set your location to get personalized weather data"
                ]
            }
        }


class ProfilePrivacyDTO(BaseModel):
    """
    Profile privacy settings DTO.
    
    This DTO manages privacy settings for profile data
    visibility and social features.
    """
    
    profile_id: UUID = Field(
        ...,
        description="Profile identifier",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    profile_visibility: VisibilityLevel = Field(
        default=VisibilityLevel.PUBLIC,
        description="Overall profile visibility",
        example=VisibilityLevel.PUBLIC
    )
    bio_visibility: VisibilityLevel = Field(
        default=VisibilityLevel.PUBLIC,
        description="Bio visibility level",
        example=VisibilityLevel.PUBLIC
    )
    location_visibility: VisibilityLevel = Field(
        default=VisibilityLevel.PUBLIC,
        description="Location visibility level",
        example=VisibilityLevel.FRIENDS
    )
    allow_friend_requests: bool = Field(
        default=True,
        description="Allow friend requests",
        example=True
    )
    show_in_search: bool = Field(
        default=True,
        description="Show profile in search results",
        example=True
    )
    allow_direct_messages: bool = Field(
        default=True,
        description="Allow direct messages",
        example=False
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "profile_id": "456e7890-f12a-34b5-c678-901234567890",
                "profile_visibility": "public",
                "bio_visibility": "public",
                "location_visibility": "friends",
                "allow_friend_requests": True,
                "show_in_search": True,
                "allow_direct_messages": False
            }
        }