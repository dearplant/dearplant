# 📄 File: app/modules/user_management/infrastructure/database/profile_repository_impl.py
# 🧭 Purpose (Layman Explanation):
# This file handles all database operations for user profiles, including storing personal information,
# preferences, photos, and settings like language and theme choices for our plant care app users.
#
# 🧪 Purpose (Technical Summary):
# Concrete implementation of ProfileRepository interface using SQLAlchemy ORM,
# providing async database operations for profile entities with relationship management.
#
# 🔗 Dependencies:
# - app.modules.user_management.domain.repositories.profile_repository (interface)
# - app.modules.user_management.domain.models.profile (domain model)
# - app.modules.user_management.infrastructure.database.models (SQLAlchemy models)
# - SQLAlchemy async session and query operations
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers (profile command and query handlers)
# - app.modules.user_management.domain.services (profile service operations)
# - Dependency injection container (repository registration)

"""
Profile Repository Implementation

This module provides the concrete implementation of the ProfileRepository interface
using SQLAlchemy for database operations. It handles the mapping between
domain Profile entities and ProfileModel database records.

Features:
- Async database operations with proper error handling
- Domain model to SQLAlchemy model mapping
- Profile CRUD operations with user relationship management
- Location-based profile searching
- Privacy and preference management
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.modules.user_management.domain.repositories.profile_repository import ProfileRepository
from app.modules.user_management.domain.models.profile import Profile
from app.modules.user_management.infrastructure.database.models import ProfileModel, UserModel

logger = logging.getLogger(__name__)


class ProfileRepositoryImpl(ProfileRepository):
    """
    SQLAlchemy implementation of the ProfileRepository interface.
    
    This repository handles all database operations for profile entities,
    providing async operations with proper error handling and user relationship management.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the profile repository.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        self._session = session
    
    async def create(self, profile: Profile) -> Profile:
        """
        Create a new profile in the database.
        
        Args:
            profile: Domain Profile entity to create
            
        Returns:
            Profile: Created profile entity with generated ID
            
        Raises:
            ValueError: If profile for user already exists or user not found
            Exception: For other database errors
        """
        try:
            # Verify user exists
            user_exists = await self._user_exists(profile.user_id)
            if not user_exists:
                raise ValueError(f"User not found: {profile.user_id}")
            
            profile_model = self._domain_to_model(profile)
            
            self._session.add(profile_model)
            await self._session.flush()  # Get the generated ID
            
            logger.info(f"Created profile with ID: {profile_model.profile_id} for user: {profile.user_id}")
            return self._model_to_domain(profile_model)
            
        except IntegrityError as e:
            await self._session.rollback()
            logger.warning(f"Profile creation failed - profile already exists for user: {profile.user_id}")
            raise ValueError(f"Profile already exists for user {profile.user_id}") from e
            
        except ValueError:
            raise
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error during profile creation: {str(e)}")
            raise Exception(f"Failed to create profile: {str(e)}") from e
    
    async def get_by_id(self, profile_id: UUID) -> Optional[Profile]:
        """
        Retrieve a profile by its ID.
        
        Args:
            profile_id: UUID of the profile to retrieve
            
        Returns:
            Optional[Profile]: Profile entity if found, None otherwise
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.profile_id == profile_id)
            result = await self._session.execute(stmt)
            profile_model = result.scalar_one_or_none()
            
            if profile_model:
                logger.debug(f"Retrieved profile: {profile_id}")
                return self._model_to_domain(profile_model)
            
            logger.debug(f"Profile not found: {profile_id}")
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving profile {profile_id}: {str(e)}")
            raise Exception(f"Failed to retrieve profile: {str(e)}") from e
    
    async def get_by_user_id(self, user_id: UUID) -> Optional[Profile]:
        """
        Retrieve a profile by user ID.
        
        Args:
            user_id: UUID of the user whose profile to retrieve
            
        Returns:
            Optional[Profile]: Profile entity if found, None otherwise
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.user_id == user_id)
            result = await self._session.execute(stmt)
            profile_model = result.scalar_one_or_none()
            
            if profile_model:
                logger.debug(f"Retrieved profile for user: {user_id}")
                return self._model_to_domain(profile_model)
            
            logger.debug(f"Profile not found for user: {user_id}")
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving profile for user {user_id}: {str(e)}")
            raise Exception(f"Failed to retrieve profile for user: {str(e)}") from e
    
    async def update(self, profile: Profile) -> Profile:
        """
        Update an existing profile in the database.
        
        Args:
            profile: Domain Profile entity with updated data
            
        Returns:
            Profile: Updated profile entity
            
        Raises:
            ValueError: If profile not found
            Exception: For other database errors
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.profile_id == profile.profile_id)
            result = await self._session.execute(stmt)
            profile_model = result.scalar_one_or_none()
            
            if not profile_model:
                raise ValueError(f"Profile not found: {profile.profile_id}")
            
            # Update model fields from domain entity
            self._update_model_from_domain(profile_model, profile)
            
            await self._session.flush()
            
            logger.info(f"Updated profile: {profile.profile_id}")
            return self._model_to_domain(profile_model)
            
        except ValueError:
            raise
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error updating profile {profile.profile_id}: {str(e)}")
            raise Exception(f"Failed to update profile: {str(e)}") from e
    
    async def delete(self, profile_id: UUID) -> bool:
        """
        Delete a profile from the database.
        
        Args:
            profile_id: UUID of the profile to delete
            
        Returns:
            bool: True if profile was deleted, False if not found
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.profile_id == profile_id)
            result = await self._session.execute(stmt)
            profile_model = result.scalar_one_or_none()
            
            if not profile_model:
                logger.debug(f"Profile not found for deletion: {profile_id}")
                return False
            
            await self._session.delete(profile_model)
            await self._session.flush()
            
            logger.info(f"Deleted profile: {profile_id}")
            return True
            
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error deleting profile {profile_id}: {str(e)}")
            raise Exception(f"Failed to delete profile: {str(e)}") from e
    
    async def delete_by_user_id(self, user_id: UUID) -> bool:
        """
        Delete a profile by user ID.
        
        Args:
            user_id: UUID of the user whose profile to delete
            
        Returns:
            bool: True if profile was deleted, False if not found
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.user_id == user_id)
            result = await self._session.execute(stmt)
            profile_model = result.scalar_one_or_none()
            
            if not profile_model:
                logger.debug(f"Profile not found for deletion by user ID: {user_id}")
                return False
            
            await self._session.delete(profile_model)
            await self._session.flush()
            
            logger.info(f"Deleted profile for user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error deleting profile for user {user_id}: {str(e)}")
            raise Exception(f"Failed to delete profile for user: {str(e)}") from e
    
    async def get_by_location(self, location: str) -> List[Profile]:
        """
        Retrieve profiles by location for weather data integration.
        
        Args:
            location: Location string to search for
            
        Returns:
            List[Profile]: List of profiles in the specified location
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.location.ilike(f"%{location}%"))
            result = await self._session.execute(stmt)
            profile_models = result.scalars().all()
            
            profiles = [self._model_to_domain(model) for model in profile_models]
            logger.debug(f"Retrieved {len(profiles)} profiles for location: {location}")
            return profiles
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving profiles by location {location}: {str(e)}")
            raise Exception(f"Failed to retrieve profiles by location: {str(e)}") from e
    
    async def get_profiles_with_notifications_enabled(self) -> List[Profile]:
        """
        Retrieve all profiles with notifications enabled.
        
        Returns:
            List[Profile]: List of profiles with notifications enabled
        """
        try:
            stmt = select(ProfileModel).where(ProfileModel.notification_enabled == True)
            result = await self._session.execute(stmt)
            profile_models = result.scalars().all()
            
            profiles = [self._model_to_domain(model) for model in profile_models]
            logger.debug(f"Retrieved {len(profiles)} profiles with notifications enabled")
            return profiles
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving profiles with notifications: {str(e)}")
            raise Exception(f"Failed to retrieve profiles with notifications: {str(e)}") from e
    
    async def search_by_display_name(self, name_pattern: str, limit: int = 50) -> List[Profile]:
        """
        Search profiles by display name pattern.
        
        Args:
            name_pattern: Pattern to search for in display names
            limit: Maximum number of results to return
            
        Returns:
            List[Profile]: List of matching profiles
        """
        try:
            stmt = (
                select(ProfileModel)
                .where(ProfileModel.display_name.ilike(f"%{name_pattern}%"))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            profile_models = result.scalars().all()
            
            profiles = [self._model_to_domain(model) for model in profile_models]
            logger.debug(f"Found {len(profiles)} profiles matching name pattern: {name_pattern}")
            return profiles
            
        except SQLAlchemyError as e:
            logger.error(f"Database error searching profiles by name {name_pattern}: {str(e)}")
            raise Exception(f"Failed to search profiles by name: {str(e)}") from e
    
    async def _user_exists(self, user_id: UUID) -> bool:
        """
        Check if a user exists in the database.
        
        Args:
            user_id: UUID of the user to check
            
        Returns:
            bool: True if user exists, False otherwise
        """
        try:
            stmt = select(UserModel.user_id).where(UserModel.user_id == user_id)
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError:
            return False
    
    def _domain_to_model(self, profile: Profile) -> ProfileModel:
        """
        Convert a domain Profile entity to a ProfileModel.
        
        Args:
            profile: Domain Profile entity
            
        Returns:
            ProfileModel: SQLAlchemy model instance
        """
        return ProfileModel(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            display_name=profile.display_name,
            profile_photo=profile.profile_photo,
            bio=profile.bio,
            location=profile.location,
            timezone=profile.timezone,
            language=profile.language,
            theme=profile.theme,
            notification_enabled=profile.notification_enabled,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    def _model_to_domain(self, profile_model: ProfileModel) -> Profile:
        """
        Convert a ProfileModel to a domain Profile entity.
        
        Args:
            profile_model: SQLAlchemy model instance
            
        Returns:
            Profile: Domain Profile entity
        """
        return Profile(
            profile_id=profile_model.profile_id,
            user_id=profile_model.user_id,
            display_name=profile_model.display_name,
            profile_photo=profile_model.profile_photo,
            bio=profile_model.bio,
            location=profile_model.location,
            timezone=profile_model.timezone,
            language=profile_model.language,
            theme=profile_model.theme,
            notification_enabled=profile_model.notification_enabled,
            created_at=profile_model.created_at,
            updated_at=profile_model.updated_at,
        )
    
    def _update_model_from_domain(self, profile_model: ProfileModel, profile: Profile) -> None:
        """
        Update a ProfileModel instance with data from a domain Profile entity.
        
        Args:
            profile_model: SQLAlchemy model instance to update
            profile: Domain Profile entity with new data
        """
        profile_model.display_name = profile.display_name
        profile_model.profile_photo = profile.profile_photo
        profile_model.bio = profile.bio
        profile_model.location = profile.location
        profile_model.timezone = profile.timezone
        profile_model.language = profile.language
        profile_model.theme = profile.theme
        profile_model.notification_enabled = profile.notification_enabled
        profile_model.updated_at = profile.updated_at