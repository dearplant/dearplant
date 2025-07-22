# 📄 File: app/modules/user_management/domain/repositories/__init__.py
# 🧭 Purpose (Layman Explanation): 
# Organizes the data access interfaces that define how to save, find, and manage user and profile information in the database
# 🧪 Purpose (Technical Summary): 
# Package initialization for repository interfaces following Repository pattern for data access abstraction and dependency inversion
# 🔗 Dependencies: 
# Repository interface classes, domain models, typing
# 🔄 Connected Modules / Calls From: 
# Domain services, infrastructure implementations, application layer

"""
User Management Domain Repositories

This package contains repository interfaces that define data access contracts
for user management entities:

Repository Interfaces:
- UserRepository: Data access interface for User entities
- ProfileRepository: Data access interface for Profile entities

Repository Pattern Benefits:
- Abstracts data access from business logic
- Enables dependency inversion (domain doesn't depend on infrastructure)
- Allows easy testing with mock implementations
- Supports multiple data storage backends
- Provides consistent data access patterns

Each repository interface:
- Defines CRUD operations for its entity
- Includes domain-specific query methods
- Returns domain entities (not database models)
- Uses async/await for non-blocking operations
- Follows consistent naming conventions

Implementation Note:
- These are interfaces/abstract classes only
- Concrete implementations are in infrastructure layer
- Domain services depend on these interfaces
- Infrastructure layer implements these interfaces
"""

# Import repository interfaces
from .user_repository import UserRepository
from .profile_repository import ProfileRepository

# Export all repository interfaces
__all__ = [
    "UserRepository",
    "ProfileRepository"
]