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
from fastapi import Depends

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timedelta,date,datetime,time,timezone
from typing import Dict, Any, List, Optional

from app.modules.user_management.domain.repositories.profile_repository import ProfileRepository
from app.modules.user_management.domain.models.profile import Profile
from app.modules.user_management.infrastructure.database.models import ProfileModel, UserModel
from app.shared.infrastructure.database.session import get_db_session

# Domain models and exceptions  
from app.shared.core.exceptions import RepositoryError

logger = logging.getLogger(__name__)


class ProfileRepositoryImpl(ProfileRepository):
    """
    SQLAlchemy implementation of the ProfileRepository interface.
    
    This repository handles all database operations for profile entities,
    providing async operations with proper error handling and user relationship management.
    """
    
    def __init__(self, session = Depends(get_db_session)):

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
            raise ValueError(f"Profile already exists for user {profile.user_id} {str(e)}") from e
            
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
            experience_level=profile.experience_level
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
            experience_level=profile_model.experience_level
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
        profile_model.experience_level = profile.experience_level

    
    async def bulk_update_notification_preferences(
        self,
        session: AsyncSession,
        preferences_updates: List[Dict[str, Any]]
    ) -> int:
        try:
            updated_count = 0
            for update_data in preferences_updates:
                user_id = update_data.get('user_id')
                preferences = update_data.get('notification_preferences', {})
                
                if not user_id:
                    continue
                    
                query = (
                    update(ProfileModel)
                    .where(ProfileModel.user_id == user_id)
                    .values(
                        notification_preferences=preferences,
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                result = await session.execute(query)
                updated_count += result.rowcount
            
            await session.commit()
            logger.info(f"Bulk updated notification preferences for {updated_count} profiles")
            return updated_count
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to bulk update notification preferences: {e}")
            raise RepositoryError(f"Failed to bulk update notification preferences: {e}")

    async def count_by_location(self, session: AsyncSession, location: str) -> int:
        try:
            query = select(func.count(ProfileModel.profile_id)).where(
                ProfileModel.location.ilike(f"%{location}%")
            )
            result = await session.execute(query)
            count = result.scalar()
            
            logger.debug(f"Count of profiles in location {location}: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count profiles by location: {e}")
            raise RepositoryError(f"Failed to count profiles by location: {e}")

    async def count_by_visibility(self, session: AsyncSession, visibility: str) -> int:
        try:
            query = select(func.count(ProfileModel.profile_id)).where(
                ProfileModel.visibility == visibility
            )
            result = await session.execute(query)
            count = result.scalar()
            
            logger.debug(f"Count of profiles with visibility {visibility}: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count profiles by visibility: {e}")
            raise RepositoryError(f"Failed to count profiles by visibility: {e}")

    async def exists_by_user_id(self, session: AsyncSession, user_id: UUID) -> bool:
        try:
            query = select(func.count(ProfileModel.profile_id)).where(
                ProfileModel.user_id == user_id
            )
            result = await session.execute(query)
            count = result.scalar()
            
            exists = count > 0
            logger.debug(f"Profile exists for user {user_id}: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check if profile exists by user ID: {e}")
            raise RepositoryError(f"Failed to check if profile exists by user ID: {e}")

    async def get_by_experience_level(
        self,
        session: AsyncSession,
        experience_level: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            query = (
                select(ProfileModel)
                .where(ProfileModel.experience_level == experience_level)
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.created_at.desc())
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} profiles with experience level {experience_level}")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get profiles by experience level: {e}")
            raise RepositoryError(f"Failed to get profiles by experience level: {e}")

    async def get_by_interests(
        self,
        session: AsyncSession,
        interests: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            # Using JSON contains operation for interests array
            query = (
                select(ProfileModel)
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.created_at.desc())
            )
            
            # Add filter for interests if provided
            if interests:
                for interest in interests:
                    query = query.where(
                        ProfileModel.interests.contains([interest])
                    )
            
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} profiles with interests {interests}")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get profiles by interests: {e}")
            raise RepositoryError(f"Failed to get profiles by interests: {e}")

    async def get_by_language(
        self,
        session: AsyncSession,
        language: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            query = (
                select(ProfileModel)
                .where(ProfileModel.language == language)
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.created_at.desc())
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} profiles with language {language}")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get profiles by language: {e}")
            raise RepositoryError(f"Failed to get profiles by language: {e}")

    async def get_incomplete_profiles(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            # Consider profile incomplete if missing key fields
            query = (
                select(ProfileModel)
                .where(
                    or_(
                        ProfileModel.display_name.is_(None),
                        ProfileModel.display_name == "",
                        ProfileModel.bio.is_(None),
                        ProfileModel.bio == "",
                        ProfileModel.profile_photo.is_(None),
                        ProfileModel.location.is_(None)
                    )
                )
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.created_at.desc())
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} incomplete profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get incomplete profiles: {e}")
            raise RepositoryError(f"Failed to get incomplete profiles: {e}")

    async def get_most_active(
        self,
        session: AsyncSession,
        days: int = 30,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Order by activity score descending and recent updates
            query = (
                select(ProfileModel)
                .where(ProfileModel.updated_at >= cutoff_date)
                .offset(skip)
                .limit(limit)
                .order_by(
                    ProfileModel.activity_score.desc(),
                    ProfileModel.updated_at.desc()
                )
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} most active profiles in last {days} days")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get most active profiles: {e}")
            raise RepositoryError(f"Failed to get most active profiles: {e}")

    async def get_most_followed(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            query = (
                select(ProfileModel)
                .offset(skip)
                .limit(limit)
                .order_by(
                    ProfileModel.followers_count.desc(),
                    ProfileModel.created_at.desc()
                )
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} most followed profiles")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get most followed profiles: {e}")
            raise RepositoryError(f"Failed to get most followed profiles: {e}")

    async def get_profile_analytics(
        self,
        session: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        try:
            conditions = []
            if start_date:
                conditions.append(ProfileModel.created_at >= start_date)
            if end_date:
                conditions.append(ProfileModel.created_at <= end_date)
            
            # Total profiles
            total_query = select(func.count(ProfileModel.profile_id))
            if conditions:
                total_query = total_query.where(and_(*conditions))
            
            total_result = await session.execute(total_query)
            total_profiles = total_result.scalar()
            
            # Profiles by experience level
            experience_query = (
                select(ProfileModel.experience_level, func.count(ProfileModel.profile_id))
                .group_by(ProfileModel.experience_level)
            )
            if conditions:
                experience_query = experience_query.where(and_(*conditions))
            
            experience_result = await session.execute(experience_query)
            experience_stats = dict(experience_result.all())
            
            # Profiles by language
            language_query = (
                select(ProfileModel.language, func.count(ProfileModel.profile_id))
                .group_by(ProfileModel.language)
            )
            if conditions:
                language_query = language_query.where(and_(*conditions))
            
            language_result = await session.execute(language_query)
            language_stats = dict(language_result.all())
            
            # Completion stats
            complete_query = select(func.count(ProfileModel.profile_id)).where(
                and_(
                    ProfileModel.display_name.isnot(None),
                    ProfileModel.bio.isnot(None),
                    ProfileModel.profile_photo.isnot(None),
                    *conditions if conditions else [True]
                )
            )
            complete_result = await session.execute(complete_query)
            complete_profiles = complete_result.scalar()
            
            analytics = {
                "total_profiles": total_profiles,
                "complete_profiles": complete_profiles,
                "completion_rate": (complete_profiles / total_profiles * 100) if total_profiles > 0 else 0,
                "by_experience_level": experience_stats,
                "by_language": language_stats,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None
            }
            
            logger.debug(f"Retrieved profile analytics: {analytics}")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get profile analytics: {e}")
            raise RepositoryError(f"Failed to get profile analytics: {e}")

    async def get_profiles_by_notification_preference(
        self,
        session: AsyncSession,
        preference_key: str,
        preference_value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            # Using JSON path operation to check notification preferences
            query = (
                select(ProfileModel)
                .where(
                    ProfileModel.notification_preferences[preference_key].as_string() == str(preference_value)
                )
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.created_at.desc())
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} profiles with {preference_key}={preference_value}")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get profiles by notification preference: {e}")
            raise RepositoryError(f"Failed to get profiles by notification preference: {e}")

    async def get_profiles_without_photos(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            query = (
                select(ProfileModel)
                .where(
                    or_(
                        ProfileModel.profile_photo.is_(None),
                        ProfileModel.profile_photo == ""
                    )
                )
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.created_at.desc())
            )
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Retrieved {len(profiles)} profiles without photos")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to get profiles without photos: {e}")
            raise RepositoryError(f"Failed to get profiles without photos: {e}")

    async def search_profiles(
        self,
        session: AsyncSession,
        search_term: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Profile]:
        try:
            query = select(ProfileModel)
            
            # Base search conditions
            search_conditions = []
            if search_term:
                search_pattern = f"%{search_term}%"
                search_conditions.append(
                    or_(
                        ProfileModel.display_name.ilike(search_pattern),
                        ProfileModel.bio.ilike(search_pattern),
                        ProfileModel.location.ilike(search_pattern)
                    )
                )
            
            # Apply filters
            filter_conditions = []
            if filters:
                if "experience_level" in filters:
                    filter_conditions.append(ProfileModel.experience_level == filters["experience_level"])
                if "language" in filters:
                    filter_conditions.append(ProfileModel.language == filters["language"])
                if "location" in filters:
                    filter_conditions.append(ProfileModel.location.ilike(f"%{filters['location']}%"))
                if "has_photo" in filters:
                    if filters["has_photo"]:
                        filter_conditions.append(ProfileModel.profile_photo.isnot(None))
                    else:
                        filter_conditions.append(ProfileModel.profile_photo.is_(None))
                if "visibility" in filters:
                    filter_conditions.append(ProfileModel.visibility == filters["visibility"])
            
            # Combine all conditions
            all_conditions = search_conditions + filter_conditions
            if all_conditions:
                query = query.where(and_(*all_conditions))
            
            # Apply pagination and ordering
            query = (
                query
                .offset(skip)
                .limit(limit)
                .order_by(ProfileModel.followers_count.desc(), ProfileModel.created_at.desc())
            )
            
            result = await session.execute(query)
            profiles_db = result.scalars().all()
            
            profiles = [self._convert_to_domain(profile_db) for profile_db in profiles_db]
            logger.debug(f"Search returned {len(profiles)} profiles for term: {search_term}")
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to search profiles: {e}")
            raise RepositoryError(f"Failed to search profiles: {e}")

    async def update_social_stats(
        self,
        session: AsyncSession,
        user_id: UUID,
        followers_count: Optional[int] = None,
        following_count: Optional[int] = None,
        posts_count: Optional[int] = None,
        activity_score: Optional[float] = None
    ) -> bool:
        try:
            # Build update values
            update_values = {
                "updated_at": datetime.now(timezone.utc)
            }
            
            if followers_count is not None:
                update_values["followers_count"] = followers_count
            if following_count is not None:
                update_values["following_count"] = following_count
            if posts_count is not None:
                update_values["posts_count"] = posts_count
            if activity_score is not None:
                update_values["activity_score"] = activity_score
            
            query = (
                update(ProfileModel)
                .where(ProfileModel.user_id == user_id)
                .values(**update_values)
            )
            result = await session.execute(query)
            await session.commit()
            
            success = result.rowcount > 0
            if success:
                logger.debug(f"Updated social stats for user {user_id}")
            else:
                logger.warning(f"No profile found to update social stats for user {user_id}")
            
            return success
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update social stats: {e}")
            raise RepositoryError(f"Failed to update social stats: {e}")