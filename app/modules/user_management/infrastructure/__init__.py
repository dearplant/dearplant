# 📄 File: app/modules/user_management/infrastructure/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file sets up the infrastructure layer for user management, which handles how our app
# actually stores and retrieves user data from the database and connects to external services.
#
# 🧪 Purpose (Technical Summary):
# Infrastructure layer initialization providing database implementations, external service
# integrations, and infrastructure dependency registration for the user management module.
#
# 🔗 Dependencies:
# - app.modules.user_management.domain.repositories (repository interfaces)
# - app.shared.infrastructure.database (database connection)
# - SQLAlchemy ORM models and implementations
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application (uses repository implementations)
# - app.modules.user_management.presentation (dependency injection)
# - Main application startup (infrastructure registration)

"""
User Management Infrastructure Layer

This module provides concrete implementations of domain repository interfaces,
database models, and external service integrations for user management.

Infrastructure Components:
- Database: SQLAlchemy models and repository implementations
- External: Supabase authentication and OAuth provider integrations
- Security: Authentication and authorization implementations
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.user_management.infrastructure.database.user_repository_impl import UserRepositoryImpl
    from app.modules.user_management.infrastructure.database.profile_repository_impl import ProfileRepositoryImpl
    from app.modules.user_management.infrastructure.external.supabase_auth import SupabaseAuthService
    from app.modules.user_management.infrastructure.external.oauth_providers import OAuthProviderManager

__all__ = [
    "UserRepositoryImpl",
    "ProfileRepositoryImpl", 
    "SupabaseAuthService",
    "OAuthProviderManager",
]


def configure_infrastructure_dependencies():
    """
    Configure infrastructure layer dependencies for dependency injection.
    
    This function should be called during application startup to register
    concrete implementations with the dependency injection container.
    """
    # This will be implemented when we set up the DI container
    pass