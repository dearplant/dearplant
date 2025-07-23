# 📄 File: app/modules/user_management/domain/services/profile_service.py
# 🧭 Purpose (Layman Explanation): 
# Manages user profile information like photos, bio, location, privacy settings, and social features for the plant care community
# 🧪 Purpose (Technical Summary): 
# Domain service implementing profile management business logic, social features, and privacy controls following core doc Profile Management Submodule specifications
# 🔗 Dependencies: 
# Domain models, repositories, events, file storage services
# 🔄 Connected Modules / Calls From: 
# Application command handlers, API profile endpoints, community features, weather integration

from fastapi import Depends
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from ..models.profile import Profile, ProfileVisibility, NotificationPreferences, PrivacySettings
from ..models.user import User
from ..repositories.profile_repository import ProfileRepository
from ..repositories.user_repository import UserRepository
from ..events.user_events import UserProfileUpdated
from app.shared.events.publisher import EventPublisher
from app.shared.utils.validators import ValidationResult
from typing import Any

logger = logging.getLogger(__name__)


class ProfileService:
    """
    Domain service for profile management business logic.
    
    Implements functionality from core doc Profile Management Submodule (1.2):
    - Profile creation and editing
    - Photo upload with compression
    - Language and theme switching
    - Location-based weather integration
    - Privacy settings management
    
    Extended with social and community features:
    - Social media links management
    - Interest and experience level tracking
    - Profile visibility controls
    - Community statistics
    """
    
    def __init__(
        self,
        profile_repository: ProfileRepository = Depends() ,
        user_repository: UserRepository = Depends(),
        event_publisher: EventPublisher = Depends()
    ):
        self.profile_repository = profile_repository
        self.user_repository = user_repository
        self.event_publisher = event_publisher
    
    async def create_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        timezone: str = "UTC",
        language: str = "en"
    ) -> Profile:
        """
        Create a new user profile.
        
        Implements profile creation from core doc Profile Management functionality.
        
        Args:
            user_id: Associated user ID
            display_name: User's display name
            bio: User biography (max 500 chars per core doc)
            location: User's location for weather data
            timezone: User's timezone
            language: Preferred language (auto-detect default per core doc)
            
        Returns:
            Created Profile entity
            
        Raises:
            ValueError: If user not found or profile already exists
        """
        logger.info(f"Creating profile for user: {user_id}")
        
        # 1. Validate user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # 2. Check if profile already exists
        existing_profile = await self.profile_repository.get_by_user_id(user_id)
        if existing_profile:
            raise ValueError(f"Profile already exists for user {user_id}")
        
        # 3. Create profile
        profile = Profile.create_new_profile(
            user_id=user_id,
            display_name=display_name,
            location=location,
            timezone=timezone,
            language=language
        )
        
        # 4. Set bio if provided
        if bio:
            profile.bio = bio
        
        # 5. Save profile
        created_profile = await self.profile_repository.create(profile)
        
        # 6. Publish profile updated event
        await self._publish_profile_updated_event(
            created_profile,
            updated_fields={"created": True},
            privacy_changes=False,
            location_changed=bool(location)
        )
        
        logger.info(f"Successfully created profile for user: {user_id}")
        return created_profile
    
    async def update_basic_info(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        website_url: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> Profile:
        """
        Update basic profile information.
        
        Implements profile editing from core doc Profile Management functionality.
        
        Args:
            user_id: User ID
            display_name: New display name
            bio: New biography
            website_url: New website URL
            experience_level: New experience level
            
        Returns:
            Updated Profile entity
            
        Raises:
            ValueError: If profile not found
        """
        logger.info(f"Updating basic info for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Track what's being updated
        updated_fields = {}
        
        # 3. Update fields
        if display_name is not None:
            updated_fields["display_name"] = display_name
        if bio is not None:
            updated_fields["bio"] = bio
        if website_url is not None:
            updated_fields["website_url"] = website_url
        if experience_level is not None:
            updated_fields["experience_level"] = experience_level
        
        # 4. Apply updates
        profile.update_basic_info(
            display_name=display_name,
            bio=bio,
            website_url=website_url
        )
        
        if experience_level is not None:
            profile.experience_level = experience_level
        
        # 5. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 6. Publish event
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields=updated_fields,
            privacy_changes=False,
            location_changed=False
        )
        
        logger.info(f"Successfully updated basic info for user: {user_id}")
        return updated_profile
    
    async def update_preferences(
        self,
        user_id: str,
        language: Optional[str] = None,
        timezone: Optional[str] = None,
        theme: Optional[str] = None
    ) -> Profile:
        """
        Update user preferences.
        
        Implements language and theme switching from core doc Profile Management functionality.
        
        Args:
            user_id: User ID
            language: New preferred language
            timezone: New timezone
            theme: New theme preference (light/dark/auto per core doc)
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating preferences for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Track updates
        updated_fields = {}
        if language is not None:
            updated_fields["language"] = language
        if timezone is not None:
            updated_fields["timezone"] = timezone
        if theme is not None:
            updated_fields["theme"] = theme
        
        # 3. Update preferences
        profile.update_preferences(
            language=language,
            timezone=timezone,
            theme=theme
        )
        
        # 4. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 5. Publish event
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields=updated_fields,
            privacy_changes=False,
            location_changed=False
        )
        
        logger.info(f"Successfully updated preferences for user: {user_id}")
        return updated_profile
    
    async def update_location(
        self,
        user_id: str,
        location: str
    ) -> Profile:
        """
        Update user location.
        
        Implements location-based weather integration from core doc Profile Management functionality.
        
        Args:
            user_id: User ID
            location: New location
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating location for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update location
        previous_location = profile.location
        profile.location = location
        profile.updated_at = datetime.now(timezone.utc)
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 4. Publish event with location change flag
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields={"location": location},
            privacy_changes=False,
            location_changed=True
        )
        
        logger.info(f"Successfully updated location for user: {user_id}")
        return updated_profile
    
    async def upload_profile_photo(
        self,
        user_id: str,
        photo_url: str
    ) -> Profile:
        """
        Update profile photo.
        
        Implements photo upload with compression from core doc Profile Management functionality.
        Note: Photo compression and upload to Supabase Storage would be handled 
        by infrastructure layer before calling this method.
        
        Args:
            user_id: User ID
            photo_url: URL of uploaded photo in Supabase Storage
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating profile photo for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update photo
        profile.update_profile_photo(photo_url)
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 4. Publish event
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields={"profile_photo": photo_url},
            privacy_changes=False,
            location_changed=False
        )
        
        logger.info(f"Successfully updated profile photo for user: {user_id}")
        return updated_profile
    
    async def update_social_links(
        self,
        user_id: str,
        social_links: Dict[str, str]
    ) -> Profile:
        """
        Update social media links.
        
        Args:
            user_id: User ID
            social_links: Dictionary of platform -> URL
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating social links for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update social links
        for platform, url in social_links.items():
            if url:
                profile.add_social_link(platform, url)
            else:
                profile.remove_social_link(platform)
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 4. Publish event
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields={"social_links": social_links},
            privacy_changes=False,
            location_changed=False
        )
        
        logger.info(f"Successfully updated social links for user: {user_id}")
        return updated_profile
    
    async def update_interests(
        self,
        user_id: str,
        interests: List[str]
    ) -> Profile:
        """
        Update plant-related interests.
        
        Args:
            user_id: User ID
            interests: List of interests
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating interests for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update interests
        profile.interests = interests
        profile.updated_at = datetime.now(timezone.utc)
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 4. Publish event
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields={"interests": interests},
            privacy_changes=False,
            location_changed=False
        )
        
        logger.info(f"Successfully updated interests for user: {user_id}")
        return updated_profile
    
    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ) -> Profile:
        """
        Update notification preferences.
        
        Args:
            user_id: User ID
            preferences: Dictionary of preference updates
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating notification preferences for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update preferences
        profile.update_notification_preferences(preferences)
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 4. Publish event
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields={"notification_preferences": preferences},
            privacy_changes=False,
            location_changed=False
        )
        
        logger.info(f"Successfully updated notification preferences for user: {user_id}")
        return updated_profile
    
    async def update_privacy_settings(
        self,
        user_id: str,
        privacy_settings: Dict[str, Any]
    ) -> Profile:
        """
        Update privacy settings.
        
        Implements privacy settings management from core doc Profile Management functionality.
        
        Args:
            user_id: User ID
            privacy_settings: Dictionary of privacy setting updates
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating privacy settings for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update privacy settings
        profile.update_privacy_settings(privacy_settings)
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        # 4. Publish event with privacy change flag
        await self._publish_profile_updated_event(
            updated_profile,
            updated_fields={"privacy_settings": privacy_settings},
            privacy_changes=True,
            location_changed=False
        )
        
        logger.info(f"Successfully updated privacy settings for user: {user_id}")
        return updated_profile
    
    async def update_social_stats(
        self,
        user_id: str,
        followers_delta: int = 0,
        following_delta: int = 0,
        plants_count: Optional[int] = None,
        posts_delta: int = 0
    ) -> Profile:
        """
        Update social statistics.
        
        Connected to Community Features and Personal Plant Collection from core doc.
        
        Args:
            user_id: User ID
            followers_delta: Change in followers count
            following_delta: Change in following count
            plants_count: New plants count (absolute value)
            posts_delta: Change in posts count
            
        Returns:
            Updated Profile entity
        """
        logger.info(f"Updating social stats for user: {user_id}")
        
        # 1. Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # 2. Update statistics
        if followers_delta > 0:
            for _ in range(followers_delta):
                profile.increment_followers()
        elif followers_delta < 0:
            for _ in range(abs(followers_delta)):
                profile.decrement_followers()
        
        if following_delta > 0:
            for _ in range(following_delta):
                profile.increment_following()
        elif following_delta < 0:
            for _ in range(abs(following_delta)):
                profile.decrement_following()
        
        if plants_count is not None:
            profile.update_plants_count(plants_count)
        
        if posts_delta > 0:
            for _ in range(posts_delta):
                profile.increment_posts()
        elif posts_delta < 0:
            for _ in range(abs(posts_delta)):
                profile.decrement_posts()
        
        # 3. Save profile
        updated_profile = await self.profile_repository.update(profile)
        
        logger.info(f"Successfully updated social stats for user: {user_id}")
        return updated_profile
    
    async def get_profile_by_user_id(self, user_id: str) -> Optional[Profile]:
        """
        Get profile by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Profile entity or None if not found
        """
        return await self.profile_repository.get_by_user_id(user_id)
    
    async def get_public_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get public profile data respecting privacy settings.
        
        Args:
            user_id: User ID
            
        Returns:
            Public profile data or None if not found/private
        """
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            return None
        
        return profile.get_public_data()
    
    async def search_profiles(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Profile]:
        """
        Search profiles by display name or interests.
        
        Args:
            query: Search query
            limit: Maximum results to return
            offset: Number of results to skip
            
        Returns:
            List of matching Profile entities
        """
        return await self.profile_repository.search_profiles(query, limit, offset)
    
    async def validate_new_profile(self, profile_data: Any) -> ValidationResult:
        """
        Validate new profile data during registration.

        Args:
            profile_data: Profile dict or Profile object (Pydantic)

        Returns:
            ValidationResult: An object with the validation status and cleaned data.
        """
        if not isinstance(profile_data, dict):
            profile_data = profile_data.dict()

        # --- Validation Checks ---
        if not profile_data.get("display_name"):
            return ValidationResult(is_valid=False, errors=["Display name is required"])

        if len(profile_data.get("bio", "")) > 500:
            return ValidationResult(is_valid=False, errors=["Bio must not exceed 500 characters"])

        # --- Apply Defaults ---
        if profile_data.get("timezone") is None:
            profile_data["timezone"] = "UTC" # Set a default if None

        if profile_data.get("language") is None:
            profile_data["language"] = "en"

        logger.info(f"profile data validated: {profile_data}")

        # Return a successful ValidationResult object
        return ValidationResult(is_valid=True, errors=[], warnings=[])

    # Private helper methods
    
    async def _publish_profile_updated_event(
        self,
        profile: Profile,
        updated_fields: Dict[str, Any],
        privacy_changes: bool,
        location_changed: bool
    ) -> None:
        """Publish profile updated event."""
        event = UserProfileUpdated(
            user_id=profile.user_id,
            profile_id=profile.profile_id,
            updated_fields=updated_fields,
            privacy_changes=privacy_changes,
            location_changed=location_changed
        )
        await self.event_publisher.publish(event)