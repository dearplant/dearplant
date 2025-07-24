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


# ================================================================
# 📄 File: app/modules/user_management/application/handlers/command_handlers.py
# 🧭 Purpose (Layman Explanation):
#     Handles user management commands: create, update, delete users.
# 🧪 Technical Summary:
#     CQRS command handlers orchestrating domain services, repositories,
#     and infrastructure for user management write operations.
# ================================================================

__all__ = [
    "CreateUserCommandHandler",
    "UpdateProfileCommandHandler",
    "DeleteUserCommandHandler",
]

# --- Standard library ---
import logging
from datetime import datetime, timedelta
from typing import Dict
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.infrastructure.database.session import get_db_session  # or however you access DB session

# --- Third-party ---
from passlib.context import CryptContext

# --- Application commands ---
from app.modules.user_management.application.commands.create_user import CreateUserCommand
from app.modules.user_management.application.commands.update_profile import UpdateProfileCommand
from app.modules.user_management.application.commands.delete_user import DeleteUserCommand

# --- Domain models ---
from app.modules.user_management.domain.models.user import User
from app.modules.user_management.domain.models.profile import Profile

# --- Domain services ---
from app.modules.user_management.domain.services.user_service import UserService
from app.modules.user_management.domain.services.auth_service import AuthService
from app.modules.user_management.domain.services.profile_service import ProfileService

# --- Domain repositories (interfaces) ---
from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.domain.repositories.profile_repository import ProfileRepository

# --- Infrastructure / External services ---
from app.modules.user_management.infrastructure.external.supabase_auth import SupabaseAuthService
from app.shared.events.publisher import EventPublisher

from app.modules.user_management.infrastructure.database.user_repository_impl import UserRepositoryImpl

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return UserRepositoryImpl(session)

