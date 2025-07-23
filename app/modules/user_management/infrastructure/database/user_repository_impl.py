# 📄 File: app/modules/user_management/infrastructure/database/user_repository_impl.py
# 🧭 Purpose (Layman Explanation):
# This file handles all database operations for user accounts, like creating new users,
# finding existing users, updating their information, and managing user authentication data.
#
# 🧪 Purpose (Technical Summary):
# Concrete implementation of UserRepository interface using SQLAlchemy ORM,
# providing async database operations for user entities with error handling and logging.
#
# 🔗 Dependencies:
# - app.modules.user_management.domain.repositories.user_repository (interface)
# - app.modules.user_management.domain.models.user (domain model)
# - app.modules.user_management.infrastructure.database.models (SQLAlchemy models)
# - SQLAlchemy async session and query operations
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers (command and query handlers)
# - app.modules.user_management.domain.services (user service operations)
# - Dependency injection container (repository registration)

"""
User Repository Implementation

This module provides the concrete implementation of the UserRepository interface
using SQLAlchemy for database operations. It handles the mapping between
domain User entities and UserModel database records.

Features:
- Async database operations with proper error handling
- Domain model to SQLAlchemy model mapping
- Comprehensive CRUD operations for user management
- Email and provider-based user lookup
- Login attempt and security status management
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import Depends 

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, and_, or_, update
from datetime import timedelta,datetime,timezone,time
from typing import Dict, Any, List, Optional

from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.domain.models.user import User
from app.modules.user_management.infrastructure.database.models import UserModel
from app.modules.user_management.domain.models.user import UserStatus, SubscriptionTier
from app.shared.core.exceptions import RepositoryError
from app.shared.infrastructure.database.session import get_db_session


logger = logging.getLogger(__name__)


class UserRepositoryImpl(UserRepository):
    """
    SQLAlchemy implementation of the UserRepository interface.
    
    This repository handles all database operations for user entities,
    providing async operations with proper error handling and logging.
    """
    
    def __init__(self, session: AsyncSession = Depends(get_db_session)):
        """
        Initialize the user repository.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        self._session = session
    
    async def create(self, user: User) -> User:
        """
        Create a new user in the database.
        
        Args:
            user: Domain User entity to create
            
        Returns:
            User: Created user entity with generated ID
            
        Raises:
            ValueError: If user with email already exists
            Exception: For other database errors
        """
        try:
            user_model = self._domain_to_model(user)
            
            self._session.add(user_model)
            await self._session.flush()  # Get the generated ID
            
            logger.info(f"Created user with ID: {user_model.user_id}")
            return self._model_to_domain(user_model)
            
        except IntegrityError as e:
            await self._session.rollback()
            logger.warning(f"User creation failed - email already exists: {user.email}")
            raise ValueError(f"User with email {user.email} already exists {str(e)}") from e
            
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error during user creation: {str(e)}")
            raise Exception(f"Failed to create user: {str(e)}") from e
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by their ID.
        
        Args:
            user_id: UUID of the user to retrieve
            
        Returns:
            Optional[User]: User entity if found, None otherwise
        """
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = await self._session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model:
                logger.debug(f"Retrieved user: {user_id}")
                return self._model_to_domain(user_model)
            
            logger.debug(f"User not found: {user_id}")
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user {user_id}: {str(e)}")
            raise Exception(f"Failed to retrieve user: {str(e)}") from e
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            Optional[User]: User entity if found, None otherwise
        """
        try:
            stmt = select(UserModel).where(UserModel.email == email.lower())
            result = await self._session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model:
                logger.debug(f"Retrieved user by email: {email}")
                return self._model_to_domain(user_model)
            
            logger.debug(f"User not found by email: {email}")
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user by email {email}: {str(e)}")
            raise Exception(f"Failed to retrieve user by email: {str(e)}") from e
    
    async def get_by_provider(self, provider: str, provider_id: str) -> Optional[User]:
        """
        Retrieve a user by their OAuth provider information.
        
        Args:
            provider: OAuth provider name (google, apple, etc.)
            provider_id: Provider-specific user ID
            
        Returns:
            Optional[User]: User entity if found, None otherwise
        """
        try:
            stmt = select(UserModel).where(
                and_(
                    UserModel.provider == provider,
                    UserModel.provider_id == provider_id
                )
            )
            result = await self._session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model:
                logger.debug(f"Retrieved user by provider: {provider}/{provider_id}")
                return self._model_to_domain(user_model)
            
            logger.debug(f"User not found by provider: {provider}/{provider_id}")
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user by provider {provider}: {str(e)}")
            raise Exception(f"Failed to retrieve user by provider: {str(e)}") from e
    
    async def get_by_provider_id(self, provider_id: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.provider_id == provider_id)
            result = await self._session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if user_model:
                logger.debug(f"Found user by provider_id: {provider_id}")
                return self._model_to_domain(user_model)
            
            logger.debug(f"No user found with provider_id: {provider_id}")
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by provider_id {provider_id}: {e}")
            raise RepositoryError(f"Failed to get user by provider_id: {e}")
    
    async def update(self, user: User) -> User:
        """
        Update an existing user in the database.
        
        Args:
            user: Domain User entity with updated data
            
        Returns:
            User: Updated user entity
            
        Raises:
            ValueError: If user not found
            Exception: For other database errors
        """
        try:
            stmt = select(UserModel).where(UserModel.user_id == user.user_id)
            result = await self._session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                raise ValueError(f"User not found: {user.user_id}")
            
            # Update model fields from domain entity
            self._update_model_from_domain(user_model, user)
            
            await self._session.flush()
            
            logger.info(f"Updated user: {user.user_id}")
            return self._model_to_domain(user_model)
            
        except ValueError:
            raise
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error updating user {user.user_id}: {str(e)}")
            raise Exception(f"Failed to update user: {str(e)}") from e
    
    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user from the database.
        
        Args:
            user_id: UUID of the user to delete
            
        Returns:
            bool: True if user was deleted, False if not found
        """
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            result = await self._session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                logger.debug(f"User not found for deletion: {user_id}")
                return False
            
            await self._session.delete(user_model)
            await self._session.flush()
            
            logger.info(f"Deleted user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error deleting user {user_id}: {str(e)}")
            raise Exception(f"Failed to delete user: {str(e)}") from e
    
    async def get_locked_users(self) -> List[User]:
        """
        Retrieve all locked user accounts.
        
        Returns:
            List[User]: List of locked user entities
        """
        try:
            stmt = select(UserModel).where(UserModel.account_locked == True)
            result = await self._session.execute(stmt)
            user_models = result.scalars().all()
            
            users = [self._model_to_domain(model) for model in user_models]
            logger.debug(f"Retrieved {len(users)} locked users")
            return users
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving locked users: {str(e)}")
            raise Exception(f"Failed to retrieve locked users: {str(e)}") from e
    
    async def increment_login_attempts(self, user_id: UUID) -> int:
        """
        Increment the login attempt counter for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            int: New login attempt count
            
        Raises:
            ValueError: If user not found
        """
        try:
            stmt = (
                update(UserModel)
                .where(UserModel.user_id == user_id)
                .values(failed_login_attempts=UserModel.failed_login_attempts + 1)
                .returning(UserModel.failed_login_attempts)
            )
            
            result = await self._session.execute(stmt)
            new_count = result.scalar_one_or_none()
            
            if new_count is None:
                raise ValueError(f"User not found: {user_id}")
            
            await self._session.flush()
            
            logger.debug(f"Incremented login attempts for user {user_id}: {new_count}")
            return new_count
            
        except ValueError:
            raise
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error incrementing login attempts for {user_id}: {str(e)}")
            raise Exception(f"Failed to increment login attempts: {str(e)}") from e
    
    async def reset_login_attempts(self, user_id: UUID) -> None:
        """
        Reset the login attempt counter for a user.
        
        Args:
            user_id: UUID of the user
            
        Raises:
            ValueError: If user not found
        """
        try:
            stmt = (
                update(UserModel)
                .where(UserModel.user_id == user_id)
                .values(failed_login_attempts=0)
            )
            
            result = await self._session.execute(stmt)
            
            if result.rowcount == 0:
                raise ValueError(f"User not found: {user_id}")
            
            await self._session.flush()
            
            logger.debug(f"Reset login attempts for user: {user_id}")
            
        except ValueError:
            raise
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error(f"Database error resetting login attempts for {user_id}: {str(e)}")
            raise Exception(f"Failed to reset login attempts: {str(e)}") from e
    
    def _domain_to_model(self, user: User) -> UserModel:
        """
        Convert a domain User entity to a UserModel.
        
        Args:
            user: Domain User entity
            
        Returns:
            UserModel: SQLAlchemy model instance
        """
        return UserModel(
            user_id=user.user_id,
            email=user.email.lower(),
            password_hash=user.password_hash,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            email_verified=user.email_verified,
            reset_token=user.reset_token,
            reset_token_expires=user.reset_token_expires,
            failed_login_attempts=user.failed_login_attempts,
            account_locked_at=user.account_locked_at,
            account_locked=user.account_locked,
            provider=user.provider,
            provider_id=user.provider_id,
            status='active'
        )
    
    def _model_to_domain(self, user_model: UserModel) -> User:
        """
        Convert a UserModel to a domain User entity.
        
        Args:
            user_model: SQLAlchemy model instance
            
        Returns:
            User: Domain User entity
        """
        return User(
            user_id=user_model.user_id,
            email=user_model.email,
            password_hash=user_model.password_hash,
            created_at=user_model.created_at,
            last_login_at=user_model.last_login_at,
            email_verified=user_model.email_verified,
            reset_token=user_model.reset_token,
            reset_token_expires=user_model.reset_token_expires,
            failed_login_attempts=user_model.failed_login_attempts,
            account_locked_at=user_model.account_locked_at,
            account_locked=user_model.account_locked,
            provider=user_model.provider,
            provider_id=user_model.provider_id,
        )
    
    def _update_model_from_domain(self, user_model: UserModel, user: User) -> None:
        """
        Update a UserModel instance with data from a domain User entity.
        
        Args:
            user_model: SQLAlchemy model instance to update
            user: Domain User entity with new data
        """
        user_model.email = user.email.lower()
        user_model.password_hash = user.password_hash
        user_model.last_login_at = user.last_login_at
        user_model.email_verified = user.email_verified
        user_model.reset_token = user.reset_token
        user_model.reset_token_expires = user.reset_token_expires
        user_model.failed_login_attempts = user.failed_login_attempts
        user_model.account_locked_at = user.account_locked_at
        user_model.account_locked = user.account_locked
        user_model.provider = user.provider
        user_model.provider_id = user.provider_id


    async def bulk_update_status(
        self, 
        session: AsyncSession, 
        user_ids: List[UUID], 
        status: UserStatus
    ) -> int:
        try:
            query = (
                update(UserModel)
                .where(UserModel.user_id.in_(user_ids))
                .values(
                    status=status.value,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            result = await session.execute(query)
            await session.commit()
            
            logger.info(f"Bulk updated status for {result.rowcount} users to {status.value}")
            return result.rowcount
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to bulk update user status: {e}")
            raise RepositoryError(f"Failed to bulk update user status: {e}")

    async def count_by_status(self, session: AsyncSession, status: UserStatus) -> int:
        try:
            query = select(func.count(UserModel.user_id)).where(UserModel.status == status.value)
            result = await session.execute(query)
            count = result.scalar()
            
            logger.debug(f"Count of users with status {status.value}: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count users by status: {e}")
            raise RepositoryError(f"Failed to count users by status: {e}")

    async def count_by_subscription_tier(self, session: AsyncSession, tier: SubscriptionTier) -> int:
        try:
            query = select(func.count(UserModel.user_id)).where(UserModel.subscription_tier == tier.value)
            result = await session.execute(query)
            count = result.scalar()
            
            logger.debug(f"Count of users with subscription tier {tier.value}: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count users by subscription tier: {e}")
            raise RepositoryError(f"Failed to count users by subscription tier: {e}")

    async def get_by_status(
        self, 
        session: AsyncSession, 
        status: UserStatus, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            query = (
                select(UserModel)
                .where(UserModel.status == status.value)
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.created_at.desc())
            )
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Retrieved {len(users)} users with status {status.value}")
            return users
            
        except Exception as e:
            logger.error(f"Failed to get users by status: {e}")
            raise RepositoryError(f"Failed to get users by status: {e}")

    async def get_by_subscription_tiers(
        self, 
        session: AsyncSession, 
        tiers: List[SubscriptionTier], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            tier_values = [tier.value for tier in tiers]
            query = (
                select(UserModel)
                .where(UserModel.subscription_tier.in_(tier_values))
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.created_at.desc())
            )
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Retrieved {len(users)} users with subscription tiers {tier_values}")
            return users
            
        except Exception as e:
            logger.error(f"Failed to get users by subscription tiers: {e}")
            raise RepositoryError(f"Failed to get users by subscription tiers: {e}")

    async def get_locked_accounts(
        self, 
        session: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            query = (
                select(UserModel)
                .where(UserModel.account_locked.isnot(None))
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.account_locked.desc())
            )
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Retrieved {len(users)} locked accounts")
            return users
            
        except Exception as e:
            logger.error(f"Failed to get locked accounts: {e}")
            raise RepositoryError(f"Failed to get locked accounts: {e}")

    async def get_unverified_users(
        self, 
        session: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            query = (
                select(UserModel)
                .where(UserModel.email_verified_at.is_(None))
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.created_at.desc())
            )
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Retrieved {len(users)} unverified users")
            return users
            
        except Exception as e:
            logger.error(f"Failed to get unverified users: {e}")
            raise RepositoryError(f"Failed to get unverified users: {e}")

    async def get_user_registration_stats(
        self, 
        session: AsyncSession, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        try:
            conditions = []
            if start_date:
                conditions.append(UserModel.created_at >= start_date)
            if end_date:
                conditions.append(UserModel.created_at <= end_date)
            
            # Total registrations
            total_query = select(func.count(UserModel.user_id))
            if conditions:
                total_query = total_query.where(and_(*conditions))
            
            total_result = await session.execute(total_query)
            total_registrations = total_result.scalar()
            
            # Registrations by tier
            tier_query = (
                select(UserModel.subscription_tier, func.count(UserModel.user_id))
                .group_by(UserModel.subscription_tier)
            )
            if conditions:
                tier_query = tier_query.where(and_(*conditions))
            
            tier_result = await session.execute(tier_query)
            tier_stats = dict(tier_result.all())
            
            # Registrations by status
            status_query = (
                select(UserModel.status, func.count(UserModel.user_id))
                .group_by(UserModel.status)
            )
            if conditions:
                status_query = status_query.where(and_(*conditions))
            
            status_result = await session.execute(status_query)
            status_stats = dict(status_result.all())
            
            stats = {
                "total_registrations": total_registrations,
                "by_subscription_tier": tier_stats,
                "by_status": status_stats,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None
            }
            
            logger.debug(f"Retrieved user registration stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user registration stats: {e}")
            raise RepositoryError(f"Failed to get user registration stats: {e}")

    async def get_users_by_last_login(
        self, 
        session: AsyncSession, 
        days_ago: int = 30, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            query = (
                select(UserModel)
                .where(UserModel.last_login_at < cutoff_date)
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.last_login_at.desc())
            )
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Retrieved {len(users)} users not logged in for {days_ago} days")
            return users
            
        except Exception as e:
            logger.error(f"Failed to get users by last login: {e}")
            raise RepositoryError(f"Failed to get users by last login: {e}")

    async def get_users_with_failed_logins(
        self, 
        session: AsyncSession, 
        threshold: int = 5, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            query = (
                select(UserModel)
                .where(UserModel.failed_login_attempts >= threshold)
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.failed_login_attempts.desc())
            )
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Retrieved {len(users)} users with {threshold}+ failed logins")
            return users
            
        except Exception as e:
            logger.error(f"Failed to get users with failed logins: {e}")
            raise RepositoryError(f"Failed to get users with failed logins: {e}")

    async def search_users(
        self, 
        session: AsyncSession, 
        search_term: str, 
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        try:
            query = select(UserModel)
            
            # Base search conditions
            search_conditions = []
            if search_term:
                search_pattern = f"%{search_term}%"
                search_conditions.append(
                    or_(
                        UserModel.email.ilike(search_pattern),
                        UserModel.first_name.ilike(search_pattern),
                        UserModel.last_name.ilike(search_pattern)
                    )
                )
            
            # Apply filters
            filter_conditions = []
            if filters:
                if "status" in filters:
                    filter_conditions.append(UserModel.status == filters["status"])
                if "subscription_tier" in filters:
                    filter_conditions.append(UserModel.subscription_tier == filters["subscription_tier"])
                if "email_verified" in filters:
                    if filters["email_verified"]:
                        filter_conditions.append(UserModel.email_verified_at.isnot(None))
                    else:
                        filter_conditions.append(UserModel.email_verified_at.is_(None))
                if "created_after" in filters:
                    filter_conditions.append(UserModel.created_at >= filters["created_after"])
                if "created_before" in filters:
                    filter_conditions.append(UserModel.created_at <= filters["created_before"])
            
            # Combine all conditions
            all_conditions = search_conditions + filter_conditions
            if all_conditions:
                query = query.where(and_(*all_conditions))
            
            # Apply pagination and ordering
            query = (
                query
                .offset(skip)
                .limit(limit)
                .order_by(UserModel.created_at.desc())
            )
            
            result = await session.execute(query)
            users_db = result.scalars().all()
            
            users = [self._convert_to_domain(user_db) for user_db in users_db]
            logger.debug(f"Search returned {len(users)} users for term: {search_term}")
            return users
            
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            raise RepositoryError(f"Failed to search users: {e}")
        
    async def exists_by_email(self, session: AsyncSession, email: str) -> bool:
        try:
            query = select(func.count(UserModel.user_id)).where(UserModel.email == email)
            result = await session.execute(query)
            count = result.scalar()
            
            exists = count > 0
            logger.debug(f"User exists check for email {email}: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check if user exists by email: {e}")
            raise RepositoryError(f"Failed to check if user exists by email: {e}")

    async def exists_by_id(self, session: AsyncSession, user_id: UUID) -> bool:
        try:
            query = select(func.count(UserModel.user_id)).where(UserModel.user_id == user_id)
            result = await session.execute(query)
            count = result.scalar()
            
            exists = count > 0
            logger.debug(f"User exists check for ID {user_id}: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check if user exists by ID: {e}")
            raise RepositoryError(f"Failed to check if user exists by ID: {e}")