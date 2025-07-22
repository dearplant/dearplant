# 📄 File: app/modules/user_management/domain/services/user_service.py
# 🧭 Purpose (Layman Explanation): 
# Handles complex user account operations like creating accounts, managing subscriptions, and coordinating user data across the system
# 🧪 Purpose (Technical Summary): 
# Domain service implementing core user business logic, lifecycle management, and coordination between User, Profile, and Subscription entities
# 🔗 Dependencies: 
# Domain models, repositories, events, app.shared.core.security
# 🔄 Connected Modules / Calls From: 
# Application command handlers, API endpoints, authentication service

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from ..models.user import User, UserRole, UserStatus, SubscriptionTier
from ..models.profile import Profile
from ..models.subscription import Subscription, PlanType, PaymentMethod
from ..repositories.user_repository import UserRepository
from ..repositories.profile_repository import ProfileRepository
from ..events.user_events import (
    UserCreated,
    UserUpdated,
    UserDeleted,
    UserSubscriptionChanged
)
from app.shared.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class UserService:
    """
    Domain service for core user business operations.
    
    Implements business logic for user lifecycle management following
    core doc specifications from User Management Module (1.1, 1.2, 1.3).
    
    Responsibilities:
    - User creation and validation
    - User lifecycle management
    - Subscription management coordination
    - Business rule enforcement
    - Domain event publishing
    """
    
    def __init__(
        self,
        user_repository: UserRepository,
        profile_repository: ProfileRepository,
        event_publisher: EventPublisher
    ):
        self.user_repository = user_repository
        self.profile_repository = profile_repository
        self.event_publisher = event_publisher
    
    async def create_user(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        provider: str = "email",
        provider_id: Optional[str] = None,
        registration_ip: Optional[str] = None,
        start_trial: bool = False
    ) -> User:
        """
        Create a new user with full initialization.
        
        Implements user registration from core doc Authentication functionality.
        Business rules:
        - Email must be unique
        - Password must meet security requirements
        - Creates associated profile and subscription
        - Publishes UserCreated event
        
        Args:
            email: User email address
            password: Plain text password
            display_name: Optional display name
            provider: Authentication provider (email/google/apple)
            provider_id: External provider ID
            registration_ip: Registration IP address
            start_trial: Whether to start free trial
            
        Returns:
            Created User entity
            
        Raises:
            ValueError: If email already exists or validation fails
        """
        logger.info(f"Creating new user with email: {email}")
        
        # 1. Validate email uniqueness
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # 2. Validate password requirements
        self._validate_password_requirements(password)
        
        # 3. Create user entity
        user = User.create_new_user(
            email=email,
            password=password,
            display_name=display_name,
            provider=provider,
            provider_id=provider_id,
            registration_ip=registration_ip
        )
        
        # 4. Save user
        created_user = await self.user_repository.create(user)
        
        # 5. Create associated profile
        profile = Profile.create_new_profile(
            user_id=created_user.user_id,
            display_name=display_name or email.split('@')[0]
        )
        await self.profile_repository.create(profile)
        
        # 6. Create subscription
        subscription = Subscription.create_free_subscription(created_user.user_id)
        if start_trial:
            subscription.start_free_trial()
        
        # Note: Subscription repository would be injected in real implementation
        # await self.subscription_repository.create(subscription)
        
        # 7. Publish domain event
        event = UserCreated(
            user_id=created_user.user_id,
            email=created_user.email,
            display_name=display_name,
            provider=provider,
            registration_ip=registration_ip,
            subscription_tier=created_user.subscription_tier,
            trial_started=start_trial
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully created user: {created_user.user_id}")
        return created_user
    
    async def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> User:
        """
        Update user information with validation and event publishing.
        
        Args:
            user_id: User to update
            updates: Dictionary of field updates
            updated_by: Who performed the update
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If user not found or validation fails
        """
        logger.info(f"Updating user: {user_id}")
        
        # 1. Get existing user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # 2. Store previous values for event
        previous_values = {}
        
        # 3. Apply updates with validation
        for field, value in updates.items():
            if hasattr(user, field):
                previous_values[field] = getattr(user, field)
                
                # Special validation for certain fields
                if field == "email":
                    await self._validate_email_uniqueness(value, user_id)
                elif field == "password":
                    self._validate_password_requirements(value)
                    user.update_password(value)
                    continue
                
                setattr(user, field, value)
        
        # 4. Update timestamp
        user.updated_at = datetime.now(timezone.utc)
        
        # 5. Save user
        updated_user = await self.user_repository.update(user)
        
        # 6. Publish domain event
        if updates:  # Only publish if there were actual updates
            event = UserUpdated(
                user_id=user_id,
                updated_fields=updates,
                previous_values=previous_values
            )
            await self.event_publisher.publish(event)
        
        logger.info(f"Successfully updated user: {user_id}")
        return updated_user
    
    async def delete_user(
        self,
        user_id: str,
        deletion_reason: Optional[str] = None,
        soft_delete: bool = True
    ) -> None:
        """
        Delete user account with proper cleanup.
        
        Args:
            user_id: User to delete
            deletion_reason: Reason for deletion
            soft_delete: Whether to soft delete (default) or hard delete
            
        Raises:
            ValueError: If user not found
        """
        logger.info(f"Deleting user: {user_id} (soft_delete: {soft_delete})")
        
        # 1. Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # 2. Perform deletion
        if soft_delete:
            user.soft_delete()
            await self.user_repository.update(user)
        else:
            await self.user_repository.delete(user_id)
        
        # 3. Publish domain event
        event = UserDeleted(
            user_id=user_id,
            email=user.email,
            deletion_reason=deletion_reason,
            soft_delete=soft_delete
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully deleted user: {user_id}")
    
    async def upgrade_user_subscription(
        self,
        user_id: str,
        plan_type: PlanType,
        payment_method: PaymentMethod,
        external_subscription_id: Optional[str] = None
    ) -> User:
        """
        Upgrade user to premium subscription.
        
        Implements plan upgrade from core doc Subscription Management functionality.
        
        Args:
            user_id: User to upgrade
            plan_type: Premium plan type
            payment_method: Payment method used
            external_subscription_id: External payment provider subscription ID
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If user not found or invalid plan
        """
        logger.info(f"Upgrading user {user_id} to {plan_type}")
        
        # 1. Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # 2. Validate upgrade
        if plan_type == PlanType.FREE:
            raise ValueError("Cannot upgrade to free plan")
        
        # 3. Store previous subscription info
        previous_tier = user.subscription_tier
        
        # 4. Update user subscription
        user.upgrade_subscription(plan_type.value)
        updated_user = await self.user_repository.update(user)
        
        # 5. Publish subscription change event
        event = UserSubscriptionChanged(
            user_id=user_id,
            previous_tier=previous_tier,
            new_tier=plan_type.value,
            previous_status="active",
            new_status="active",
            change_reason="upgrade"
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully upgraded user {user_id} to {plan_type}")
        return updated_user
    
    async def downgrade_user_subscription(
        self,
        user_id: str,
        reason: Optional[str] = None
    ) -> User:
        """
        Downgrade user to free subscription.
        
        Args:
            user_id: User to downgrade
            reason: Reason for downgrade
            
        Returns:
            Updated User entity
        """
        logger.info(f"Downgrading user {user_id} to free")
        
        # 1. Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # 2. Store previous subscription info
        previous_tier = user.subscription_tier
        
        # 3. Downgrade user
        user.downgrade_to_free()
        updated_user = await self.user_repository.update(user)
        
        # 4. Publish subscription change event
        event = UserSubscriptionChanged(
            user_id=user_id,
            previous_tier=previous_tier,
            new_tier=SubscriptionTier.FREE,
            previous_status="active",
            new_status="active",
            change_reason=reason or "downgrade"
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully downgraded user {user_id} to free")
        return updated_user
    
    async def activate_user(self, user_id: str) -> User:
        """
        Activate user account.
        
        Args:
            user_id: User to activate
            
        Returns:
            Updated User entity
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.activate()
        return await self.user_repository.update(user)
    
    async def deactivate_user(self, user_id: str) -> User:
        """
        Deactivate user account.
        
        Args:
            user_id: User to deactivate
            
        Returns:
            Updated User entity
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.deactivate()
        return await self.user_repository.update(user)
    
    async def suspend_user(self, user_id: str, reason: Optional[str] = None) -> User:
        """
        Suspend user account.
        
        Args:
            user_id: User to suspend
            reason: Suspension reason
            
        Returns:
            Updated User entity
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.suspend()
        updated_user = await self.user_repository.update(user)
        
        logger.warning(f"User {user_id} suspended. Reason: {reason}")
        return updated_user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID to find
            
        Returns:
            User entity or None if not found
        """
        return await self.user_repository.get_by_id(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email to find
            
        Returns:
            User entity or None if not found
        """
        return await self.user_repository.get_by_email(email)
    
    async def get_users_by_status(
        self,
        status: UserStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Get users by status with pagination.
        
        Args:
            status: User status to filter by
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities
        """
        return await self.user_repository.get_by_status(status, limit, offset)
    
    async def get_premium_users(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Get premium users with pagination.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of premium User entities
        """
        premium_tiers = [SubscriptionTier.PREMIUM_MONTHLY, SubscriptionTier.PREMIUM_YEARLY]
        return await self.user_repository.get_by_subscription_tiers(premium_tiers, limit, offset)
    
    # Private helper methods
    
    def _validate_password_requirements(self, password: str) -> None:
        """
        Validate password meets security requirements.
        
        Args:
            password: Password to validate
            
        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
        
        # Check for common weak passwords
        weak_passwords = ["password", "12345678", "qwerty", "admin"]
        if password.lower() in weak_passwords:
            raise ValueError("Password is too common and not secure")
    
    async def _validate_email_uniqueness(self, email: str, exclude_user_id: Optional[str] = None) -> None:
        """
        Validate email is unique (excluding specified user).
        
        Args:
            email: Email to validate
            exclude_user_id: User ID to exclude from check
            
        Raises:
            ValueError: If email already exists
        """
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user and existing_user.user_id != exclude_user_id:
            raise ValueError(f"User with email {email} already exists")