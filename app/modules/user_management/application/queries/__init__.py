# 📄 File: app/modules/user_management/application/queries/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes all the "information requests" for user management, like getting user details,
# profile information, or checking account status - basically all the ways to READ data from our app.
#
# 🧪 Purpose (Technical Summary):
# Queries package initialization implementing CQRS query pattern for user management
# read operations, providing query definitions for user and profile data retrieval.
#
# 🔗 Dependencies:
# - Pydantic models for query validation and response formatting
# - app.modules.user_management.domain.models (domain entities for response mapping)
# - Query handler interfaces and implementations
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.query_handlers (execute queries)
# - app.modules.user_management.presentation.api (API endpoints create queries)
# - Application layer initialization (query registration)

"""
User Management Queries

This module contains all query definitions for user management operations
following the CQRS (Command Query Responsibility Segregation) pattern.

Queries represent read operations and data retrieval use cases:
- GetUserQuery: User account information retrieval
- GetProfileQuery: Profile information and preferences retrieval
- Additional queries for user searches and filtering

All queries are immutable data structures that encapsulate
the parameters needed to retrieve specific data sets.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.user_management.application.queries.get_user import GetUserQuery
    from app.modules.user_management.application.queries.get_profile import GetProfileQuery

__all__ = [
    "GetUserQuery",
    "GetProfileQuery",
]