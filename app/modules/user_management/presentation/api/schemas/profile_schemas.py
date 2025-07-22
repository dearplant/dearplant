# 📄 File: app/modules/user_management/presentation/api/schemas/profile_schemas.py
# 🧭 Purpose (Layman Explanation):
# This file defines all the data formats for user profile requests and responses like personal info,
# privacy settings, profile photos, and social features for our plant care app's API.
#
# 🧪 Purpose (Technical Summary):
# Pydantic profile management schemas implementing Core Doc 1.2 specifications for request/response
# validation, privacy controls, completeness tracking, and comprehensive profile management.
#
# 🔗 Dependencies:
# - pydantic for schema validation and serialization
# - app.modules.user_management.application.dto.profile_dto (DTOs for data conversion)
# - Core doc 1.2 specifications for profile fields and privacy requirements
# - FastAPI integration for file uploads and automatic validation
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1.profiles (profile management endpoints)
# - FastAPI automatic request validation and response serialization
# - Social features and community interaction interfaces

"""
Profile Management API Schemas

This module implements Pydantic schemas for profile management endpoints
following Core Doc 1.2 specifications with privacy controls and social features.

Request Schemas:
- ProfileCreateRequest: New profile creation with initial preferences
- ProfileUpdateRequest: Profile updates with partial update support
- ProfilePrivacyRequest: Privacy settings management
- ProfileSearchRequest: Profile discovery and search parameters

Response Schemas:
- ProfileResponse: Profile information with privacy filtering
- ProfileListResponse: Paginated profile lists for discovery
- ProfileCompletenessResponse: Profile completion analysis
- ProfilePrivacyResponse: Privacy settings information
- ProfilePhotoResponse: Photo upload confirmation
- ProfileSearchResponse: Profile search results

Privacy Features:
- Field-level privacy controls (bio, location visibility)
- Profile visibility settings (public, friends, private)
- Privacy-aware profile discovery and search
- Social interaction permission management
- Granular content visibility controls

All schemas follow Core Doc 1.2 specifications and implement proper
privacy measures for social features and profile management.
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


class VisibilityLevel(str, Enum):
    """Privacy visibility level enumeration."""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class ProfileSortField(str, Enum):
    """Profile list sorting fields."""
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    DISPLAY_NAME = "display_name"
    COMPLETENESS = "completeness"
    LOCATION = "location"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class ProfileCreateRequest(BaseModel):
    """
    Profile creation request schema following Core Doc 1.2 specifications.
    
    This schema validates new profile creation with all required and
    optional fields for initial profile setup.
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
        description="User biography (max 500 chars)",
        example="Urban gardening enthusiast specializing in herbs and succulents"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User's location for weather data",
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
    
    @validator('bio')
    def validate_bio_length(cls, v):
        """Validate bio length according to Core Doc 1.2 (max 500 chars)."""
        if v is not None and len(v) > 500:
            raise ValueError("Bio must not exceed 500 characters")
        return v


