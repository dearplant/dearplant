# 📄 File: app/modules/user_management/domain/events/user_events.py
# 🧭 Purpose (Layman Explanation): 
# Defines specific events that happen during user activities like registration, login, profile changes - so other parts of the app can respond automatically
# 🧪 Purpose (Technical Summary): 
# Domain events for user lifecycle management implementing event-driven architecture with immutable event data for cross-module communication
# 🔗 Dependencies: 
# pydantic, datetime, typing, app.shared.events.base
# 🔄 Connected Modules / Calls From: 
# Domain services, event handlers, notification system, analytics, community features

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.shared.events.base import DomainEvent


class UserCreated(DomainEvent):
    """
    Event fired when a new user is created.
    
    Triggers:
    - Welcome email sending
    - Profile initialization  
    - Analytics tracking
    - Onboarding flow start
    """
    event_type: str = "user.created"
    
    # User information
    user_id: str
    email: str
    display_name: Optional[str]
    provider: str  # email/google/apple
    registration_ip: Optional[str]
    
    # Subscription information
    subscription_tier: str
    trial_started: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.created",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "display_name": "John Doe",
                "provider": "email",
                "registration_ip": "192.168.1.1",
                "subscription_tier": "free",
                "trial_started": False,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserUpdated(DomainEvent):
    """
    Event fired when user information is updated.
    
    Triggers:
    - Profile sync across services
    - Cache invalidation
    - Analytics tracking
    """
    event_type: str = "user.updated"
    
    user_id: str
    updated_fields: Dict[str, Any]  # Field name -> new value
    previous_values: Dict[str, Any]  # Field name -> old value
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.updated",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "updated_fields": {"display_name": "Jane Doe", "language": "es"},
                "previous_values": {"display_name": "John Doe", "language": "en"},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserDeleted(DomainEvent):
    """
    Event fired when a user account is deleted.
    
    Triggers:
    - Data cleanup across modules
    - Plant collection archiving
    - Subscription cancellation
    - Analytics tracking
    """
    event_type: str = "user.deleted"
    
    user_id: str
    email: str
    deletion_reason: Optional[str]
    soft_delete: bool = True  # True for soft delete, False for hard delete
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.deleted",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "deletion_reason": "User requested account deletion",
                "soft_delete": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserEmailVerified(DomainEvent):
    """
    Event fired when user verifies their email address.
    
    Triggers:
    - Account activation
    - Welcome sequence completion
    - Feature access enablement
    - Analytics tracking
    """
    event_type: str = "user.email_verified"
    
    user_id: str
    email: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.email_verified",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "verified_at": "2024-01-15T10:30:00Z",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserPasswordChanged(DomainEvent):
    """
    Event fired when user changes their password.
    
    Triggers:
    - Security notification email
    - Session invalidation
    - Security audit logging
    - Analytics tracking
    """
    event_type: str = "user.password_changed"
    
    user_id: str
    email: str
    change_ip: Optional[str]
    reset_token_used: bool = False  # True if changed via reset token
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.password_changed",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "change_ip": "192.168.1.1",
                "reset_token_used": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserSubscriptionChanged(DomainEvent):
    """
    Event fired when user subscription status changes.
    
    Triggers:
    - Feature access updates
    - Billing notifications
    - Analytics tracking
    - Premium feature enablement/disablement
    """
    event_type: str = "user.subscription_changed"
    
    user_id: str
    previous_tier: str
    new_tier: str
    previous_status: str
    new_status: str
    change_reason: Optional[str]  # upgrade/downgrade/cancellation/payment_failed
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.subscription_changed",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "previous_tier": "free",
                "new_tier": "premium_monthly",
                "previous_status": "active",
                "new_status": "active",
                "change_reason": "upgrade",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserProfileUpdated(DomainEvent):
    """
    Event fired when user profile information is updated.
    
    Triggers:
    - Profile sync across services
    - Social features updates
    - Location-based feature updates
    - Analytics tracking
    """
    event_type: str = "user.profile_updated"
    
    user_id: str
    profile_id: str
    updated_fields: Dict[str, Any]
    privacy_changes: bool = False  # True if privacy settings changed
    location_changed: bool = False  # True if location changed (for weather updates)
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.profile_updated",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "profile_id": "456e7890-e89b-12d3-a456-426614174000",
                "updated_fields": {"bio": "Plant enthusiast", "location": "New York"},
                "privacy_changes": False,
                "location_changed": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserLoginSuccessful(DomainEvent):
    """
    Event fired when user successfully logs in.
    
    Triggers:
    - Login analytics tracking
    - Security monitoring
    - Session creation
    - Welcome back notifications
    """
    event_type: str = "user.login_successful"
    
    user_id: str
    email: str
    login_ip: Optional[str]
    user_agent: Optional[str]
    login_method: str  # email/google/apple
    session_id: Optional[str]
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.login_successful",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "login_ip": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "login_method": "email",
                "session_id": "sess_123456",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserLoginFailed(DomainEvent):
    """
    Event fired when user login attempt fails.
    
    Triggers:
    - Security monitoring
    - Brute force detection
    - Account lockout if needed
    - Security analytics
    """
    event_type: str = "user.login_failed"
    
    email: str
    user_id: Optional[str]  # May be None if email not found
    login_ip: Optional[str]
    user_agent: Optional[str]
    failure_reason: str  # invalid_email/invalid_password/account_locked/account_inactive
    attempt_count: int  # Current failed attempt count for this user
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.login_failed",
                "email": "user@example.com",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "login_ip": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "failure_reason": "invalid_password",
                "attempt_count": 2,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserAccountLocked(DomainEvent):
    """
    Event fired when user account is locked due to security concerns.
    
    Triggers:
    - Security notification email
    - Security team alert
    - Account unlock procedure initiation
    - Security analytics
    """
    event_type: str = "user.account_locked"
    
    user_id: str
    email: str
    lock_reason: str  # failed_logins/suspicious_activity/admin_action
    failed_attempts: int
    lock_ip: Optional[str]
    unlock_instructions_sent: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.account_locked",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "lock_reason": "failed_logins",
                "failed_attempts": 5,
                "lock_ip": "192.168.1.1",
                "unlock_instructions_sent": True,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserAccountUnlocked(DomainEvent):
    """
    Event fired when user account is unlocked.
    
    Triggers:
    - Account unlocked notification
    - Security log entry
    - Login attempt reset
    - Analytics tracking
    """
    event_type: str = "user.account_unlocked"
    
    user_id: str
    email: str
    unlock_method: str  # auto_timeout/admin_action/user_request/password_reset
    unlocked_by: Optional[str]  # admin_id if unlocked by admin
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "user.account_unlocked",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "unlock_method": "password_reset",
                "unlocked_by": None,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }