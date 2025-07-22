# 📄 File: app/modules/user_management/domain/models/profile.py
# 🧭 Purpose (Layman Explanation): 
# Defines the extended user profile information like bio, location, photos, and privacy settings that make each user's experience personalized
# 🧪 Purpose (Technical Summary): 
# Domain model for Profile entity implementing extended user information, preferences, and social features following core doc Profile Management Submodule specifications
# 🔗 Dependencies: 
# pydantic, datetime, typing, uuid, enum
# 🔄 Connected Modules / Calls From: 
# profile_service.py, user_service.py, profile_repository.py, community features

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, validator, Field


class ProfileVisibility(str, Enum):
    """Profile visibility settings"""
    PUBLIC = "public"          # Visible to all users
    FRIENDS = "friends"        # Visible to friends only
    PRIVATE = "private"        # Only visible to user


class NotificationPreferences(BaseModel):
    """
    Notification preferences following core doc Profile Management functionality.
    Global notification toggle handled in User model.
    """
    # Care reminders
    care_reminders_push: bool = True
    care_reminders_email: bool = True
    
    # Plant health alerts
    health_alerts_push: bool = True
    health_alerts_email: bool = True
    
    # Social notifications
    social_likes_push: bool = True
    social_comments_push: bool = True
    social_follows_push: bool = True
    social_email: bool = False
    
    # System notifications
    newsletter_email: bool = False
    promotional_email: bool = False
    security_alerts_email: bool = True


class PrivacySettings(BaseModel):
    """Privacy settings for user profile and data"""
    # Profile visibility
    profile_visibility: ProfileVisibility = ProfileVisibility.PUBLIC
    plant_collection_visible: bool = True
    activity_visible: bool = True
    
    # Data sharing
    analytics_sharing: bool = True
    location_sharing: bool = True
    
    # Communication
    allow_messages: bool = True
    show_online_status: bool = True


