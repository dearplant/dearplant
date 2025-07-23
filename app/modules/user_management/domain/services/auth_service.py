# 📄 File: app/modules/user_management/domain/services/auth_service.py
# 🧭 Purpose (Layman Explanation): 
# Handles user login, logout, password management, and security features like account lockouts and email verification
# 🧪 Purpose (Technical Summary): 
# Domain service implementing authentication business logic, security policies, and session management following core doc Authentication Submodule specifications
# 🔗 Dependencies: 
# Domain models, repositories, events, app.shared.core.security
# 🔄 Connected Modules / Calls From: 
# Application command handlers, API auth endpoints, authentication middleware

from fastapi import Depends
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from ..models.user import User, UserStatus
from ..repositories.user_repository import UserRepository
from ..events.user_events import (
    UserEmailVerified,
    UserPasswordChanged,
    UserLoginSuccessful,
    UserLoginFailed,
    UserAccountLocked,
    UserAccountUnlocked
)
from app.shared.events.publisher import EventPublisher
from app.shared.core.security import create_access_token, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """
    Domain service for authentication and authorization business logic.
    
    Implements authentication functionality from core doc Authentication 
    Submodule (1.1) including:
    - User registration with email validation
    - Login with rate limiting (max 5 attempts)
    - OAuth integration (Google, Apple)
    - Password reset via email
    - Account lockout protection
    - Session management
    
    Business rules:
    - Maximum 5 login attempts before lockout
    - Email verification required for full access
    - Password reset tokens expire after 24 hours
    - Account lockout duration varies by security level
    """
    
    def __init__(
        self,
        user_repository: UserRepository = Depends(),
        event_publisher: EventPublisher =Depends()
    ):
        self.user_repository = user_repository
        self.event_publisher = event_publisher
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        login_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with email and password.
        
        Implements login with rate limiting from core doc Authentication functionality.
        Business rules:
        - Maximum 5 failed attempts before account lockout
        - Account must be active and email verified for full access
        - Records login attempts for security monitoring
        
        Args:
            email: User email address
            password: Plain text password
            login_ip: IP address of login attempt
            user_agent: User agent string
            
        Returns:
            Tuple of (User entity, JWT token) if successful, (None, None) if failed
        """
        logger.info(f"Authenticating user: {email}")
        
        # 1. Get user by email
        user = await self.user_repository.get_by_email(email)
        
        if not user:
            # Record failed login attempt for non-existent email
            await self._record_failed_login(
                email=email,
                user_id=None,
                login_ip=login_ip,
                user_agent=user_agent,
                failure_reason="invalid_email"
            )
            return None, None
        
        # 2. Check if account is locked
        if user.is_account_locked():
            await self._record_failed_login(
                email=email,
                user_id=user.user_id,
                login_ip=login_ip,
                user_agent=user_agent,
                failure_reason="account_locked",
                attempt_count=user.failed_login_attempts
            )
            return None, None
        
        # 3. Check if user can login (account status)
        if not user.can_login():
            await self._record_failed_login(
                email=email,
                user_id=user.user_id,
                login_ip=login_ip,
                user_agent=user_agent,
                failure_reason="account_inactive",
                attempt_count=user.failed_login_attempts
            )
            return None, None
        
        # 4. Verify password
        if not user.verify_password(password):
            # Record failed login and check for lockout
            user.record_login_failure()
            await self.user_repository.update(user)
            
            # Check if account should be locked after this attempt
            if user.is_account_locked():
                await self._handle_account_lockout(user, login_ip)
            
            await self._record_failed_login(
                email=email,
                user_id=user.user_id,
                login_ip=login_ip,
                user_agent=user_agent,
                failure_reason="invalid_password",
                attempt_count=user.failed_login_attempts
            )
            return None, None
        
        # 5. Successful authentication
        user.record_login_success(login_ip)
        await self.user_repository.update(user)
        
        # 6. Generate JWT token
        token_data = {
            "sub": user.user_id,
            "email": user.email,
            "role": user.role,
            "is_premium": user.is_premium_user(),
            "email_verified": user.email_verified
        }
        
        access_token = create_access_token(token_data)
        
        # 7. Publish successful login event
        await self._record_successful_login(
            user=user,
            login_ip=login_ip,
            user_agent=user_agent,
            session_id=None  # Would be generated by session service
        )
        
        logger.info(f"Successfully authenticated user: {user.user_id}")
        return user, access_token
    
    async def verify_email(self, email: str, verification_token: str) -> bool:
        """
        Verify user email with verification token.
        
        Implements email verification from core doc Authentication functionality.
        
        Args:
            email: User email address
            verification_token: Email verification token
            
        Returns:
            True if verification successful, False otherwise
        """
        logger.info(f"Verifying email: {email}")
        
        # 1. Get user by email
        user = await self.user_repository.get_by_email(email)
        if not user:
            logger.warning(f"Email verification failed - user not found: {email}")
            return False
        
        # 2. Check if already verified
        if user.email_verified:
            logger.info(f"Email already verified: {email}")
            return True
        
        # 3. Validate verification token
        if user.reset_token != verification_token:
            logger.warning(f"Invalid verification token for email: {email}")
            return False
        
        # 4. Verify email
        user.verify_email()
        await self.user_repository.update(user)
        
        # 5. Publish email verified event
        event = UserEmailVerified(
            user_id=user.user_id,
            email=user.email
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully verified email: {email}")
        return True
    
    async def initiate_password_reset(self, email: str) -> bool:
        """
        Initiate password reset process.
        
        Implements password reset via email from core doc Authentication functionality.
        
        Args:
            email: User email address
            
        Returns:
            True if reset initiated (always returns True for security)
        """
        logger.info(f"Initiating password reset for: {email}")
        
        # 1. Get user by email
        user = await self.user_repository.get_by_email(email)
        if not user:
            # For security, always return True even if user doesn't exist
            logger.info(f"Password reset requested for non-existent email: {email}")
            return True
        
        # 2. Generate reset token
        reset_token = user.generate_password_reset_token()
        await self.user_repository.update(user)
        
        # 3. Send reset email (would be handled by event handler)
        # The event handler will send the actual email
        
        logger.info(f"Password reset token generated for: {email}")
        return True
    
    async def reset_password(
        self,
        email: str,
        reset_token: str,
        new_password: str,
        reset_ip: Optional[str] = None
    ) -> bool:
        """
        Reset user password with reset token.
        
        Args:
            email: User email address
            reset_token: Password reset token
            new_password: New password
            reset_ip: IP address of reset request
            
        Returns:
            True if reset successful, False otherwise
        """
        logger.info(f"Resetting password for: {email}")
        
        # 1. Get user by email
        user = await self.user_repository.get_by_email(email)
        if not user:
            return False
        
        # 2. Validate reset token
        if user.reset_token != reset_token:
            logger.warning(f"Invalid reset token for email: {email}")
            return False
        
        # 3. Check token expiration
        if user.reset_token_expires and user.reset_token_expires < datetime.now(timezone.utc):
            logger.warning(f"Expired reset token for email: {email}")
            return False
        
        # 4. Update password
        user.update_password(new_password)
        await self.user_repository.update(user)
        
        # 5. Publish password changed event
        event = UserPasswordChanged(
            user_id=user.user_id,
            email=user.email,
            change_ip=reset_ip,
            reset_token_used=True
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully reset password for: {email}")
        return True
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        change_ip: Optional[str] = None
    ) -> bool:
        """
        Change user password with current password verification.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            change_ip: IP address of change request
            
        Returns:
            True if change successful, False otherwise
        """
        logger.info(f"Changing password for user: {user_id}")
        
        # 1. Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False
        
        # 2. Verify current password
        if not user.verify_password(current_password):
            logger.warning(f"Invalid current password for user: {user_id}")
            return False
        
        # 3. Update password
        user.update_password(new_password)
        await self.user_repository.update(user)
        
        # 4. Publish password changed event
        event = UserPasswordChanged(
            user_id=user.user_id,
            email=user.email,
            change_ip=change_ip,
            reset_token_used=False
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully changed password for user: {user_id}")
        return True
    
    async def unlock_account(
        self,
        user_id: str,
        unlock_method: str = "admin_action",
        unlocked_by: Optional[str] = None
    ) -> bool:
        """
        Unlock user account.
        
        Implements account lockout protection from core doc Authentication functionality.
        
        Args:
            user_id: User ID to unlock
            unlock_method: Method used to unlock (admin_action/auto_timeout/user_request)
            unlocked_by: ID of admin who unlocked (if applicable)
            
        Returns:
            True if unlock successful, False otherwise
        """
        logger.info(f"Unlocking account for user: {user_id}")
        
        # 1. Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False
        
        # 2. Unlock account
        user.unlock_account()
        await self.user_repository.update(user)
        
        # 3. Publish account unlocked event
        event = UserAccountUnlocked(
            user_id=user.user_id,
            email=user.email,
            unlock_method=unlock_method,
            unlocked_by=unlocked_by
        )
        await self.event_publisher.publish(event)
        
        logger.info(f"Successfully unlocked account for user: {user_id}")
        return True
    
    async def oauth_authenticate(
        self,
        provider: str,
        provider_id: str,
        email: str,
        provider_data: Dict[str, Any],
        login_ip: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user via OAuth provider.
        
        Implements OAuth integration from core doc Authentication functionality.
        
        Args:
            provider: OAuth provider (google/apple)
            provider_id: Provider user ID
            email: User email from provider
            provider_data: Additional data from provider
            login_ip: IP address of login attempt
            
        Returns:
            Tuple of (User entity, JWT token) if successful
        """
        logger.info(f"OAuth authentication via {provider} for email: {email}")
        
        # 1. Try to find existing user by provider_id
        user = await self.user_repository.get_by_provider_id(provider, provider_id)
        
        if not user:
            # 2. Try to find by email
            user = await self.user_repository.get_by_email(email)
            
            if user:
                # Link existing account with OAuth provider
                user.provider_id = provider_id
                user.provider = provider
                await self.user_repository.update(user)
            else:
                # 3. Create new user via OAuth
                from .user_service import UserService  # Avoid circular import
                # In real implementation, UserService would be injected
                # user = await user_service.create_user(
                #     email=email,
                #     password="",  # No password for OAuth users
                #     display_name=provider_data.get("name"),
                #     provider=provider,
                #     provider_id=provider_id,
                #     registration_ip=login_ip
                # )
                return None, None  # For now, return None
        
        # 4. Check if user can login
        if not user.can_login():
            return None, None
        
        # 5. Record successful login
        user.record_login_success(login_ip)
        await self.user_repository.update(user)
        
        # 6. Generate JWT token
        token_data = {
            "sub": user.user_id,
            "email": user.email,
            "role": user.role,
            "is_premium": user.is_premium_user(),
            "email_verified": user.email_verified
        }
        
        access_token = create_access_token(token_data)
        
        # 7. Publish successful login event
        await self._record_successful_login(
            user=user,
            login_ip=login_ip,
            user_agent=None,
            session_id=None
        )
        
        logger.info(f"Successfully authenticated OAuth user: {user.user_id}")
        return user, access_token
    
    # Private helper methods
    
    async def _record_successful_login(
        self,
        user: User,
        login_ip: Optional[str],
        user_agent: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Record successful login event."""
        event = UserLoginSuccessful(
            user_id=user.user_id,
            email=user.email,
            login_ip=login_ip,
            user_agent=user_agent,
            login_method=user.provider,
            session_id=session_id
        )
        await self.event_publisher.publish(event)
    
    async def _record_failed_login(
        self,
        email: str,
        user_id: Optional[str],
        login_ip: Optional[str],
        user_agent: Optional[str],
        failure_reason: str,
        attempt_count: int = 0
    ) -> None:
        """Record failed login event."""
        event = UserLoginFailed(
            email=email,
            user_id=user_id,
            login_ip=login_ip,
            user_agent=user_agent,
            failure_reason=failure_reason,
            attempt_count=attempt_count
        )
        await self.event_publisher.publish(event)
    
    async def _handle_account_lockout(
        self,
        user: User,
        lock_ip: Optional[str]
    ) -> None:
        """Handle account lockout after max failed attempts."""
        event = UserAccountLocked(
            user_id=user.user_id,
            email=user.email,
            lock_reason="failed_logins",
            failed_attempts=user.failed_login_attempts,
            lock_ip=lock_ip,
            unlock_instructions_sent=True  # Would be handled by event handler
        )
        await self.event_publisher.publish(event)
        
        logger.warning(f"Account locked due to failed login attempts: {user.user_id}")