class ProfileUpdateRequest(BaseModel):
    """
    Profile update request schema with partial update support.
    
    This schema validates profile updates with optional fields and
    clear flags for nullable field management following Core Doc 1.2.
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
    
    # Clear flags for nullable fields (Core Doc 1.2)
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
    
    @validator('bio')
    def validate_bio_length(cls, v):
        """Validate bio length according to Core Doc 1.2 (max 500 chars)."""
        if v is not None and len(v) > 500:
            raise ValueError("Bio must not exceed 500 characters")
        return v


class ProfilePrivacyRequest(BaseModel):
    """
    Profile privacy settings request schema.
    
    This schema validates privacy setting updates with granular
    control over profile data visibility and social features.
    """
    
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
                "profile_visibility": "public",
                "bio_visibility": "public",
                "location_visibility": "friends",
                "allow_friend_requests": True,
                "show_in_search": True,
                "allow_direct_messages": False
            }
        }


class ProfileSearchRequest(BaseModel):
    """
    Profile search request schema for profile discovery.
    
    This schema validates profile search and filtering parameters
    for community discovery and social features.
    """
    
    # Search parameters
    search_term: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Search term for display name or bio",
        example="gardening"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Location filter",
        example="Seattle"
    )
    
    # Interest filters
    has_bio: Optional[bool] = Field(
        default=None,
        description="Filter profiles with/without bio",
        example=True
    )
    has_photo: Optional[bool] = Field(
        default=None,
        description="Filter profiles with/without photo",
        example=True
    )
    
    # Completeness filters
    min_completeness: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Minimum profile completeness percentage",
        example=50.0
    )
    
    # Activity filters
    created_after: Optional[datetime] = Field(
        default=None,
        description="Filter profiles created after this date",
        example="2024-01-01T00:00:00Z"
    )
    updated_after: Optional[datetime] = Field(
        default=None,
        description="Filter profiles updated after this date",
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
        le=50,
        description="Items per page (max 50 for profiles)",
        example=20
    )
    
    # Sorting
    sort_by: ProfileSortField = Field(
        default=ProfileSortField.UPDATED_AT,
        description="Sort field",
        example=ProfileSortField.COMPLETENESS
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
                "search_term": "gardening",
                "location": "Seattle",
                "has_bio": True,
                "has_photo": True,
                "min_completeness": 50.0,
                "page": 1,
                "page_size": 20,
                "sort_by": "completeness",
                "sort_order": "desc"
            }
        }
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order options."""
        if v not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ProfileResponse(BaseModel):
    """
    Profile response schema with privacy filtering.
    
    This schema provides profile information with appropriate privacy
    filtering based on requester permissions and user privacy settings.
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
    
    # Computed fields (self only)
    completeness_percentage: Optional[float] = Field(
        default=None,
        description="Profile completeness percentage (self only)",
        example=75.0
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
                "updated_at": "2024-01-20T15:45:00Z",
                "completeness_percentage": 75.0
            }
        }
    
    @classmethod
    def from_domain_data(
        cls,
        profile_data: Dict,
        privacy_level: str = "public",
        privacy_settings: Optional[Dict] = None
    ) -> "ProfileResponse":
        """
        Create response from domain profile data with privacy filtering.
        
        Args:
            profile_data: Profile data from domain layer
            privacy_level: Privacy level for field filtering ("public", "self", "admin")
            privacy_settings: User's privacy settings
            
        Returns:
            ProfileResponse: Filtered profile response
        """
        settings = privacy_settings or {}
        
        # Base response data (always visible)
        response_data = {
            "profile_id": profile_data["profile_id"],
            "user_id": profile_data["user_id"],
            "display_name": profile_data["display_name"],
            "profile_photo": profile_data.get("profile_photo"),
        }
        
        # Bio visibility filtering
        if profile_data.get("bio") and settings.get("bio_visibility", "public") == "public":
            response_data["bio"] = profile_data["bio"]
        elif privacy_level in ["self", "admin"]:
            response_data["bio"] = profile_data.get("bio")
        
        # Location data filtering
        location_visible = (
            settings.get("location_visibility", "public") == "public" or
            privacy_level in ["self", "admin"]
        )
        if location_visible:
            response_data["location"] = profile_data.get("location")
            response_data["timezone"] = profile_data.get("timezone")
        
        # Preferences (self/admin only)
        if privacy_level in ["self", "admin"]:
            response_data.update({
                "language": LanguageCode(profile_data.get("language", "auto")),
                "theme": ThemePreference(profile_data.get("theme", "auto")),
                "notification_enabled": profile_data.get("notification_enabled"),
                "created_at": profile_data.get("created_at"),
                "updated_at": profile_data.get("updated_at"),
            })
        
        # Completeness (self only)
        if privacy_level == "self" and "profile_completeness" in profile_data:
            response_data["completeness_percentage"] = profile_data["profile_completeness"]["percentage"]
        
        return cls(**response_data)
    
    @classmethod
    def from_handler_result(cls, handler_result: Dict, privacy_level: str = "self") -> "ProfileResponse":
        """Create response from command handler result."""
        return cls.from_domain_data(handler_result, privacy_level=privacy_level)


class ProfileListResponse(BaseModel):
    """
    Paginated profile list response schema for discovery.
    
    This schema provides paginated profile data for community
    discovery with navigation metadata and search information.
    """
    
    profiles: List[ProfileResponse] = Field(
        ...,
        description="List of profiles",
        example=[]
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of profiles matching criteria",
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
        le=50,
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
    
    # Search summary
    search_criteria: Dict = Field(
        default_factory=dict,
        description="Summary of search criteria used",
        example={"location": "Seattle", "min_completeness": 50.0}
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
                "has_previous": False,
                "search_criteria": {"location": "Seattle", "min_completeness": 50.0}
            }
        }


class ProfileCompletenessResponse(BaseModel):
    """
    Profile completeness analysis response schema.
    
    This schema provides profile completion status with detailed
    analysis and improvement suggestions for better user engagement.
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
    completion_score: str = Field(
        ...,
        description="Completion level description",
        example="Good"
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
                ],
                "completion_score": "Good"
            }
        }


