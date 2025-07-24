# 📄 File: app/modules/user_management/domain/services/user_service.py
# 🧭 Purpose (Layman Explanation): 
# This file contains the business logic for managing users - creating accounts, updating profiles,
# and handling all the rules about what users can and cannot do with their accounts.
# 🧪 Purpose (Technical Summary): 
# Domain service implementing core user management business logic including user creation,
# profile updates, validation rules, and user lifecycle management with proper separation of concerns.
# 🔗 Dependencies: 
# User domain models, repositories, events, validation logic
# 🔄 Connected Modules / Calls From: 
# Application command handlers, API endpoints, authentication services

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select, and_, update

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime, timedelta
 

from ..models.user import User
from ..models.profile import Profile
from ..models.subscription import Subscription
from ..repositories.user_repository import UserRepository
from ..repositories.profile_repository import ProfileRepository
from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.domain.repositories.subscription_repository import SubscriptionRepository
from app.shared.core.exceptions import ValidationError, RepositoryError
from app.modules.user_management.domain.models.subscription import SubscriptionPlan,PaymentMethod,SubscriptionStatus

from ..events.user_events import (
    UserCreated, 
    UserUpdated, 
    UserDeleted,
    UserProfileUpdated
)
from .....shared.core.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    DuplicateResourceError,
    DatabaseError
)

logger = logging.getLogger(__name__)

# A simple helper class for the validation result
class ValidationResult:
    def __init__(self, is_valid: bool = True, error_message: str = None):
        self.is_valid = is_valid
        self.error_message = error_message

