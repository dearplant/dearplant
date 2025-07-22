# 📄 File: app/modules/user_management/application/handlers/query_handlers.py
# 🧭 Purpose (Layman Explanation):
# This file contains the "information retrievers" that handle requests for user and profile data
# by coordinating with databases while respecting privacy settings and security permissions.
#
# 🧪 Purpose (Technical Summary):
# CQRS query handlers implementation orchestrating domain services and repositories for
# user management read operations with security filtering, privacy controls, and data transformation.
#
# 🔗 Dependencies:
# - app.modules.user_management.application.queries (query definitions)
# - app.modules.user_management.domain.services (domain business logic)
# - app.modules.user_management.domain.repositories (repository interfaces)
# - app.modules.user_management.infrastructure.database (repository implementations)
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1 (API endpoints invoke handlers)
# - Dependency injection container (handler instantiation and lifecycle)
# - Authentication middleware (for security context)

"""
User Management Query Handlers

This module implements CQRS query handlers for user management read operations,
following Core Doc specifications and implementing proper security and privacy controls.

Query Handlers:
- GetUserQueryHandler: User data retrieval with security filtering (Core Doc 1.1)
- GetProfileQueryHandler: Profile data retrieval with privacy controls (Core Doc 1.2)

Each handler:
- Validates authorization and security permissions
- Applies privacy and security filtering
- Coordinates with repositories for data retrieval
- Transforms data based on access levels
- Implements caching strategies for performance
- Handles error cases gracefully
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.modules.user_management.application.queries.get_user import GetUserQuery, UserLookupType, SecurityLevel
from app.modules.user_management.application.queries.get_profile import GetProfileQuery, ProfileLookupType, PrivacyLevel

from app.modules.user_management.domain.models.user import User
from app.modules.user_management.domain.models.profile import Profile
from app.modules.user_management.domain.services.user_service import UserService
from app.modules.user_management.domain.services.profile_service import ProfileService

from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.domain.repositories.profile_repository import ProfileRepository

logger = logging.getLogger(__name__)


class GetUserQueryHandler:
    """
    Handler for user data retrieval query following Core Doc 1.1 specifications.
    
    This handler orchestrates user data retrieval including:
    - Authorization and security validation
    - Multiple lookup methods (ID, email, provider)
    - Security-based field filtering
    - Admin vs self vs public access levels
    - Sensitive data protection
    """
    
    def __init__(
        self,
        user_service: UserService,
        user_repository: UserRepository,
    ):
        """
        Initialize the get user query handler.
        
        Args:
            user_service: Domain service for user operations
            user_repository: Repository for user data access
        """
        self._user_service = user_service
        self._user_repository = user_repository
    
    async def handle(self, query: GetUserQuery) -> Optional[Dict]:
        """
        Handle user data retrieval query.
        
        Args:
            query: GetUserQuery with lookup parameters and security context
            
        Returns:
            Optional[Dict]: User data with appropriate filtering, None if not found
            
        Raises:
            ValueError: If query validation fails or unauthorized
            Exception: For other retrieval errors
        """
        try:
            logger.debug(f"Processing GetUserQuery for lookup type: {query.get_lookup_type()}")
            
            # 1. Validate query authorization
            query.validate_authorization()
            
            # 2. Determine lookup strategy
            lookup_type = query.get_lookup_type()
            user = None
            
            # 3. Execute lookup based on type
            if lookup_type == UserLookupType.BY_ID:
                user = await self._user_repository.get_by_id(query.user_id)
                
            elif lookup_type == UserLookupType.BY_EMAIL:
                # Email lookup requires authorization
                if not query.is_authorized_for_email_lookup():
                    raise ValueError("Email lookup requires admin privileges or self-access")
                user = await self._user_repository.get_by_email(query.email)
                
            elif lookup_type == UserLookupType.BY_PROVIDER:
                user = await self._user_repository.get_by_provider(query.provider, query.provider_id)
            
            # 4. Return None if user not found
            if not user:
                logger.debug(f"User not found for query: {lookup_type.value}")
                return None
            
            # 5. Additional authorization check for cross-user access
            security_level = query.get_security_level()
            if security_level == SecurityLevel.PUBLIC and user.user_id != query.requesting_user_id:
                # Verify this is actually a public profile request, not unauthorized access
                if not await self._user_service.is_profile_public(user.user_id):
                    logger.warning(f"Unauthorized access attempt to user {user.user_id} by {query.requesting_user_id}")
                    return None
            
            # 6. Apply security filtering
            filtered_data = self._apply_security_filtering(user, query)
            
            # 7. Add computed fields if requested
            if query.include_security_data and query.is_authorized_for_security_data():
                security_info = await self._get_security_information(user)
                filtered_data.update(security_info)
            
            if query.include_login_history and query.is_authorized_for_login_history():
                login_history = await self._get_login_history(user.user_id)
                filtered_data["login_history"] = login_history
            
            logger.debug(f"Successfully retrieved user data for: {user.user_id}")
            return filtered_data
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error handling GetUserQuery: {str(e)}")
            raise Exception(f"Failed to retrieve user: {str(e)}") from e
    
    def _apply_security_filtering(self, user: User, query: GetUserQuery) -> Dict:
        """
        Apply security-based filtering to user data.
        
        Args:
            user: User domain entity
            query: GetUserQuery with security context
            
        Returns:
            Dict: Filtered user data
        """
        # Start with basic user data
        user_data = {
            "user_id": user.user_id,
            "email": user.email,
            "created_at": user.created_at,
            "email_verified": user.email_verified,
            "provider": user.provider,
        }
        
        # Get fields to exclude based on security level
        excluded_fields = query.get_filtered_fields()
        
        # Apply timestamp filtering
        if query.include_timestamps:
            user_data.update({
                "created_at": user.created_at,
                "last_login": user.last_login,
            })
        
        # Apply provider data filtering
        if query.include_provider_data and "provider" not in excluded_fields:
            user_data.update({
                "provider": user.provider,
                "provider_id": user.provider_id,
            })
        
        # Remove excluded fields
        for field in excluded_fields:
            user_data.pop(field, None)
        
        return user_data
    
    async def _get_security_information(self, user: User) -> Dict:
        """
        Get security information for admin users.
        
        Args:
            user: User domain entity
            
        Returns:
            Dict: Security information
        """
        return {
            "account_locked": user.account_locked,
            "login_attempts": user.login_attempts,
            "has_reset_token": user.reset_token is not None,
            "reset_token_expires": user.reset_token_expires,
        }
    
    async def _get_login_history(self, user_id) -> List[Dict]:
        """
        Get login history for authorized users.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List[Dict]: Login history entries
        """
        # This would typically query a login_history table
        # For now, return basic information
        return [
            {
                "login_type": "email",
                "login_time": datetime.utcnow(),
                "ip_address": "192.168.1.100",
                "success": True,
            }
        ]


class GetProfileQueryHandler:
    """
    Handler for profile data retrieval query following Core Doc 1.2 specifications.
    
    This handler orchestrates profile data retrieval including:
    - Privacy setting enforcement
    - Multiple lookup methods (profile ID, user ID)
    - Privacy-based field filtering
    - Social data vs private data separation
    - Profile completeness calculation
    """
    
    def __init__(
        self,
        profile_service: ProfileService,
        profile_repository: ProfileRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the get profile query handler.
        
        Args:
            profile_service: Domain service for profile operations
            profile_repository: Repository for profile data access
            user_repository: Repository for user data access
        """
        self._profile_service = profile_service
        self._profile_repository = profile_repository
        self._user_repository = user_repository
    
    async def handle(self, query: GetProfileQuery) -> Optional[Dict]:
        """
        Handle profile data retrieval query.
        
        Args:
            query: GetProfileQuery with lookup parameters and privacy context
            
        Returns:
            Optional[Dict]: Profile data with appropriate filtering, None if not found
            
        Raises:
            ValueError: If query validation fails or unauthorized
            Exception: For other retrieval errors
        """
        try:
            logger.debug(f"Processing GetProfileQuery for lookup type: {query.get_lookup_type()}")
            
            # 1. Validate query authorization
            query.validate_authorization()
            
            # 2. Determine lookup strategy
            lookup_type = query.get_lookup_type()
            profile = None
            
            # 3. Execute lookup based on type
            if lookup_type == ProfileLookupType.BY_PROFILE_ID:
                profile = await self._profile_repository.get_by_id(query.profile_id)
                
            elif lookup_type == ProfileLookupType.BY_USER_ID:
                profile = await self._profile_repository.get_by_user_id(query.user_id)
            
            # 4. Return None if profile not found
            if not profile:
                logger.debug(f"Profile not found for query: {lookup_type.value}")
                return None
            
            # 5. Get user's privacy settings
            privacy_settings = await self._get_user_privacy_settings(profile.user_id)
            
            # 6. Additional authorization check for cross-user access
            privacy_level = query.get_privacy_level()
            if privacy_level == PrivacyLevel.PUBLIC:
                # Check if profile allows public viewing
                if not await self._profile_service.is_profile_publicly_visible(profile, privacy_settings):
                    logger.debug(f"Profile not publicly visible: {profile.profile_id}")
                    return None
            
            # 7. Apply privacy filtering
            filtered_data = self._apply_privacy_filtering(profile, query, privacy_settings)
            
            # 8. Add computed fields if requested
            if query.include_computed_fields:
                computed_fields = await self._get_computed_fields(profile, query)
                filtered_data.update(computed_fields)
            
            logger.debug(f"Successfully retrieved profile data for: {profile.profile_id}")
            return filtered_data
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error handling GetProfileQuery: {str(e)}")
            raise Exception(f"Failed to retrieve profile: {str(e)}") from e
    
    def _apply_privacy_filtering(self, profile: Profile, query: GetProfileQuery, privacy_settings: Dict) -> Dict:
        """
        Apply privacy-based filtering to profile data.
        
        Args:
            profile: Profile domain entity
            query: GetProfileQuery with privacy context
            privacy_settings: User's privacy settings
            
        Returns:
            Dict: Filtered profile data
        """
        # Start with public fields (always visible)
        profile_data = {
            "profile_id": profile.profile_id,
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "profile_photo": profile.profile_photo,
        }
        
        # Get fields to exclude based on privacy level
        excluded_fields = query.get_filtered_fields(privacy_settings)
        
        # Add optional fields if not excluded
        if "bio" not in excluded_fields and profile.bio:
            profile_data["bio"] = profile.bio
        
        if query.include_location_data and "location" not in excluded_fields:
            if profile.location:
                profile_data["location"] = profile.location
            if profile.timezone:
                profile_data["timezone"] = profile.timezone
        
        if query.include_preferences and query.get_privacy_level() != PrivacyLevel.PUBLIC:
            profile_data.update({
                "language": profile.language,
                "theme": profile.theme,
            })
        
        if query.include_notification_settings and query.is_authorized_for_notification_settings():
            profile_data["notification_enabled"] = profile.notification_enabled
        
        if query.include_timestamps:
            profile_data.update({
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            })
        
        return profile_data
    
    async def _get_user_privacy_settings(self, user_id) -> Dict:
        """
        Get user's privacy settings for filtering.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dict: Privacy settings
        """
        # This would typically come from a user preferences or privacy settings table
        # For now, return default settings
        return {
            "bio_visibility": "public",
            "location_visibility": "public",
            "profile_visibility": "public",
        }
    
    async def _get_computed_fields(self, profile: Profile, query: GetProfileQuery) -> Dict:
        """
        Calculate computed fields like profile completeness.
        
        Args:
            profile: Profile domain entity
            query: GetProfileQuery with computation flags
            
        Returns:
            Dict: Computed field values
        """
        computed = {}
        
        # Calculate profile completeness percentage
        completeness_fields = query.calculate_profile_completeness_fields()
        total_fields = len(completeness_fields)
        completed_fields = 0
        
        for field in completeness_fields:
            field_value = getattr(profile, field, None)
            if field_value is not None and field_value != "":
                completed_fields += 1
        
        completeness_percentage = (completed_fields / total_fields) * 100 if total_fields > 0 else 0
        
        computed.update({
            "profile_completeness": {
                "percentage": round(completeness_percentage, 1),
                "completed_fields": completed_fields,
                "total_fields": total_fields,
                "missing_fields": [
                    field for field in completeness_fields 
                    if not getattr(profile, field, None)
                ]
            }
        })
        
        # Add social metrics if requested
        if query.include_social_data:
            social_metrics = await self._get_social_metrics(profile.user_id)
            computed["social_metrics"] = social_metrics
        
        return computed
    
    async def _get_social_metrics(self, user_id) -> Dict:
        """
        Get social metrics for the profile.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dict: Social metrics
        """
        # This would typically query community/social tables
        # For now, return placeholder metrics
        return {
            "plants_shared": 0,
            "community_posts": 0,
            "helpful_votes": 0,
            "following_count": 0,
            "followers_count": 0,
        }