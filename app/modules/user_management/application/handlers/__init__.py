# 📄 File: app/modules/user_management/application/handlers/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes all the "action processors" for user management, which take commands
# and queries and actually execute them by coordinating with the database and business logic.
#
# 🧪 Purpose (Technical Summary):
# Handlers package initialization implementing CQRS handler pattern for user management
# operations, providing command and query handlers that orchestrate domain services and repositories.
#
# 🔗 Dependencies:
# - app.modules.user_management.application.commands (command definitions)
# - app.modules.user_management.application.queries (query definitions)
# - app.modules.user_management.domain.services (domain business logic)
# - app.modules.user_management.infrastructure.database (repository implementations)
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api (API endpoints invoke handlers)
# - app.modules.user_management.application.__init__ (handler registration)
# - Dependency injection container (handler lifecycle management)

"""
User Management Handlers

This module contains all command and query handlers for user management operations
following the CQRS (Command Query Responsibility Segregation) pattern.

Handler Components:
- Command Handlers: Process write operations (create, update, delete)
- Query Handlers: Process read operations (get user, get profile)
- Handler Base Classes: Common functionality and error handling
- Handler Registration: Dependency injection setup

Command Handlers:
- CreateUserCommandHandler: User registration with profile creation
- UpdateProfileCommandHandler: Profile information updates
- DeleteUserCommandHandler: User account deletion with cleanup

Query Handlers:
- GetUserQueryHandler: User account data retrieval with security filtering
- GetProfileQueryHandler: Profile data retrieval with privacy controls

All handlers coordinate between domain services, repositories, and
infrastructure components to fulfill business use cases.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Command Handlers
    from app.modules.user_management.application.handlers.command_handlers import (
        CreateUserCommandHandler,
        UpdateProfileCommandHandler,
        DeleteUserCommandHandler,
    )
    
    # Query Handlers
    from app.modules.user_management.application.handlers.query_handlers import (
        GetUserQueryHandler,
        GetProfileQueryHandler,
    )

__all__ = [
    # Command Handlers
    "CreateUserCommandHandler",
    "UpdateProfileCommandHandler",
    "DeleteUserCommandHandler",
    
    # Query Handlers
    "GetUserQueryHandler",
    "GetProfileQueryHandler",
]


def configure_handler_dependencies():
    """
    Configure handler dependencies for dependency injection.
    
    This function should be called during application startup to register
    command and query handlers with the dependency injection container.
    
    Handlers require:
    - Domain services (UserService, AuthService, ProfileService)
    - Repository implementations (UserRepositoryImpl, ProfileRepositoryImpl)
    - Infrastructure services (SupabaseAuthService, OAuthProviderManager)
    - Event publishers and logging services
    """
    # This will be implemented when we set up the DI container
    pass