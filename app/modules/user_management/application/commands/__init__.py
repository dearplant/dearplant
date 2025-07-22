# 📄 File: app/modules/user_management/application/commands/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes all the "action commands" for user management, like creating new users,
# updating profiles, or deleting accounts - basically all the things users can DO in our app.
#
# 🧪 Purpose (Technical Summary):
# Commands package initialization implementing CQRS command pattern for user management
# write operations, providing command definitions for user lifecycle management.
#
# 🔗 Dependencies:
# - Pydantic models for command validation
# - app.modules.user_management.domain.models (domain entities)
# - Command handler interfaces and implementations
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.command_handlers (execute commands)
# - app.modules.user_management.presentation.api (API endpoints create commands)
# - Application layer initialization (command registration)

"""
User Management Commands

This module contains all command definitions for user management operations
following the CQRS (Command Query Responsibility Segregation) pattern.

Commands represent write operations and business use cases:
- CreateUserCommand: User registration and account creation
- UpdateProfileCommand: Profile information updates
- DeleteUserCommand: User account deletion and cleanup

All commands are immutable data structures that encapsulate
the parameters needed to perform business operations.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.user_management.application.commands.create_user import CreateUserCommand
    from app.modules.user_management.application.commands.update_profile import UpdateProfileCommand
    from app.modules.user_management.application.commands.delete_user import DeleteUserCommand

__all__ = [
    "CreateUserCommand",
    "UpdateProfileCommand",
    "DeleteUserCommand",
]