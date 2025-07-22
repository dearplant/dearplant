# 📄 File: app/modules/user_management/domain/models/__init__.py
# 🧭 Purpose (Layman Explanation): 
# Organizes the core user data models - like defining what information we store about users, their profiles, and subscriptions
# 🧪 Purpose (Technical Summary): 
# Package initialization for domain models containing User, Profile, and Subscription entities with their enums and validation rules
# 🔗 Dependencies: 
# Domain model classes, enums, pydantic base models
# 🔄 Connected Modules / Calls From: 
# Domain services, repositories, application layer, infrastructure layer

"""
User Management Domain Models

This package contains the core domain entities for user management:

Models:
- User: Core user entity with authentication data and basic profile info
- Profile: Extended user profile with preferences and social information  
- Subscription: User subscription and billing information

Each model follows domain-driven design principles:
- Rich domain models with business logic
- Validation rules enforced at domain level
- Immutable value objects where appropriate
- Domain events for state changes

Field specifications follow core doc requirements:
- UUID primary keys for all entities
- Timestamp fields with timezone support
- Email validation and uniqueness
- Password hashing with bcrypt
- Status and role enumerations
"""

# Import domain models
from .user import (
    User,
    UserRole,
    UserStatus,
    SubscriptionTier
)

from .profile import (
    Profile,
    ProfileVisibility,
    NotificationPreferences,
    PrivacySettings
)

from .subscription import (
    Subscription,
    SubscriptionStatus,
    PlanType,
    PaymentMethod
)

# Export all domain models and related types
__all__ = [
    # User entity and enums
    "User",
    "UserRole",
    "UserStatus", 
    "SubscriptionTier",
    
    # Profile entity and enums
    "Profile",
    "ProfileVisibility",
    "NotificationPreferences",
    "PrivacySettings",
    
    # Subscription entity and enums
    "Subscription",
    "SubscriptionStatus",
    "PlanType",
    "PaymentMethod"
]