# 📄 File: app/modules/user_management/application/queries/get_profile.py
# 🧭 Purpose (Layman Explanation):
# This file defines the "get profile" query that contains all the information needed
# to retrieve a user's profile details safely, including personal info, preferences, and settings.
#
# 🧪 Purpose (Technical Summary):
# CQRS query implementation for profile data retrieval following Core Doc 1.2 Profile Management
# specifications with privacy controls, preference filtering, and proper data access validation.
#
# 🔗 Dependencies:
# - pydantic for query validation and serialization
# - app.modules.user_management.domain.models.profile (Profile domain entity)
# - Core doc 1.2 specifications for profile fields and privacy controls
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.query_handlers (GetProfileQueryHandler)
# - app.modules.user_management.presentation.api.v1.profiles (profile retrieval endpoints)
# - app.modules.user_management.presentation.api.schemas.profile_schemas (API schema conversion)

"""
Get Profile Query

This module implements the CQRS query for profile data retrieval,
following the exact specifications from Core Doc 1.2 (Profile Management)
with proper privacy controls and preference access validation.

Query Fields:
- profile_id: UUID of the profile to retrieve (optional if using user_id)
- user_id: UUID of the user whose profile to retrieve (optional if using profile_id)
- requesting_user_id: UUID of user making the request (for privacy control)
- include_private_data: Include private fields (self/admin only)
- include_preferences: Include language/theme preferences
- include_location_data: Include location and timezone (privacy controlled)
- include_notification_settings: Include notification preferences

Privacy Controls (Core Doc 1.2):
- Users can access their own profiles fully
- Public profiles show limited information
- Location data respects privacy settings
- Bio and personal info filtered based on privacy
- Notification settings visible to owner only
- Admin can access all profile data

Response Filtering:
- Private fields filtered based on privacy settings
- Location data filtered for privacy compliance
- Notification settings restricted to owner
- Profile photos always visible (if set)
- Display names always visible for social features
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ProfileLookupType(str, Enum):
    """Enumeration of profile lookup methods."""
    BY_PROFILE_ID = "by_profile_id"
    BY_USER_ID = "by_user_id"


class PrivacyLevel(str, Enum):
    """Privacy access levels for profile data filtering."""
    PUBLIC = "public"          # Public profile view
    SELF = "self"             # Owner's own profile
    ADMIN = "admin"           # Full administrative access


class ProfileVisibility(str, Enum):
    """Profile visibility settings."""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class GetProfileQuery(BaseModel):
    """
    Query for retrieving user profile information.
    
    This query encapsulates profile lookup parameters following
    Core Doc 1.2 (Profile Management) specifications with proper
    privacy controls and access validation.
    """
    
    # Primary lookup fields (at least one required)
    profile_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the profile to retrieve",
        example="456e7890-f12a-34b5-c678-901234567890"
    )
    user_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the user whose profile to retrieve",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    # Security and access control
    requesting_user_id: UUID = Field(
        ...,
        description="UUID of user making the request (for privacy control)",
        example="987fcdeb-51a2-43d1-9876-ba0987654321"
    )
    is_admin_request: bool = Field(
        default=False,
        description="Whether request is from admin user",
        example=False
    )
    
    # Data inclusion options (Core Doc 1.2)
    include_private_data: bool = Field(
        default=False,
        description="Include private fields (self/admin only)",
        example=False
    )
    include_preferences: bool = Field(
        default=True,
        description="Include language/theme preferences",
        example=True
    )
    include_location_data: bool = Field(
        default=True,
        description="Include location and timezone (privacy controlled)",
        example=True
    )
    include_notification_settings: bool = Field(
        default=False,
        description="Include notification preferences (self/admin only)",
        example=False
    )
    include_timestamps: bool = Field(
        default=True,
        description="Include creation and update timestamps",
        example=True
    )
    
    # Social and community features
    include_social_data: bool = Field(
        default=True,
        description="Include social profile information",
        example=True
    )
    respect_privacy_settings: bool = Field(
        default=True,
        description="Respect user's privacy settings for data filtering",
        example=True
    )
    
    # Response formatting
    include_computed_fields: bool = Field(
        default=False,
        description="Include computed fields like profile completion percentage",
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
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "requesting_user_id": "123e4567-e89b-12d3-a456-426614174000",
                "is_admin_request": False,
                "include_private_data": True,
                "include_preferences": True,
                "include_location_data": True,
                "include_notification_settings": True,
                "include_timestamps": True,
                "include_social_data": True,
                "respect_privacy_settings": True,
                "include_computed_fields": False
            }
        }
    
    def get_lookup_type(self) -> ProfileLookupType:
        """
        Determine the type of profile lookup being performed.
        
        Returns:
            ProfileLookupType: Type of lookup operation
            
        Raises:
            ValueError: If no valid lookup parameters provided
        """
        if self.profile_id is not None:
            return ProfileLookupType.BY_PROFILE_ID
        
        if self.user_id is not None:
            return ProfileLookupType.BY_USER_ID
        
        raise ValueError("Must provide profile_id or user_id for lookup")
    
    def get_privacy_level(self) -> PrivacyLevel:
        """
        Determine the privacy access level for this request.
        
        Returns:
            PrivacyLevel: Access level for data filtering
        """
        if self.is_admin_request:
            return PrivacyLevel.ADMIN
        
        # Check if user is requesting their own profile
        if self.user_id == self.requesting_user_id:
            return PrivacyLevel.SELF
        
        return PrivacyLevel.PUBLIC
    
    def is_authorized_for_private_data(self) -> bool:
        """
        Check if request is authorized for private data access.
        
        Returns:
            bool: True if authorized for private data
        """
        privacy_level = self.get_privacy_level()
        return privacy_level in [PrivacyLevel.ADMIN, PrivacyLevel.SELF]
    
    def is_authorized_for_notification_settings(self) -> bool:
        """
        Check if request is authorized for notification settings access.
        
        Returns:
            bool: True if authorized for notification settings
        """
        privacy_level = self.get_privacy_level()
        return privacy_level in [PrivacyLevel.ADMIN, PrivacyLevel.SELF]
    
    def is_authorized_for_location_data(self, profile_privacy_setting: str = "public") -> bool:
        """
        Check if request is authorized for location data access.
        
        Args:
            profile_privacy_setting: User's privacy setting for location
            
        Returns:
            bool: True if authorized for location data
        """
        privacy_level = self.get_privacy_level()
        
        # Admin and self always have access
        if privacy_level in [PrivacyLevel.ADMIN, PrivacyLevel.SELF]:
            return True
        
        # Respect user's privacy settings if not disabled
        if not self.respect_privacy_settings:
            return True
        
        # Check privacy setting
        return profile_privacy_setting == "public"
    
    def get_filtered_fields(self, profile_privacy_settings: Optional[dict] = None) -> List[str]:
        """
        Get list of fields that should be excluded from response based on privacy.
        
        Args:
            profile_privacy_settings: User's privacy settings
            
        Returns:
            List[str]: List of field names to exclude
        """
        excluded_fields = []
        privacy_level = self.get_privacy_level()
        settings = profile_privacy_settings or {}
        
        # Private data filtering
        if not self.include_private_data or not self.is_authorized_for_private_data():
            if settings.get("bio_visibility", "public") != "public" and privacy_level == PrivacyLevel.PUBLIC:
                excluded_fields.append("bio")
        
        # Location data filtering (Core Doc 1.2)
        if not self.include_location_data or not self.is_authorized_for_location_data(
            settings.get("location_visibility", "public")
        ):
            excluded_fields.extend(["location", "timezone"])
        
        # Notification settings filtering
        if not self.include_notification_settings or not self.is_authorized_for_notification_settings():
            excluded_fields.append("notification_enabled")
        
        # Preferences filtering
        if not self.include_preferences and privacy_level == PrivacyLevel.PUBLIC:
            excluded_fields.extend(["language", "theme"])
        
        # Timestamp filtering
        if not self.include_timestamps and privacy_level == PrivacyLevel.PUBLIC:
            excluded_fields.extend(["created_at", "updated_at"])
        
        # Social data filtering
        if not self.include_social_data:
            excluded_fields.extend(["display_name"])  # Keep minimal for functionality
        
        return excluded_fields
    
    def get_public_fields(self) -> List[str]:
        """
        Get list of fields that are always visible in public profile view.
        
        Returns:
            List[str]: List of always-visible field names
        """
        return [
            "profile_id",
            "user_id", 
            "display_name",  # Required for social features
            "profile_photo",  # Profile photos are typically public
        ]
    
    def validate_authorization(self) -> None:
        """
        Validate that the request is authorized based on lookup type and privacy level.
        
        Raises:
            ValueError: If request is not authorized
        """
        privacy_level = self.get_privacy_level()
        
        # Private data authorization
        if self.include_private_data and not self.is_authorized_for_private_data():
            raise ValueError("Private data access requires owner or admin privileges")
        
        # Notification settings authorization
        if self.include_notification_settings and not self.is_authorized_for_notification_settings():
            raise ValueError("Notification settings access requires owner or admin privileges")
    
    def calculate_profile_completeness_fields(self) -> List[str]:
        """
        Get fields used for profile completeness calculation.
        
        Returns:
            List[str]: List of fields to check for completeness
        """
        return [
            "display_name",      # Required
            "profile_photo",     # Optional but improves completeness
            "bio",              # Optional but improves completeness  
            "location",         # Optional but useful for weather
            "timezone",         # Optional but useful for notifications
            "language",         # Usually auto-detected
            "theme",           # User preference
        ]
    
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
            "privacy_level": self.get_privacy_level().value,
            "respect_privacy_settings": self.respect_privacy_settings,
            "public_fields": self.get_public_fields(),
            "include_computed_fields": self.include_computed_fields,
        }
        
        # Add lookup-specific parameters
        if lookup_type == ProfileLookupType.BY_PROFILE_ID:
            lookup_params["profile_id"] = self.profile_id
        
        elif lookup_type == ProfileLookupType.BY_USER_ID:
            lookup_params["user_id"] = self.user_id
        
        # Add data inclusion flags
        lookup_params.update({
            "include_private_data": self.include_private_data and self.is_authorized_for_private_data(),
            "include_preferences": self.include_preferences,
            "include_location_data": self.include_location_data,
            "include_notification_settings": self.include_notification_settings and self.is_authorized_for_notification_settings(),
            "include_timestamps": self.include_timestamps,
            "include_social_data": self.include_social_data,
        })
        
        # Add profile completeness fields if requested
        if self.include_computed_fields:
            lookup_params["completeness_fields"] = self.calculate_profile_completeness_fields()
        
        return lookup_params