class ProfilePrivacyResponse(BaseModel):
    """
    Profile privacy settings response schema.
    
    This schema provides current privacy settings with detailed
    information about visibility controls and social permissions.
    """
    
    profile_id: UUID = Field(
        ...,
        description="Profile identifier",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    profile_visibility: VisibilityLevel = Field(
        ...,
        description="Overall profile visibility",
        example=VisibilityLevel.PUBLIC
    )
    bio_visibility: VisibilityLevel = Field(
        ...,
        description="Bio visibility level",
        example=VisibilityLevel.PUBLIC
    )
    location_visibility: VisibilityLevel = Field(
        ...,
        description="Location visibility level",
        example=VisibilityLevel.FRIENDS
    )
    allow_friend_requests: bool = Field(
        ...,
        description="Allow friend requests",
        example=True
    )
    show_in_search: bool = Field(
        ...,
        description="Show profile in search results",
        example=True
    )
    allow_direct_messages: bool = Field(
        ...,
        description="Allow direct messages",
        example=False
    )
    updated_at: datetime = Field(
        ...,
        description="Privacy settings last updated",
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
                "profile_visibility": "public",
                "bio_visibility": "public",
                "location_visibility": "friends",
                "allow_friend_requests": True,
                "show_in_search": True,
                "allow_direct_messages": False,
                "updated_at": "2024-01-20T15:45:00Z"
            }
        }


class ProfilePhotoResponse(BaseModel):
    """
    Profile photo upload response schema.
    
    This schema provides photo upload confirmation with metadata
    and URL information for profile photo management.
    """
    
    profile_id: UUID = Field(
        ...,
        description="Profile identifier",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    photo_url: str = Field(
        ...,
        description="Uploaded photo URL",
        example="https://supabase.co/storage/v1/object/profiles/user456/avatar_20240120.jpg"
    )
    uploaded_at: datetime = Field(
        ...,
        description="Photo upload timestamp",
        example="2024-01-20T15:30:00Z"
    )
    file_size: Optional[int] = Field(
        default=None,
        description="File size in bytes",
        example=1024000
    )
    content_type: Optional[str] = Field(
        default=None,
        description="File content type",
        example="image/jpeg"
    )
    message: str = Field(
        default="Profile photo uploaded successfully",
        description="Upload confirmation message",
        example="Profile photo uploaded successfully"
    )
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        schema_extra = {
            "example": {
                "profile_id": "456e7890-f12a-34b5-c678-901234567890",
                "photo_url": "https://supabase.co/storage/v1/object/profiles/user456/avatar_20240120.jpg",
                "uploaded_at": "2024-01-20T15:30:00Z",
                "file_size": 1024000,
                "content_type": "image/jpeg",
                "message": "Profile photo uploaded successfully"
            }
        }


class ProfileSearchResponse(BaseModel):
    """
    Profile search response schema with enhanced metadata.
    
    This schema extends ProfileListResponse with search-specific
    information and discovery features for community interaction.
    """
    
    profiles: List[ProfileResponse] = Field(
        ...,
        description="List of matching profiles",
        example=[]
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of matching profiles",
        example=42
    )
    search_metadata: Dict = Field(
        default_factory=dict,
        description="Search execution metadata",
        example={
            "search_time_ms": 150,
            "total_indexed": 10000,
            "matched_criteria": ["location", "completeness"]
        }
    )
    suggested_searches: List[str] = Field(
        default_factory=list,
        description="Suggested search refinements",
        example=["Try searching in Portland", "Look for profiles with photos"]
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "profiles": [],
                "total_count": 42,
                "search_metadata": {
                    "search_time_ms": 150,
                    "total_indexed": 10000,
                    "matched_criteria": ["location", "completeness"]
                },
                "suggested_searches": ["Try searching in Portland", "Look for profiles with photos"]
            }
        }