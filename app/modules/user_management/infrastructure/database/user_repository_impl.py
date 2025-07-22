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

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.domain.models.user import User
from app.modules.user_management.infrastructure.database.models import UserModel

logger = logging.getLogger(__name__)


class UserRepositoryImpl(UserRepository):
    """
    SQLAlchemy implementation of the UserRepository interface.
    
    This repository handles all database operations for user entities,
    providing async operations with proper error handling and logging.
    """
    
    def __init__(self, session: AsyncSession):
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
            raise ValueError(f"User with email {user.email} already exists") from e
            
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
                .values(login_attempts=UserModel.login_attempts + 1)
                .returning(UserModel.login_attempts)
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
                .values(login_attempts=0)
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
            last_login=user.last_login,
            email_verified=user.email_verified,
            reset_token=user.reset_token,
            reset_token_expires=user.reset_token_expires,
            login_attempts=user.login_attempts,
            account_locked=user.account_locked,
            provider=user.provider,
            provider_id=user.provider_id,
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
            last_login=user_model.last_login,
            email_verified=user_model.email_verified,
            reset_token=user_model.reset_token,
            reset_token_expires=user_model.reset_token_expires,
            login_attempts=user_model.login_attempts,
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
        user_model.last_login = user.last_login
        user_model.email_verified = user.email_verified
        user_model.reset_token = user.reset_token
        user_model.reset_token_expires = user.reset_token_expires
        user_model.login_attempts = user.login_attempts
        user_model.account_locked = user.account_locked
        user_model.provider = user.provider
        user_model.provider_id = user.provider_id