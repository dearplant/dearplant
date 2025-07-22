# 📄 File: app/modules/user_management/application/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes the application layer for user management, which contains the business
# logic commands (like "create user") and queries (like "get user info") that our app uses.
#
# 🧪 Purpose (Technical Summary):
# Application layer initialization implementing CQRS pattern with commands, queries, handlers,
# and DTOs for user management business operations and data transfer objects.
#
# 🔗 Dependencies:
# - app.modules.user_management.domain (domain services and models)
# - app.modules.user_management.infrastructure (repository implementations)
# - CQRS command and query handlers
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation (API endpoints use application handlers)
# - Main application startup (application layer registration)
# - Dependency injection container (handler registration)

"""
User Management Application Layer

This module contains the application layer implementation following CQRS
(Command Query Responsibility Segregation) pattern for user management.

Application Components:
- Commands: User creation, updates, and deletion operations
- Queries: User and profile data retrieval operations  
- Handlers: Command and query execution logic
- DTOs: Data transfer objects for application layer communication

The application layer orchestrates domain services and coordinates
with infrastructure to fulfill business use cases.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Commands
    from app.modules.user_management.application.commands.create_user import CreateUserCommand
    from app.modules.user_management.application.commands.update_profile import UpdateProfileCommand
    from app.modules.user_management.application.commands.delete_user import DeleteUserCommand
    
    # Queries
    from app.modules.user_management.application.queries.get_user import GetUserQuery
    from app.modules.user_management.application.queries.get_profile import GetProfileQuery
    
    # Handlers
    from app.modules.user_management.application.handlers.command_handlers import (
        CreateUserCommandHandler,
        UpdateProfileCommandHandler,
        DeleteUserCommandHandler,
    )
    from app.modules.user_management.application.handlers.query_handlers import (
        GetUserQueryHandler,
        GetProfileQueryHandler,
    )
    
    # DTOs
    from app.modules.user_management.application.dto.user_dto import (
        UserDTO,
        CreateUserDTO,
        UpdateUserDTO,
    )
    from app.modules.user_management.application.dto.profile_dto import (
        ProfileDTO,
        CreateProfileDTO,
        UpdateProfileDTO,
    )

__all__ = [
    # Commands
    "CreateUserCommand",
    "UpdateProfileCommand", 
    "DeleteUserCommand",
    
    # Queries
    "GetUserQuery",
    "GetProfileQuery",
    
    # Handlers
    "CreateUserCommandHandler",
    "UpdateProfileCommandHandler",
    "DeleteUserCommandHandler",
    "GetUserQueryHandler",
    "GetProfileQueryHandler",
    
    # DTOs
    "UserDTO",
    "CreateUserDTO",
    "UpdateUserDTO",
    "ProfileDTO",
    "CreateProfileDTO",
    "UpdateProfileDTO",
]


def configure_application_layer():
    """
    Configure application layer dependencies and handlers.
    
    This function should be called during application startup to register
    command and query handlers with the dependency injection container.
    """
    # This will be implemented when we set up the DI container
    pass