class UserService:
    """
    Domain service for user management business logic.
    
    IMPORTANT: This is a domain service class used for business logic only.
    It should NEVER be used as a FastAPI response model or Pydantic field type.
    Always return DTOs/schemas from API endpoints, not domain service instances.
    """
    
    def __init__(
        self,
        user_repository: UserRepository = Depends(),
        profile_repository: ProfileRepository = Depends(),
        subscription_repository: SubscriptionRepository = Depends(),

    ):
        self.user_repository = user_repository
        self.profile_repository = profile_repository
        self.subscription_repository = subscription_repository
    
    # =========================================================================
    # USER CREATION AND LIFECYCLE
    # =========================================================================
    
    async def validate_new_user(self, user: User) -> ValidationResult:
        """
        Validates a new user object before it is created.
        """
        # You can add more complex validation logic here later.
        if not self._is_valid_email(user.email):
            return ValidationResult(is_valid=False, error_message="Invalid email format")

        # All checks passed
        logger.debug(f"User validation successful for email: {user.email}")
        return ValidationResult(is_valid=True)

    async def create_user(
        self,
        email: str,
        password_hash: str,
        display_name: Optional[str] = None,
        provider: str = "email",
        provider_id: Optional[str] = None
    ) -> User:
        """
        Create a new user with business rule validation.
        
        Args:
            email: User's email address
            password_hash: Hashed password
            display_name: Optional display name
            provider: Authentication provider
            provider_id: External provider ID
            
        Returns:
            User: Created user domain model
            
        Raises:
            DuplicateResourceError: If email already exists
            ValidationError: If input validation fails
        """
        try:
            # Validate email format
            if not self._is_valid_email(email):
                raise ValidationError(
                    "Invalid email format",
                    field="email",
                    value=email
                )
            
            # Check if user already exists
            existing_user = await self.user_repository.get_by_email(email)
            if existing_user:
                raise DuplicateResourceError(
                    "User with this email already exists",
                    resource_type="user",
                    field="email",
                    value=email
                )
            
            # Create user domain model
            user = User(
                user_id=str(uuid4()),
                email=email.lower().strip(),
                password_hash=password_hash,
                provider=provider,
                provider_id=provider_id,
                email_verified=False,
                account_locked=False,
                failed_login_attempts=0,
                created_at=datetime.utcnow(),
                last_login_at=None
            )
            
            # Save user
            saved_user = await self.user_repository.create(user)
            
            # Create default profile
            await self._create_default_profile(
                user_id=saved_user.user_id,
                display_name=display_name or email.split('@')[0]
            )
            
            # Publish domain event
            await self._publish_event(UserCreated(
                user_id=saved_user.user_id,
                email=saved_user.email,
                provider=provider
            ))
            
            logger.info(f"User created successfully: {saved_user.user_id}")
            return saved_user
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            if isinstance(e, (DuplicateResourceError, ValidationError)):
                raise
            raise ValidationError(f"User creation failed: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID with business logic validation.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        try:
            if not self._is_valid_uuid(user_id):
                raise ValidationError(
                    "Invalid user ID format",
                    field="user_id",
                    value=user_id
                )
            
            user = await self.user_repository.get_by_id(user_id)
            
            if user:
                logger.debug(f"User retrieved: {user_id}")
            else:
                logger.debug(f"User not found: {user_id}")
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            if isinstance(e, ValidationError):
                raise
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email with validation.
        
        Args:
            email: User's email address
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        try:
            if not self._is_valid_email(email):
                raise ValidationError(
                    "Invalid email format",
                    field="email",
                    value=email
                )
            
            user = await self.user_repository.get_by_email(email.lower().strip())
            
            if user:
                logger.debug(f"User found by email: {email}")
            else:
                logger.debug(f"User not found by email: {email}")
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            if isinstance(e, ValidationError):
                raise
            return None
    
    # =========================================================================
    # USER UPDATES AND MANAGEMENT
    # =========================================================================
    
    async def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
        updated_by: str
    ) -> User:
        """
        Update user with business rule validation.
        
        Args:
            user_id: User identifier
            updates: Fields to update
            updated_by: ID of user making the update
            
        Returns:
            User: Updated user
            
        Raises:
            NotFoundError: If user not found
            AuthorizationError: If update not authorized
            ValidationError: If validation fails
        """
        try:
            # Get existing user
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise NotFoundError(
                    "User not found",
                    resource_type="user",
                    resource_id=user_id
                )
            
            # Validate authorization (user can update self, admin can update anyone)
            if not await self._can_update_user(user_id, updated_by):
                raise AuthorizationError(
                    "Not authorized to update this user",
                    resource_type="user",
                    resource_id=user_id
                )
            
            # Validate and apply updates
            validated_updates = await self._validate_user_updates(updates)
            
            # Update user
            updated_user = await self.user_repository.update(user_id, validated_updates)
            
            # Publish domain event
            await self._publish_event(UserUpdated(
                user_id=user_id,
                updated_fields=list(validated_updates.keys()),
                updated_by=updated_by
            ))
            
            logger.info(f"User updated successfully: {user_id}")
            return updated_user
            
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            if isinstance(e, (NotFoundError, AuthorizationError, ValidationError)):
                raise
            raise ValidationError(f"User update failed: {str(e)}")
    
    async def delete_user(
        self,
        user_id: str,
        deleted_by: str,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete user (soft delete by default).
        
        Args:
            user_id: User identifier
            deleted_by: ID of user performing deletion
            soft_delete: Whether to soft delete or hard delete
            
        Returns:
            bool: True if successful
            
        Raises:
            NotFoundError: If user not found
            AuthorizationError: If deletion not authorized
        """
        try:
            # Get existing user
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise NotFoundError(
                    "User not found",
                    resource_type="user",
                    resource_id=user_id
                )
            
            # Validate authorization
            if not await self._can_delete_user(user_id, deleted_by):
                raise AuthorizationError(
                    "Not authorized to delete this user",
                    resource_type="user",
                    resource_id=user_id
                )
            
            # Perform deletion
            if soft_delete:
                # Soft delete - mark as deleted
                await self.user_repository.update(user_id, {
                    "account_locked": True,
                    "deleted_at": datetime.utcnow()
                })
            else:
                # Hard delete - remove from database
                await self.user_repository.delete(user_id)
            
            # Publish domain event
            await self._publish_event(UserDeleted(
                user_id=user_id,
                deleted_by=deleted_by,
                soft_delete=soft_delete
            ))
            
            logger.info(f"User deleted successfully: {user_id} (soft={soft_delete})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            if isinstance(e, (NotFoundError, AuthorizationError)):
                raise
            raise ValidationError(f"User deletion failed: {str(e)}")
    
    # =========================================================================
    # AUTHENTICATION SUPPORT
    # =========================================================================
    
    async def verify_user_credentials(
        self,
        email: str,
        password_hash: str
    ) -> Optional[User]:
        """
        Verify user credentials for authentication.
        
        Args:
            email: User's email
            password_hash: Hashed password to verify
            
        Returns:
            Optional[User]: User if credentials valid, None otherwise
        """
        try:
            user = await self.get_user_by_email(email)
            
            if not user:
                return None
            
            # Check if account is locked
            if user.account_locked:
                raise AuthenticationError(
                    "Account is locked. Please contact support.",
                    user_id=user.user_id
                )
            
            # Verify password hash
            if user.password_hash != password_hash:
                # Increment failed login attempts
                await self._increment_login_attempts(user.user_id)
                return None
            
            # Reset login attempts on successful auth
            await self._reset_login_attempts(user.user_id)
            
            # Update last login
            await self.user_repository.update(user.user_id, {
                "last_login_at": datetime.utcnow()
            })
            
            logger.info(f"User credentials verified: {user.user_id}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to verify credentials: {e}")
            if isinstance(e, AuthenticationError):
                raise
            return None
    
    async def lock_user_account(
        self,
        user_id: str,
        reason: str,
        locked_by: str
    ) -> bool:
        """
        Lock user account for security reasons.
        
        Args:
            user_id: User identifier
            reason: Reason for locking
            locked_by: ID of user/system locking account
            
        Returns:
            bool: True if successful
        """
        try:
            await self.user_repository.update(user_id, {
                "account_locked": True,
                "lock_reason": reason,
                "locked_at": datetime.utcnow(),
                "locked_by": locked_by
            })
            
            logger.warning(f"User account locked: {user_id} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to lock user account: {e}")
            return False
    
    # =========================================================================
    # PROFILE MANAGEMENT
    # =========================================================================
    
    async def _create_default_profile(
        self,
        user_id: str,
        display_name: str
    ) -> Profile:
        """Create default profile for new user."""
        try:
            profile = Profile(
                profile_id=str(uuid4()),
                user_id=user_id,
                display_name=display_name,
                bio=None,
                profile_photo=None,
                location=None,
                timezone="UTC",
                language="en",
                theme="auto",
                notification_enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            saved_profile = await self.profile_repository.create(profile)
            logger.debug(f"Default profile created for user: {user_id}")
            return saved_profile
            
        except Exception as e:
            logger.error(f"Failed to create default profile: {e}")
            raise ValidationError(f"Profile creation failed: {str(e)}")
    
    # =========================================================================
    # SUBSCRIBTION MANAGEMENT
    # =========================================================================

    async def create_free_trial_subscription(
        self,
        user_id: UUID,
        session: AsyncSession
    ) -> Subscription:
        """
        Create a free trial subscription for a new user.
        
        According to core documentation: "Free trial activation (7 days)"
        
        Args:
            user_id: User UUID
            session: Database session
            
        Returns:
            SubscriptionModel: Created subscription with active trial
            
        Raises:
            RepositoryError: If subscription creation fails
            ValidationError: If user already has a subscription
        """
        from datetime import datetime, timezone, timedelta
        from uuid import uuid4
        
        try:
            # Check if user already has a subscription
            existing_subscription = await self.subscription_repository.get_by_user_id(user_id)
            if existing_subscription:
                raise ValidationError("User already has a subscription")
            
            # Create trial subscription data
            trial_start_date = datetime.now(timezone.utc)
            trial_end_date = trial_start_date + timedelta(days=7)  # 7-day free trial
            
            subscription_data = {
                "subscription_id": str(uuid4()),
                "user_id": str(user_id),  # Ensure user_id is a string
                "plan_type": SubscriptionPlan.FREE.value,  # Explicitly use string value
                "status": SubscriptionStatus.ACTIVE.value,
                "trial_active": True,
                "trial_start_date": trial_start_date,
                "trial_end_date": trial_end_date,
                "auto_renew": False,
                "created_at": trial_start_date,
                "updated_at": trial_start_date,
                "payment_method": PaymentMethod.NONE.value
            }
            
            # Create subscription using repository
            subscription = await self.subscription_repository.create(subscription_data)
            
            # Update user's subscription tier
            await self.user_repository.update_subscription_tier(user_id, "free")
            
            logger.info(f"Free trial subscription created for user {user_id}, expires: {trial_end_date}")
            
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to create free trial subscription for user {user_id}: {e}")
            await session.rollback()
            raise
    # =========================================================================
    # VALIDATION HELPERS
    # =========================================================================
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Validate UUID format."""
        try:
            UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    async def _validate_user_updates(
        self, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate user update data."""
        validated = {}
        
        # Validate allowed fields
        allowed_fields = {
            'email', 'password_hash', 'email_verified', 
            'account_locked_at', 'provider', 'provider_id','account_locked'
        }
        
        for field, value in updates.items():
            if field not in allowed_fields:
                raise ValidationError(
                    f"Field '{field}' is not allowed for update",
                    field=field
                )
            
            # Field-specific validation
            if field == 'email' and not self._is_valid_email(value):
                raise ValidationError(
                    "Invalid email format",
                    field="email",
                    value=value
                )
            
            validated[field] = value
        
        return validated
    
    async def _can_update_user(self, user_id: str, updater_id: str) -> bool:
        """Check if user can be updated by updater."""
        # User can update themselves
        if user_id == updater_id:
            return True
        
        # Check if updater is admin (implement admin check logic)
        # For now, only allow self-updates
        return False
    
    async def _can_delete_user(self, user_id: str, deleter_id: str) -> bool:
        """Check if user can be deleted by deleter."""
        # User can delete themselves
        if user_id == deleter_id:
            return True
        
        # Check if deleter is admin
        # For now, only allow self-deletion
        return False
    
    # =========================================================================
    # LOGIN ATTEMPT MANAGEMENT
    # =========================================================================
    
    async def _increment_login_attempts(self, user_id: str) -> None:
        """Increment failed login attempts and lock if necessary."""
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                return
            
            new_attempts = user.failed_login_attempts + 1
            updates = {"failed_login_attempts": new_attempts}
            
            # Lock account after 5 failed attempts
            if new_attempts >= 5:
                updates.update({
                    "account_locked": True,
                    "lock_reason": "Too many failed login attempts",
                    "locked_at": datetime.utcnow()
                })
                logger.warning(f"Account locked due to failed attempts: {user_id}")
            
            await self.user_repository.update(user_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to increment login attempts: {e}")
    
    async def _reset_login_attempts(self, user_id: str) -> None:
        """Reset failed login attempts on successful login."""
        try:
            await self.user_repository.update(user_id, {
                "failed_login_attempts": 0
            })
        except Exception as e:
            logger.error(f"Failed to reset login attempts: {e}")
    
    # =========================================================================
    # EVENT PUBLISHING
    # =========================================================================
    
    async def _publish_event(self, event) -> None:
        """Publish domain event."""
        try:
            # In a real implementation, this would publish to an event bus
            # For now, just log the event
            logger.info(f"Domain event published: {event.__class__.__name__}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

# =============================================================================
# DEPENDENCY INJECTION HELPERS
# =============================================================================

def get_user_service(
    user_repository: UserRepository,
    profile_repository: ProfileRepository
) -> UserService:
    """
    Factory function to create UserService instance.
    
    This function should be used with FastAPI's Depends() for dependency injection.
    NEVER return UserService directly from API endpoints as response models.
    
    Args:
        user_repository: User repository implementation
        profile_repository: Profile repository implementation
        
    Returns:
        UserService: Configured user service instance
    """
    return UserService(
        user_repository=user_repository,
        profile_repository=profile_repository
    )

