# 📄 File: app/modules/user_management/domain/repositories/profile_repository.py
# 🧭 Purpose (Layman Explanation): 
# Defines the contract for how to save, find, update, and delete user profile information like photos, bio, and preferences in the database
# 🧪 Purpose (Technical Summary): 
# Repository interface defining data access operations for Profile entities following Repository pattern and supporting social and community features
# 🔗 Dependencies: 
# Domain models (Profile, ProfileVisibility), typing, abc
# 🔄 Connected Modules / Calls From: 
# Domain services, infrastructure implementations, application handlers, community features

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from ..models.profile import Profile, ProfileVisibility


class ProfileRepository(ABC):
    """
    Repository interface for Profile entity data access operations.
    
    Defines the contract for Profile data persistence following the Repository pattern.
    Supports core doc Profile Management Submodule (1.2) functionality including:
    - Profile creation and editing
    - Photo upload management
    - Language and theme preferences
    - Location-based features
    - Privacy settings management
    
    Extended with social and community features:
    - Profile search and discovery
    - Social statistics tracking
    - Interest-based filtering
    - Privacy-aware data access
    
    Implementation Notes:
    - Concrete implementations are in infrastructure layer
    - Methods return domain entities (Profile), not database models
    - All operations are async for non-blocking I/O
    - Repository handles entity-to-model mapping
    - Respects privacy settings in query operations
    """
    
    @abstractmethod
    async def create(self, profile: Profile) -> Profile:
        """
        Create a new user profile.
        
        Args:
            profile: Profile entity to create
            
        Returns:
            Created Profile entity with generated fields populated
            
        Raises:
            ValueError: If profile for user already exists
            RepositoryError: If database operation fails
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, profile_id: str) -> Optional[Profile]:
        """
        Get profile by profile ID.
        
        Args:
            profile_id: Profile ID to find
            
        Returns:
            Profile entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[Profile]:
        """
        Get profile by user ID.
        
        Args:
            user_id: User ID to find profile for
            
        Returns:
            Profile entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, profile: Profile) -> Profile:
        """
        Update existing profile.
        
        Args:
            profile: Profile entity with updated data
            
        Returns:
            Updated Profile entity
            
        Raises:
            ValueError: If profile not found
            RepositoryError: If database operation fails
        """
        pass
    
    @abstractmethod
    async def delete(self, profile_id: str) -> bool:
        """
        Delete profile by ID.
        
        Args:
            profile_id: Profile ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        pass
    
    @abstractmethod
    async def delete_by_user_id(self, user_id: str) -> bool:
        """
        Delete profile by user ID.
        
        Args:
            user_id: User ID to delete profile for
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def search_profiles(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        visibility_filter: Optional[ProfileVisibility] = None
    ) -> List[Profile]:
        """
        Search profiles by display name, bio, or interests.
        
        Supports profile search and discovery for community features.
        Respects privacy settings by default.
        
        Args:
            query: Search query string
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            visibility_filter: Filter by profile visibility (default: PUBLIC only)
            
        Returns:
            List of Profile entities matching search criteria
        """
        pass
    
    @abstractmethod
    async def get_by_interests(
        self,
        interests: List[str],
        limit: int = 20,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles by plant-related interests.
        
        Supports interest-based community discovery.
        Only returns publicly visible profiles.
        
        Args:
            interests: List of interests to match
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities with matching interests
        """
        pass
    
    @abstractmethod
    async def get_by_location(
        self,
        location: str,
        radius_km: Optional[float] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles by location.
        
        Supports location-based community features and local plant groups.
        Only returns profiles with location sharing enabled.
        
        Args:
            location: Location to search around
            radius_km: Search radius in kilometers (if supported)
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities in the specified location
        """
        pass
    
    @abstractmethod
    async def get_by_experience_level(
        self,
        experience_level: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles by gardening experience level.
        
        Supports skill-based community grouping.
        Only returns publicly visible profiles.
        
        Args:
            experience_level: Experience level (beginner/intermediate/advanced)
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities with matching experience level
        """
        pass
    
    @abstractmethod
    async def get_most_followed(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles with most followers.
        
        Supports community leaderboards and discovery.
        Only returns publicly visible profiles.
        
        Args:
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities ordered by follower count
        """
        pass
    
    @abstractmethod
    async def get_most_active(
        self,
        days: int = 30,
        limit: int = 10,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get most active profiles by post count.
        
        Supports community engagement tracking.
        Only returns publicly visible profiles.
        
        Args:
            days: Number of days to look back for activity
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities ordered by recent activity
        """
        pass
    
    @abstractmethod
    async def get_by_language(
        self,
        language: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles by preferred language.
        
        Supports language-based community grouping.
        Only returns publicly visible profiles.
        
        Args:
            language: Language code (e.g., 'en', 'es', 'fr')
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities with matching language preference
        """
        pass
    
    @abstractmethod
    async def count_by_visibility(self, visibility: ProfileVisibility) -> int:
        """
        Count profiles by visibility setting.
        
        Args:
            visibility: Profile visibility to count
            
        Returns:
            Number of profiles with given visibility
        """
        pass
    
    @abstractmethod
    async def count_by_location(self, location: str) -> int:
        """
        Count profiles by location.
        
        Args:
            location: Location to count
            
        Returns:
            Number of profiles in given location
        """
        pass
    
    @abstractmethod
    async def get_profiles_without_photos(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles without profile photos.
        
        Supports profile completion campaigns.
        
        Args:
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities without profile photos
        """
        pass
    
    @abstractmethod
    async def get_incomplete_profiles(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles with missing key information.
        
        Supports profile completion tracking and user engagement.
        
        Args:
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities with incomplete information
        """
        pass
    
    @abstractmethod
    async def update_social_stats(
        self,
        profile_id: str,
        stats_update: Dict[str, int]
    ) -> bool:
        """
        Update social statistics efficiently.
        
        Optimized for frequent social stat updates from community interactions.
        
        Args:
            profile_id: Profile ID to update
            stats_update: Dictionary of stat name to new value
                         (followers_count, following_count, posts_count, plants_count)
            
        Returns:
            True if updated successfully, False if profile not found
        """
        pass
    
    @abstractmethod
    async def bulk_update_notification_preferences(
        self,
        user_ids: List[str],
        preference_updates: Dict[str, bool]
    ) -> int:
        """
        Bulk update notification preferences.
        
        Supports system-wide notification setting changes.
        
        Args:
            user_ids: List of user IDs to update
            preference_updates: Dictionary of preference updates
            
        Returns:
            Number of profiles updated
        """
        pass
    
    @abstractmethod
    async def get_profiles_by_notification_preference(
        self,
        preference_name: str,
        enabled: bool = True,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Profile]:
        """
        Get profiles by notification preference setting.
        
        Supports targeted notification campaigns.
        
        Args:
            preference_name: Name of notification preference
            enabled: Whether preference should be enabled or disabled
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of Profile entities with matching preference
        """
        pass
    
    @abstractmethod
    async def exists_by_user_id(self, user_id: str) -> bool:
        """
        Check if profile exists for user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if profile exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_profile_analytics(
        self,
        profile_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get profile analytics data.
        
        Supports profile insights and engagement metrics.
        
        Args:
            profile_id: Profile ID to get analytics for
            days: Number of days to analyze
            
        Returns:
            Dictionary with analytics data (views, interactions, growth, etc.)
        """
        pass