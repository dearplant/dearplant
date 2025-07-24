# 📄 File: app/modules/user_management/infrastructure/database/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes the database-related components for user management, making it easy
# to access user data storage functionality and database table definitions.
#
# 🧪 Purpose (Technical Summary):
# Database layer organization for user management, providing access to SQLAlchemy models,
# repository implementations, and database-specific utilities for user data persistence.
#
# 🔗 Dependencies:
# - SQLAlchemy ORM models and sessions
# - app.modules.user_management.domain.repositories (interface definitions)
# - app.shared.infrastructure.database (shared database utilities)
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.infrastructure.__init__ (imports models and repositories)
# - app.modules.user_management.application (uses repository implementations)
# - Database migration scripts (imports models for schema generation)

"""
User Management Database Layer

This module contains SQLAlchemy models and repository implementations
for persisting user management domain entities.

Database Components:
- Models: SQLAlchemy ORM models for users, profiles, and subscriptions
- Repositories: Concrete implementations of domain repository interfaces
- Utilities: Database-specific helper functions and configurations
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.user_management.infrastructure.database.models import (
        UserModel,
        ProfileModel,
        SubscriptionModel,
    )
    from app.modules.user_management.infrastructure.database.user_repository_impl import UserRepositoryImpl
    from app.modules.user_management.infrastructure.database.profile_repository_impl import ProfileRepositoryImpl
    from app.modules.user_management.infrastructure.database.subscription_repository_impl import SubscriptionRepositoryImpl


__all__ = [
    "UserModel",
    "ProfileModel", 
    "SubscriptionModel",
    "UserRepositoryImpl",
    "ProfileRepositoryImpl",
    "SubscriptionRepositoryImpl"
]