class Profile(BaseModel):
    """
    Profile domain model representing extended user information.
    
    Implements core doc fields from Profile Management Submodule (1.2):
    - profile_id (UUID): Unique profile identifier
    - user_id (UUID): Foreign key to authentication
    - display_name (String): User's display name
    - profile_photo (String): Profile image URL in Supabase Storage
    - bio (Text): User biography (max 500 chars)
    - location (String): User's location for weather data
    - timezone (String): User's timezone
    - language (String): Preferred language (default: auto-detect)
    - theme (String): UI theme preference (light/dark/auto)
    - notification_enabled (Boolean): Global notification toggle
    - created_at (Timestamp): Profile creation date
    - updated_at (Timestamp): Last profile update
    
    Extended with social and privacy features for community functionality.
    """
    
    # Identity - following core doc Profile Management Submodule
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Foreign key to User
    
    # Basic profile information from core doc
    display_name: Optional[str] = None
    profile_photo: Optional[str] = None  # URL in Supabase Storage
    bio: Optional[str] = Field(None, max_length=500)  # max 500 chars per core doc
    location: Optional[str] = None  # For weather data integration
    
    # User preferences from core doc
    timezone: str = "UTC"
    language: str = "en"  # auto-detect default
    theme: str = "auto"  # light/dark/auto per core doc
    
    # Extended profile information for community features
    website_url: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)  # {"instagram": "url", "twitter": "url"}
    interests: list[str] = Field(default_factory=list)  # Plant-related interests
    experience_level: str = "beginner"  # beginner/intermediate/advanced
    
    # Social statistics
    followers_count: int = 0
    following_count: int = 0
    plants_count: int = 0
    posts_count: int = 0
    
    # Preferences and settings
    notification_preferences: NotificationPreferences = Field(default_factory=NotificationPreferences)
    privacy_settings: PrivacySettings = Field(default_factory=PrivacySettings)
    
    # Metadata following core doc timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
    
    @validator('bio')
    def validate_bio(cls, v):
        """Validate bio length following core doc max 500 chars requirement"""
        if v and len(v) > 500:
            raise ValueError('Bio cannot exceed 500 characters')
        return v
    
    @validator('display_name')
    def validate_display_name(cls, v):
        """Validate display name format"""
        if v is None:
            return v
            
        name = v.strip()
        
        if len(name) < 1:
            raise ValueError('Display name cannot be empty')
        if len(name) > 50:
            raise ValueError('Display name cannot exceed 50 characters')
            
        return name
    
    @validator('website_url')
    def validate_website_url(cls, v):
        """Validate website URL format"""
        if v is None:
            return v
            
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Website URL must start with http:// or https://')
            
        return v
    
    @validator('theme')
    def validate_theme(cls, v):
        """Validate theme preference following core doc"""
        allowed_themes = ["light", "dark", "auto"]
        if v not in allowed_themes:
            raise ValueError(f'Theme must be one of: {allowed_themes}')
        return v
    
    @validator('experience_level')
    def validate_experience_level(cls, v):
        """Validate experience level"""
        allowed_levels = ["beginner", "intermediate", "advanced"]
        if v not in allowed_levels:
            raise ValueError(f'Experience level must be one of: {allowed_levels}')
        return v
    
    @validator('social_links')
    def validate_social_links(cls, v):
        """Validate social media links"""
        allowed_platforms = ["instagram", "twitter", "facebook", "youtube", "tiktok", "pinterest"]
        
        for platform, url in v.items():
            if platform not in allowed_platforms:
                raise ValueError(f'Social platform must be one of: {allowed_platforms}')
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'Social link for {platform} must be a valid URL')
        
        return v
    
    # Business Logic Methods following core doc Profile Management functionality
    
    @classmethod
    def create_new_profile(
        cls,
        user_id: str,
        display_name: Optional[str] = None,
        location: Optional[str] = None,
        timezone: str = "UTC",
        language: str = "en"
    ) -> "Profile":
        """
        Create a new user profile with defaults.
        Implements profile creation from core doc Profile Management functionality.
        
        Args:
            user_id: Associated user ID
            display_name: User's display name
            location: User's location for weather integration
            timezone: User's timezone
            language: Preferred language (auto-detect default)
            
        Returns:
            New Profile instance
        """
        return cls(
            user_id=user_id,
            display_name=display_name,
            location=location,
            timezone=timezone,
            language=language
        )
    
    def update_basic_info(
        self,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        website_url: Optional[str] = None
    ) -> None:
        """
        Update basic profile information.
        Implements profile editing from core doc Profile Management functionality.
        
        Args:
            display_name: New display name
            bio: New biography
            location: New location
            website_url: New website URL
        """
        if display_name is not None:
            self.display_name = display_name
        if bio is not None:
            self.bio = bio
        if location is not None:
            self.location = location
        if website_url is not None:
            self.website_url = website_url
            
        self.updated_at = datetime.now(timezone.utc)
    
    def update_preferences(
        self,
        language: Optional[str] = None,
        timezone: Optional[str] = None,
        theme: Optional[str] = None
    ) -> None:
        """
        Update user preferences.
        Implements language and theme switching from core doc Profile Management functionality.
        
        Args:
            language: New preferred language
            timezone: New timezone
            theme: New theme preference
        """
        if language is not None:
            self.language = language
        if timezone is not None:
            self.timezone = timezone
        if theme is not None:
            self.theme = theme
            
        self.updated_at = datetime.now(timezone.utc)
    
    def update_profile_photo(self, photo_url: str) -> None:
        """
        Update profile photo.
        Implements photo upload with compression from core doc Profile Management functionality.
        
        Args:
            photo_url: New profile photo URL in Supabase Storage
        """
        self.profile_photo = photo_url
        self.updated_at = datetime.now(timezone.utc)
    
    def add_social_link(self, platform: str, url: str) -> None:
        """
        Add or update social media link.
        
        Args:
            platform: Social media platform
            url: Profile URL
        """
        self.social_links[platform] = url
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_social_link(self, platform: str) -> None:
        """
        Remove social media link.
        
        Args:
            platform: Social media platform to remove
        """
        self.social_links.pop(platform, None)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_interest(self, interest: str) -> None:
        """
        Add plant-related interest.
        
        Args:
            interest: Interest to add
        """
        if interest not in self.interests:
            self.interests.append(interest)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_interest(self, interest: str) -> None:
        """
        Remove plant-related interest.
        
        Args:
            interest: Interest to remove
        """
        if interest in self.interests:
            self.interests.remove(interest)
            self.updated_at = datetime.now(timezone.utc)
    
    def update_notification_preferences(self, preferences: Dict[str, bool]) -> None:
        """
        Update notification preferences.
        
        Args:
            preferences: Dictionary of notification preference updates
        """
        for key, value in preferences.items():
            if hasattr(self.notification_preferences, key):
                setattr(self.notification_preferences, key, value)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def update_privacy_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update privacy settings.
        Implements privacy settings management from core doc Profile Management functionality.
        
        Args:
            settings: Dictionary of privacy setting updates
        """
        for key, value in settings.items():
            if hasattr(self.privacy_settings, key):
                setattr(self.privacy_settings, key, value)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_followers(self) -> None:
        """Increment followers count."""
        self.followers_count += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def decrement_followers(self) -> None:
        """Decrement followers count."""
        if self.followers_count > 0:
            self.followers_count -= 1
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_following(self) -> None:
        """Increment following count."""
        self.following_count += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def decrement_following(self) -> None:
        """Decrement following count."""
        if self.following_count > 0:
            self.following_count -= 1
        self.updated_at = datetime.now(timezone.utc)
    
    def update_plants_count(self, count: int) -> None:
        """
        Update plants count.
        Connected to Personal Plant Collection from core doc.
        
        Args:
            count: New plants count
        """
        self.plants_count = max(0, count)
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_posts(self) -> None:
        """Increment posts count."""
        self.posts_count += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def decrement_posts(self) -> None:
        """Decrement posts count."""
        if self.posts_count > 0:
            self.posts_count -= 1
        self.updated_at = datetime.now(timezone.utc)
    
    def is_public_profile(self) -> bool:
        """
        Check if profile is publicly visible.
        
        Returns:
            True if profile is public
        """
        return self.privacy_settings.profile_visibility == ProfileVisibility.PUBLIC
    
    def can_be_messaged(self) -> bool:
        """
        Check if user accepts messages.
        
        Returns:
            True if user accepts messages
        """
        return self.privacy_settings.allow_messages
    
    def get_public_data(self) -> Dict[str, Any]:
        """
        Get profile data safe for public display.
        Respects privacy settings.
        
        Returns:
            Public profile data
        """
        data = {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "experience_level": self.experience_level,
            "created_at": self.created_at
        }
        
        # Add data based on privacy settings
        if self.privacy_settings.profile_visibility == ProfileVisibility.PUBLIC:
            data.update({
                "profile_photo": self.profile_photo,
                "bio": self.bio,
                "interests": self.interests,
                "social_links": self.social_links,
                "website_url": self.website_url,
                "followers_count": self.followers_count,
                "following_count": self.following_count
            })
            
            if self.privacy_settings.plant_collection_visible:
                data["plants_count"] = self.plants_count
                
            if self.privacy_settings.activity_visible:
                data["posts_count"] = self.posts_count
                
            if self.privacy_settings.location_sharing and self.location:
                data["location"] = self.location
        
        return data
    
    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        """
        Convert profile to dictionary.
        
        Args:
            include_private: Whether to include private data
            
        Returns:
            Profile data as dictionary
        """
        if include_private:
            return self.dict()
        else:
            return self.get_public_data()