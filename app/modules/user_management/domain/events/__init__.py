# 📄 File: app/modules/user_management/domain/events/__init__.py
# 🧭 Purpose (Layman Explanation): 
# Organizes events that happen when users do things like register, login, or change their profile - so other parts of the app can react accordingly
# 🧪 Purpose (Technical Summary): 
# Package initialization for domain events implementing event-driven architecture for user lifecycle management and cross-module communication
# 🔗 Dependencies: 
# Domain event classes, event handlers, app.shared.events
# 🔄 Connected Modules / Calls From: 
# Domain services, application handlers, infrastructure event publishers, notification system

"""
User Management Domain Events

This package contains domain events for user lifecycle management:

Domain Events:
- UserCreated: Fired when a new user registers
- UserUpdated: Fired when user information changes
- UserDeleted: Fired when user account is deleted
- UserEmailVerified: Fired when user verifies their email
- UserPasswordChanged: Fired when user changes password
- UserSubscriptionChanged: Fired when subscription status changes
- UserProfileUpdated: Fired when profile information changes
- UserLoginSuccessful: Fired on successful login
- UserLoginFailed: Fired on failed login attempt

Event Handlers:
- User event processing and side effects
- Cross-module communication
- Notification triggering
- Analytics tracking

Events follow domain-driven design principles:
- Events are immutable
- Events contain all necessary data
- Events are published after domain state changes
- Events enable loose coupling between modules
"""

# Import domain events
from .user_events import (
    UserCreated,
    UserUpdated,
    UserDeleted,
    UserEmailVerified,
    UserPasswordChanged,
    UserSubscriptionChanged,
    UserProfileUpdated,
    UserLoginSuccessful,
    UserLoginFailed,
    UserAccountLocked,
    UserAccountUnlocked
)

# Import event handlers
from .handlers import (
    UserEventHandler,
    handle_user_created,
    handle_user_email_verified,
    handle_user_subscription_changed,
    handle_user_login_events
)

# Export all domain events and handlers
__all__ = [
    # Domain Events
    "UserCreated",
    "UserUpdated", 
    "UserDeleted",
    "UserEmailVerified",
    "UserPasswordChanged",
    "UserSubscriptionChanged",
    "UserProfileUpdated",
    "UserLoginSuccessful",
    "UserLoginFailed",
    "UserAccountLocked",
    "UserAccountUnlocked",
    
    # Event Handlers
    "UserEventHandler",
    "handle_user_created",
    "handle_user_email_verified", 
    "handle_user_subscription_changed",
    "handle_user_login_events"
]