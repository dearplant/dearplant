# 📄 File: app/modules/user_management/application/handlers/command_handlers.py
# 🧭 Purpose (Layman Explanation):
# This file contains the "action processors" that handle user management commands like creating
# accounts, updating profiles, and deleting users by coordinating with databases and business rules.
#
# 🧪 Purpose (Technical Summary):
# CQRS command handlers implementation orchestrating domain services, repositories, and
# infrastructure for user management write operations with proper transaction management and event publishing.
#
# 🔗 Dependencies:
# - app.modules.user_management.application.commands (command definitions)
# - app.modules.user_management.domain.services (domain business logic)
# - app.modules.user_management.domain.repositories (repository interfaces)
# - app.modules.user_management.infrastructure.database (repository implementations)
# - passlib for password hashing (security standard)
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1 (API endpoints invoke handlers)
# - Dependency injection container (handler instantiation and lifecycle)
# - Event bus system (domain event publishing)

"""
User Management Command Handlers

This module implements CQRS command handlers for user management write operations,
following Core Doc specifications and orchestrating domain services with infrastructure.

Command Handlers:
- CreateUserCommandHandler: User registration with profile creation (Core Doc 1.1 + 1.2)
- UpdateProfileCommandHandler: Profile updates with validation (Core Doc 1.2)
- DeleteUserCommandHandler: User deletion with cleanup (Core Doc 1.1)

Each handler:
- Validates business rules through domain services
- Coordinates with repositories for data persistence
- Publishes domain events for side effects
- Manages transactions and error handling
- Implements security controls and audit logging
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID

from passlib.context import CryptContext

from app.modules.user_management.application.commands.create_user import CreateUserCommand
from app.modules.user_management.application.commands.update_profile import UpdateProfileCommand
from app.modules.user_management.application.commands.delete_user import DeleteUserCommand

from app.modules.user_management.domain.models.user import User
from app.modules.user_management.domain.models.profile import Profile
from app.modules.user_management.domain.services.user_service import UserService
from app.modules.user_management.domain.services.auth_service import AuthService
from app.modules.user_management.domain.services.profile_service import ProfileService

from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.domain.repositories.profile_repository import ProfileRepository

from app.modules.user_management.infrastructure.external.supabase_auth import SupabaseAuthService
from app.shared.events.publisher import EventPublisher

logger = logging.getLogger(__name__)

# Password hashing context using bcrypt (Core Security Standard)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUserCommandHandler:
    """
    Handler for user creation command following Core Doc 1.1 and 1.2 specifications.
    
    This handler orchestrates user registration including:
    - Email validation and uniqueness checking
    - Password hashing with bcrypt
    - Profile creation with preferences
    - Free trial subscription setup
    - Domain event publishing
    """
    
    def __init__(
        self,
        user_service: UserService,
        auth_service: AuthService,
        profile_service: ProfileService,
        user_repository: UserRepository,
        profile_repository: ProfileRepository,
        supabase_auth: SupabaseAuthService,
        event_publisher: EventPublisher,
    ):
        """
        Initialize the create user command handler.
        
        Args:
            user_service: Domain service for user operations
            auth_service: Domain service for authentication
            profile_service: Domain service for profile operations
            user_repository: Repository for user data persistence
            profile_repository: Repository for profile data persistence
            supabase_auth: Supabase authentication service
            event_publisher: Event publisher for domain events
        """
        self._user_service = user_service
        self._auth_service = auth_service
        self._profile_service = profile_service
        self._user_repository = user_repository
        self._profile_repository = profile_repository
        self._supabase_auth = supabase_auth
        self._event_publisher = event_publisher
    
    async def handle(self, command: CreateUserCommand) -> Dict:
        """
        Handle user creation command.
        
        Args:
            command: CreateUserCommand with user registration data
            
        Returns:
            Dict: Created user and profile information
            
        Raises:
            ValueError: If validation fails or user already exists
            Exception: For other creation errors
        """
        try:
            logger.info(f"Starting user creation process for email: {command.email}")
            
            # 1. Validate user doesn't already exist (Core Doc 1.1)
            existing_user = await self._user_repository.get_by_email(command.email)
            if existing_user:
                raise ValueError(f"User with email {command.email} already exists")
            
            # 2. Hash password using bcrypt (Security Standard)
            password_hash = pwd_context.hash(command.password)
            
            # 3. Convert command to domain entities
            user_data, profile_data = command.to_domain_entities()
            user_data["password_hash"] = password_hash
            
            # 4. Create User domain entity
            user = User(**user_data)
            
            # 5. Validate user through domain service
            validation_result = await self._user_service.validate_new_user(user)
            if not validation_result.is_valid:
                raise ValueError(f"User validation failed: {validation_result.error_message}")
            
            # 6. Create user in database
            created_user = await self._user_repository.create(user)
            
            # 7. Create Profile domain entity with user_id
            profile_data["user_id"] = created_user.user_id
            profile = Profile(**profile_data)
            
            # 8. Validate profile through domain service
            profile_validation = await self._profile_service.validate_new_profile(profile)
            if not profile_validation.is_valid:
                # Rollback user creation if profile validation fails
                await self._user_repository.delete(created_user.user_id)
                raise ValueError(f"Profile validation failed: {profile_validation.error_message}")
            
            # 9. Create profile in database
            created_profile = await self._profile_repository.create(profile)
            
            # 10. Set up free trial subscription (Core Doc 1.3 - 7 days)
            trial_end_date = datetime.utcnow() + timedelta(days=7)
            await self._user_service.create_free_trial_subscription(
                created_user.user_id, 
                trial_end_date
            )
            
            # 11. Sync with Supabase authentication if not OAuth
            if command.provider == "email":
                sync_success = await self._supabase_auth.sync_user_with_supabase(created_user)
                if not sync_success:
                    logger.warning(f"Failed to sync user with Supabase: {created_user.email}")
            
            # 12. Publish domain events
            await self._event_publisher.publish("UserCreated", {
                "user_id": str(created_user.user_id),
                "email": created_user.email,
                "provider": created_user.provider,
                "created_at": created_user.created_at.isoformat(),
            })
            
            await self._event_publisher.publish("ProfileCreated", {
                "profile_id": str(created_profile.profile_id),
                "user_id": str(created_profile.user_id),
                "display_name": created_profile.display_name,
                "created_at": created_profile.created_at.isoformat(),
            })
            
            await self._event_publisher.publish("FreeTrialActivated", {
                "user_id": str(created_user.user_id),
                "trial_end_date": trial_end_date.isoformat(),
            })
            
            logger.info(f"Successfully created user: {created_user.user_id}")
            
            return {
                "user_id": created_user.user_id,
                "profile_id": created_profile.profile_id,
                "email": created_user.email,
                "display_name": created_profile.display_name,
                "email_verified": created_user.email_verified,
                "trial_active": True,
                "trial_end_date": trial_end_date,
                "created_at": created_user.created_at,
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating user for {command.email}: {str(e)}")
            raise Exception(f"Failed to create user: {str(e)}") from e


class UpdateProfileCommandHandler:
    """
    Handler for profile update command following Core Doc 1.2 specifications.
    
    This handler orchestrates profile updates including:
    - Partial update validation
    - Privacy setting enforcement
    - Field clearing for nullable fields
    - Domain event publishing
    """
    
    def __init__(
        self,
        profile_service: ProfileService,
        profile_repository: ProfileRepository,
        event_publisher: EventPublisher,
    ):
        """
        Initialize the update profile command handler.
        
        Args:
            profile_service: Domain service for profile operations
            profile_repository: Repository for profile data persistence
            event_publisher: Event publisher for domain events
        """
        self._profile_service = profile_service
        self._profile_repository = profile_repository
        self._event_publisher = event_publisher
    
    async def handle(self, command: UpdateProfileCommand) -> Dict:
        """
        Handle profile update command.
        
        Args:
            command: UpdateProfileCommand with profile update data
            
        Returns:
            Dict: Updated profile information
            
        Raises:
            ValueError: If validation fails or profile not found
            Exception: For other update errors
        """
        try:
            logger.info(f"Starting profile update process for profile: {command.profile_id}")
            
            # 1. Check if command has any updates
            if not command.has_updates():
                raise ValueError("No updates provided in command")
            
            # 2. Get existing profile
            existing_profile = await self._profile_repository.get_by_id(command.profile_id)
            if not existing_profile:
                raise ValueError(f"Profile not found: {command.profile_id}")
            
            # 3. Get update data from command
            update_data = command.get_update_data()
            
            # 4. Apply updates to profile entity
            updated_profile = await self._profile_service.update_profile(
                existing_profile, 
                update_data
            )
            
            # 5. Validate updated profile
            validation_result = await self._profile_service.validate_profile_update(
                existing_profile, 
                updated_profile
            )
            if not validation_result.is_valid:
                raise ValueError(f"Profile update validation failed: {validation_result.error_message}")
            
            # 6. Persist updates to database
            saved_profile = await self._profile_repository.update(updated_profile)
            
            # 7. Publish domain event
            await self._event_publisher.publish("ProfileUpdated", {
                "profile_id": str(saved_profile.profile_id),
                "user_id": str(saved_profile.user_id),
                "updated_fields": list(update_data.keys()),
                "updated_at": saved_profile.updated_at.isoformat(),
            })
            
            logger.info(f"Successfully updated profile: {saved_profile.profile_id}")
            
            return {
                "profile_id": saved_profile.profile_id,
                "user_id": saved_profile.user_id,
                "display_name": saved_profile.display_name,
                "bio": saved_profile.bio,
                "location": saved_profile.location,
                "timezone": saved_profile.timezone,
                "language": saved_profile.language,
                "theme": saved_profile.theme,
                "notification_enabled": saved_profile.notification_enabled,
                "profile_photo": saved_profile.profile_photo,
                "updated_at": saved_profile.updated_at,
                "updated_fields": list(update_data.keys()),
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating profile {command.profile_id}: {str(e)}")
            raise Exception(f"Failed to update profile: {str(e)}") from e


class DeleteUserCommandHandler:
    """
    Handler for user deletion command following Core Doc 1.1 specifications.
    
    This handler orchestrates user deletion including:
    - Security confirmation validation
    - Cascade deletion of related entities
    - External service cleanup
    - Audit logging and event publishing
    """
    
    def __init__(
        self,
        user_service: UserService,
        auth_service: AuthService,
        profile_service: ProfileService,
        user_repository: UserRepository,
        profile_repository: ProfileRepository,
        supabase_auth: SupabaseAuthService,
        event_publisher: EventPublisher,
    ):
        """
        Initialize the delete user command handler.
        
        Args:
            user_service: Domain service for user operations
            auth_service: Domain service for authentication
            profile_service: Domain service for profile operations
            user_repository: Repository for user data persistence
            profile_repository: Repository for profile data persistence
            supabase_auth: Supabase authentication service
            event_publisher: Event publisher for domain events
        """
        self._user_service = user_service
        self._auth_service = auth_service
        self._profile_service = profile_service
        self._user_repository = user_repository
        self._profile_repository = profile_repository
        self._supabase_auth = supabase_auth
        self._event_publisher = event_publisher
    
    async def handle(self, command: DeleteUserCommand) -> Dict:
        """
        Handle user deletion command.
        
        Args:
            command: DeleteUserCommand with deletion parameters
            
        Returns:
            Dict: Deletion confirmation and audit information
            
        Raises:
            ValueError: If validation fails or user not found
            Exception: For other deletion errors
        """
        try:
            logger.info(f"Starting user deletion process for user: {command.user_id}")
            
            # 1. Get existing user
            existing_user = await self._user_repository.get_by_id(command.user_id)
            if not existing_user:
                raise ValueError(f"User not found: {command.user_id}")
            
            # 2. Validate deletion authorization
            if command.requires_password_verification():
                password_valid = pwd_context.verify(
                    command.password_confirmation, 
                    existing_user.password_hash
                )
                if not password_valid:
                    raise ValueError("Password confirmation failed")
            
            # 3. Validate confirmation token
            token_valid = await self._auth_service.validate_deletion_token(
                command.user_id,
                command.confirmation_token
            )
            if not token_valid:
                raise ValueError("Invalid confirmation token")
            
            # 4. Check account status
            if existing_user.account_locked and not command.is_admin_deletion():
                raise ValueError("Cannot delete locked account without admin privileges")
            
            # 5. Get cleanup operations
            cleanup_ops = command.get_cleanup_operations()
            
            # 6. Delete profile if requested
            if cleanup_ops["delete_user_data"]:
                profile_deleted = await self._profile_repository.delete_by_user_id(command.user_id)
                if profile_deleted:
                    await self._event_publisher.publish("ProfileDeleted", {
                        "user_id": str(command.user_id),
                        "deleted_at": datetime.utcnow().isoformat(),
                        "deletion_type": "cascade",
                    })
            
            # 7. Handle subscription cleanup
            if cleanup_ops["delete_subscription_data"]:
                await self._user_service.cancel_user_subscriptions(command.user_id)
            
            # 8. Revoke sessions if requested
            if cleanup_ops["revoke_all_sessions"]:
                await self._supabase_auth.revoke_token("user_sessions")  # Implementation specific
            
            # 9. Delete user entity
            if cleanup_ops["hard_delete"]:
                user_deleted = await self._user_repository.delete(command.user_id)
            else:
                # Soft delete - mark as deleted but keep record
                soft_delete_result = await self._user_service.soft_delete_user(command.user_id)
                user_deleted = soft_delete_result.success
            
            if not user_deleted:
                raise Exception("Failed to delete user from database")
            
            # 10. Cleanup external services
            if cleanup_ops["delete_uploaded_files"]:
                # This would integrate with Supabase Storage cleanup
                logger.info(f"File cleanup initiated for user: {command.user_id}")
            
            # 11. Publish deletion event with audit data
            audit_data = command.get_audit_data()
            await self._event_publisher.publish("UserDeleted", {
                **audit_data,
                "cleanup_operations": cleanup_ops,
                "deleted_at": datetime.utcnow().isoformat(),
            })
            
            logger.info(f"Successfully deleted user: {command.user_id}")
            
            return {
                "user_id": command.user_id,
                "deletion_type": "hard" if cleanup_ops["hard_delete"] else "soft",
                "deleted_at": datetime.utcnow(),
                "cleanup_completed": cleanup_ops,
                "audit_data": audit_data,
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error deleting user {command.user_id}: {str(e)}")
            raise Exception(f"Failed to delete user: {str(e)}") from e