class CreateUserCommandHandler:
    """
    Handles user creation command: registration, profile creation, and event publishing.
    """
    def __init__(
        self,
        user_service: UserService  = Depends(),
        auth_service: AuthService  = Depends(),
        profile_service: ProfileService  = Depends(),
        user_repository: UserRepository = Depends(get_user_repository),
        profile_repository: ProfileRepository  = Depends(),
        supabase_auth: SupabaseAuthService  = Depends(),
        event_publisher: EventPublisher  = Depends(),
    ):
        self._user_service = user_service
        self._auth_service = auth_service
        self._profile_service = profile_service
        self._user_repository = user_repository
        self._profile_repository = profile_repository
        self._supabase_auth = supabase_auth
        self._event_publisher = event_publisher

    async def handle(self, command: CreateUserCommand) -> Dict:
        """
        Handles the user creation command.
        """
        try:
            logger.info(f"Starting user creation process for email: {command.email}")
            existing_user = await self._user_repository.get_by_email(command.email)
            if existing_user:
                raise ValueError(f"User with email {command.email} already exists")

            password_hash = pwd_context.hash(command.password)
            user_data, profile_data = command.to_domain_entities()
            user_data["password_hash"] = password_hash
            user = User(**user_data)

            validation_result = await self._user_service.validate_new_user(user)
            if not validation_result.is_valid:
                raise ValueError(f"User validation failed: {validation_result.error_message}")

            created_user = await self._user_repository.create(user)
            profile_data["user_id"] = created_user.user_id
            profile = Profile(**profile_data)
            logger.info(f"profile_data keys: {profile_data.keys()}")
            validation_result = await self._profile_service.validate_new_profile(profile)
            if not validation_result.is_valid:
                await self._user_repository.delete(created_user.user_id)
                raise ValueError(f"Profile validation failed: {validation_result.error_message}")
            logger.info(f"profile data validated: {profile}")

            created_profile = await self._profile_repository.create(profile)

            # Pass the database session instead of trial_end_date
            session = await get_db_session().__anext__()  # Get the AsyncSession
            await self._user_service.create_free_trial_subscription(created_user.user_id, session)

            logger.info(f"created_user {created_user}")
            if command.provider == "email":
                user_payload = {
                    "user_id": str(created_user.user_id),
                    "email": created_user.email,
                    "password": created_user.password_hash,
                    "created_at": created_user.created_at.isoformat(),
                    "last_login_at": created_user.last_login_at.isoformat() if created_user.last_login_at else None,
                    "email_verified": created_user.email_verified,
                    "provider": created_user.provider,
                    "provider_id": created_user.provider_id,
                    "role": created_user.role.value if created_user.role else None,
                    "status": created_user.status.value if created_user.status else None,
                    "subscription_tier": created_user.subscription_tier.value if created_user.subscription_tier else None,
                    "display_name": created_user.display_name,
                    "profile_photo": created_user.profile_photo,
                    "language": created_user.language,
                    "timezone": created_user.timezone,
                    "theme": created_user.theme,
                    "notification_enabled": created_user.notification_enabled,
                    "updated_at": created_user.updated_at.isoformat() if created_user.updated_at else None,
                    "login_count": created_user.login_count,
                    "last_active_at": created_user.last_active_at.isoformat() if created_user.last_active_at else None,
                    "registration_ip": created_user.registration_ip,
                    "account_locked_at": created_user.account_locked_at.isoformat() if created_user.account_locked_at else None,
                }
                # sync_success = await self._supabase_auth.sync_user_with_supabase(created_user.user_id, user_payload)
                # if not sync_success:
                #     logger.warning(f"Failed to sync user with Supabase: {created_user.email}")

            trial_end_date = datetime.utcnow() + timedelta(days=7)
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
    Handles profile update command: validation, update, and event publishing.
    """
    def __init__(
        self,
        profile_service: ProfileService = Depends(),
        profile_repository: ProfileRepository = Depends(),
        event_publisher: EventPublisher = Depends(),
    ):
        self._profile_service = profile_service
        self._profile_repository = profile_repository
        self._event_publisher = event_publisher

    async def handle(self, command: UpdateProfileCommand) -> Dict:
        """
        Handles the profile update command.
        """
        try:
            logger.info(f"Starting profile update process for profile: {command.profile_id}")
            if not command.has_updates():
                raise ValueError("No updates provided in command")

            existing_profile = await self._profile_repository.get_by_id(command.profile_id)
            if not existing_profile:
                raise ValueError(f"Profile not found: {command.profile_id}")

            update_data = command.get_update_data()
            updated_profile = await self._profile_service.update_profile(
                existing_profile, update_data
            )

            validation_result = await self._profile_service.validate_profile_update(
                existing_profile, updated_profile
            )
            if not validation_result.is_valid:
                raise ValueError(f"Profile update validation failed: {validation_result.error_message}")

            saved_profile = await self._profile_repository.update(updated_profile)

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
    Handles user deletion command: authorization, cleanup, and event publishing.
    """
    def __init__(
        self,
        user_service: UserService = Depends(),
        auth_service: AuthService = Depends(),
        profile_service: ProfileService = Depends(),
        user_repository: UserRepository = Depends(),
        profile_repository: ProfileRepository = Depends(),
        supabase_auth: SupabaseAuthService = Depends(),
        event_publisher: EventPublisher = Depends(),
    ):
        self._user_service = user_service
        self._auth_service = auth_service
        self._profile_service = profile_service
        self._user_repository = user_repository
        self._profile_repository = profile_repository
        self._supabase_auth = supabase_auth
        self._event_publisher = event_publisher

    async def handle(self, command: DeleteUserCommand) -> Dict:
        """
        Handles the user deletion command.
        """
        try:
            logger.info(f"Starting user deletion process for user: {command.user_id}")
            existing_user = await self._user_repository.get_by_id(command.user_id)
            if not existing_user:
                raise ValueError(f"User not found: {command.user_id}")

            if command.requires_password_verification():
                password_valid = pwd_context.verify(
                    command.password_confirmation,
                    existing_user.password_hash
                )
                if not password_valid:
                    raise ValueError("Password confirmation failed")

            token_valid = await self._auth_service.validate_deletion_token(
                command.user_id,
                command.confirmation_token
            )
            if not token_valid:
                raise ValueError("Invalid confirmation token")

            if existing_user.account_locked and not command.is_admin_deletion():
                raise ValueError("Cannot delete locked account without admin privileges")

            cleanup_ops = command.get_cleanup_operations()

            if cleanup_ops["delete_user_data"]:
                profile_deleted = await self._profile_repository.delete_by_user_id(command.user_id)
                if profile_deleted:
                    await self._event_publisher.publish("ProfileDeleted", {
                        "user_id": str(command.user_id),
                        "deleted_at": datetime.utcnow().isoformat(),
                        "deletion_type": "cascade",
                    })

            if cleanup_ops["delete_subscription_data"]:
                await self._user_service.cancel_user_subscriptions(command.user_id)

            if cleanup_ops["revoke_all_sessions"]:
                await self._supabase_auth.revoke_token("user_sessions")

            if cleanup_ops["hard_delete"]:
                user_deleted = await self._user_repository.delete(command.user_id)
            else:
                result = await self._user_service.soft_delete_user(command.user_id)
                user_deleted = result.success

            if not user_deleted:
                raise Exception("Failed to delete user from database")

            if cleanup_ops["delete_uploaded_files"]:
                logger.info(f"File cleanup initiated for user: {command.user_id}")

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