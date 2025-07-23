# 📄 File: app/modules/user_management/domain/__init__.py
# 🧭 Purpose (Layman Explanation): 
# Organizes the core business rules and logic for user accounts - like what makes a valid user, how passwords work, and user roles
# 🧪 Purpose (Technical Summary): 
# Domain layer initialization containing business entities, domain services, repositories interfaces, and domain events for user management
# 🔗 Dependencies: 
# Domain models, services, repositories, events from subpackages
# 🔄 Connected Modules / Calls From: 
# Application layer, Infrastructure layer, Presentation layer

"""
User Management Domain Layer

This package contains the core business logic and entities for user management:

Domain Models:
- User: Core user entity with authentication and profile data
- Profile: Extended user profile information and preferences  
- Subscription: User subscription and billing information

Domain Services:
- UserService: Core user business operations
- AuthService: Authentication business logic
- ProfileService: Profile management operations

Repository Interfaces:
- UserRepository: User data access interface
- ProfileRepository: Profile data access interface

Domain Events:
- UserEvents: User lifecycle events (created, updated, deleted)
- Event Handlers: Domain event processing

Business Rules Enforced:
- Email uniqueness and validation
- Password complexity requirements
- Account status management
- Subscription tier rules
- Profile data validation
- Authentication security rules
"""

# Re-export domain entities for easy access
from .models.user import User, UserRole, UserStatus, SubscriptionTier
from .models.profile import Profile, ProfileVisibility
from .models.subscription import Subscription, SubscriptionStatus, PlanType

# Re-export domain services interfaces
from .services.user_service import UserService
from .services.auth_service import AuthService  
from .services.profile_service import ProfileService

# Re-export repository interfaces
from .repositories.user_repository import UserRepository
from .repositories.profile_repository import ProfileRepository

# Re-export domain events
from .events.user_events import (
    UserCreated,
    UserUpdated, 
    UserDeleted,
    UserEmailVerified,
    UserPasswordChanged,
    UserSubscriptionChanged
) 
__all__ = [
    # Domain Models
    "User",
    "UserRole", 
    "UserStatus",
    "SubscriptionTier",
    "Profile",
    "ProfileVisibility",
    "Subscription",
    "SubscriptionStatus",
    "PlanType",
    
    # Domain Services
    "UserService",
    "AuthService",
    "ProfileService",
    
    # Repository Interfaces  
    "UserRepository",
    "ProfileRepository",
    
    # Domain Events
    "UserCreated",
    "UserUpdated",
    "UserDeleted", 
    "UserEmailVerified",
    "UserPasswordChanged",
    "UserSubscriptionChanged"
]