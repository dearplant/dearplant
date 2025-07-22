# 📄 File: app/modules/user_management/domain/events/handlers.py
# 🧭 Purpose (Layman Explanation): 
# Handles what happens automatically when user events occur - like sending welcome emails when someone registers or updating analytics when users login
# 🧪 Purpose (Technical Summary): 
# Event handlers implementing side effects and cross-module communication for user domain events following event-driven architecture patterns
# 🔗 Dependencies: 
# Domain events, app.shared.events.handlers, typing, logging
# 🔄 Connected Modules / Calls From: 
# Event publishers, notification system, analytics module, profile management

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from app.shared.events.base import DomainEvent
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

logger = logging.getLogger(__name__)


class UserEventHandler(ABC):
    """
    Abstract base class for user event handlers.
    Provides common functionality for processing user domain events.
    """
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a domain event.
        
        Args:
            event: Domain event to process
        """
        pass
    
    def log_event_processing(self, event: DomainEvent, status: str = "processing") -> None:
        """
        Log event processing for monitoring and debugging.
        
        Args:
            event: Domain event being processed
            status: Processing status (processing/completed/failed)
        """
        logger.info(
            f"Event {status}: {event.event_type}",
            extra={
                "event_type": event.event_type,
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "status": status
            }
        )


# User Creation Event Handlers

async def handle_user_created(event: UserCreated) -> None:
    """
    Handle UserCreated event with multiple side effects.
    
    Triggers:
    - Welcome email sending
    - Profile initialization
    - Analytics tracking
    - Onboarding flow start
    
    Args:
        event: UserCreated event
    """
    logger.info(f"Processing user creation for user_id: {event.user_id}")
    
    try:
        # 1. Send welcome email
        await _send_welcome_email(event)
        
        # 2. Initialize user profile if not exists
        await _initialize_user_profile(event)
        
        # 3. Track registration analytics
        await _track_user_registration(event)
        
        # 4. Start onboarding flow
        await _start_onboarding_flow(event)
        
        # 5. Create initial plant library recommendations
        await _create_plant_recommendations(event)
        
        logger.info(f"Successfully processed user creation for user_id: {event.user_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to process user creation for user_id: {event.user_id}",
            exc_info=True,
            extra={"user_id": event.user_id, "error": str(e)}
        )
        # Re-raise to trigger retry mechanism
        raise


async def handle_user_email_verified(event: UserEmailVerified) -> None:
    """
    Handle UserEmailVerified event.
    
    Triggers:
    - Account activation
    - Welcome sequence completion
    - Feature access enablement
    - Analytics tracking
    
    Args:
        event: UserEmailVerified event
    """
    logger.info(f"Processing email verification for user_id: {event.user_id}")
    
    try:
        # 1. Activate user account fully
        await _activate_user_account(event)
        
        # 2. Send welcome sequence completion email
        await _send_verification_confirmation(event)
        
        # 3. Enable full feature access
        await _enable_verified_user_features(event)
        
        # 4. Track verification analytics
        await _track_email_verification(event)
        
        # 5. Trigger any waiting background processes
        await _process_pending_user_actions(event)
        
        logger.info(f"Successfully processed email verification for user_id: {event.user_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to process email verification for user_id: {event.user_id}",
            exc_info=True,
            extra={"user_id": event.user_id, "error": str(e)}
        )
        raise


async def handle_user_subscription_changed(event: UserSubscriptionChanged) -> None:
    """
    Handle UserSubscriptionChanged event.
    
    Triggers:
    - Feature access updates
    - Billing notifications
    - Analytics tracking
    - Premium feature enablement/disablement
    
    Args:
        event: UserSubscriptionChanged event
    """
    logger.info(f"Processing subscription change for user_id: {event.user_id}")
    
    try:
        # 1. Update feature access permissions
        await _update_feature_access(event)
        
        # 2. Send subscription change notification
        await _send_subscription_notification(event)
        
        # 3. Track subscription analytics
        await _track_subscription_change(event)
        
        # 4. Update user role if needed
        await _update_user_role(event)
        
        # 5. Process premium/free specific actions
        if _is_upgrade_to_premium(event):
            await _handle_premium_upgrade(event)
        elif _is_downgrade_to_free(event):
            await _handle_premium_downgrade(event)
        
        logger.info(f"Successfully processed subscription change for user_id: {event.user_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to process subscription change for user_id: {event.user_id}",
            exc_info=True,
            extra={"user_id": event.user_id, "error": str(e)}
        )
        raise


async def handle_user_login_events(event: UserLoginSuccessful | UserLoginFailed) -> None:
    """
    Handle user login events (both successful and failed).
    
    Args:
        event: UserLoginSuccessful or UserLoginFailed event
    """
    if isinstance(event, UserLoginSuccessful):
        await _handle_successful_login(event)
    elif isinstance(event, UserLoginFailed):
        await _handle_failed_login(event)


# Security Event Handlers

async def handle_user_account_locked(event: UserAccountLocked) -> None:
    """
    Handle UserAccountLocked event.
    
    Triggers:
    - Security notification email
    - Security team alert
    - Account unlock procedure initiation
    
    Args:
        event: UserAccountLocked event
    """
    logger.warning(f"Processing account lock for user_id: {event.user_id}")
    
    try:
        # 1. Send security notification to user
        await _send_account_locked_notification(event)
        
        # 2. Alert security team if suspicious
        await _alert_security_team(event)
        
        # 3. Track security analytics
        await _track_security_event(event)
        
        # 4. Initiate unlock procedure if appropriate
        if event.lock_reason == "failed_logins":
            await _initiate_account_unlock_procedure(event)
        
        logger.warning(f"Successfully processed account lock for user_id: {event.user_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to process account lock for user_id: {event.user_id}",
            exc_info=True,
            extra={"user_id": event.user_id, "error": str(e)}
        )
        raise


# Profile Event Handlers

async def handle_user_profile_updated(event: UserProfileUpdated) -> None:
    """
    Handle UserProfileUpdated event.
    
    Triggers:
    - Profile sync across services
    - Location-based feature updates
    - Social features updates
    
    Args:
        event: UserProfileUpdated event
    """
    logger.info(f"Processing profile update for user_id: {event.user_id}")
    
    try:
        # 1. Sync profile across services
        await _sync_profile_across_services(event)
        
        # 2. Update location-based features if location changed
        if event.location_changed:
            await _update_location_based_features(event)
        
        # 3. Update privacy settings if changed
        if event.privacy_changes:
            await _process_privacy_changes(event)
        
        # 4. Track profile analytics
        await _track_profile_update(event)
        
        logger.info(f"Successfully processed profile update for user_id: {event.user_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to process profile update for user_id: {event.user_id}",
            exc_info=True,
            extra={"user_id": event.user_id, "error": str(e)}
        )
        raise


# Helper Functions for Event Processing

async def _send_welcome_email(event: UserCreated) -> None:
    """Send welcome email to new user."""
    # TODO: Implement email sending via notification service
    logger.info(f"Sending welcome email to {event.email}")


async def _initialize_user_profile(event: UserCreated) -> None:
    """Initialize user profile with defaults."""
    # TODO: Connect to profile service to create initial profile
    logger.info(f"Initializing profile for user_id: {event.user_id}")


async def _track_user_registration(event: UserCreated) -> None:
    """Track user registration in analytics."""
    # TODO: Connect to analytics service
    logger.info(f"Tracking registration analytics for user_id: {event.user_id}")


async def _start_onboarding_flow(event: UserCreated) -> None:
    """Start user onboarding process."""
    # TODO: Connect to onboarding service
    logger.info(f"Starting onboarding for user_id: {event.user_id}")


async def _create_plant_recommendations(event: UserCreated) -> None:
    """Create initial plant recommendations for new user."""
    # TODO: Connect to plant recommendation service
    logger.info(f"Creating plant recommendations for user_id: {event.user_id}")


async def _activate_user_account(event: UserEmailVerified) -> None:
    """Fully activate user account after email verification."""
    # TODO: Connect to user service to update account status
    logger.info(f"Activating account for user_id: {event.user_id}")


async def _send_verification_confirmation(event: UserEmailVerified) -> None:
    """Send email verification confirmation."""
    # TODO: Connect to notification service
    logger.info(f"Sending verification confirmation to user_id: {event.user_id}")


async def _enable_verified_user_features(event: UserEmailVerified) -> None:
    """Enable features available only to verified users."""
    # TODO: Connect to feature access service
    logger.info(f"Enabling verified user features for user_id: {event.user_id}")


async def _track_email_verification(event: UserEmailVerified) -> None:
    """Track email verification in analytics."""
    # TODO: Connect to analytics service
    logger.info(f"Tracking email verification for user_id: {event.user_id}")


async def _process_pending_user_actions(event: UserEmailVerified) -> None:
    """Process any actions that were waiting for email verification."""
    # TODO: Process pending actions queue
    logger.info(f"Processing pending actions for user_id: {event.user_id}")


async def _update_feature_access(event: UserSubscriptionChanged) -> None:
    """Update user's feature access based on subscription change."""
    # TODO: Connect to feature access control service
    logger.info(f"Updating feature access for user_id: {event.user_id}")


async def _send_subscription_notification(event: UserSubscriptionChanged) -> None:
    """Send subscription change notification to user."""
    # TODO: Connect to notification service
    logger.info(f"Sending subscription notification to user_id: {event.user_id}")


async def _track_subscription_change(event: UserSubscriptionChanged) -> None:
    """Track subscription change in analytics."""
    # TODO: Connect to analytics service
    logger.info(f"Tracking subscription change for user_id: {event.user_id}")


async def _update_user_role(event: UserSubscriptionChanged) -> None:
    """Update user role based on subscription."""
    # TODO: Connect to user service to update role
    logger.info(f"Updating user role for user_id: {event.user_id}")


async def _handle_premium_upgrade(event: UserSubscriptionChanged) -> None:
    """Handle premium upgrade specific actions."""
    # TODO: Enable premium features, send upgrade confirmation
    logger.info(f"Handling premium upgrade for user_id: {event.user_id}")


async def _handle_premium_downgrade(event: UserSubscriptionChanged) -> None:
    """Handle premium downgrade specific actions."""
    # TODO: Disable premium features, send downgrade notification
    logger.info(f"Handling premium downgrade for user_id: {event.user_id}")


async def _handle_successful_login(event: UserLoginSuccessful) -> None:
    """Handle successful login event."""
    # TODO: Track login analytics, update last login time
    logger.info(f"Handling successful login for user_id: {event.user_id}")


async def _handle_failed_login(event: UserLoginFailed) -> None:
    """Handle failed login event."""
    # TODO: Track security analytics, check for brute force
    logger.info(f"Handling failed login for email: {event.email}")


async def _send_account_locked_notification(event: UserAccountLocked) -> None:
    """Send account locked notification to user."""
    # TODO: Connect to notification service
    logger.info(f"Sending account locked notification to user_id: {event.user_id}")


async def _alert_security_team(event: UserAccountLocked) -> None:
    """Alert security team about account lock."""
    # TODO: Connect to security monitoring service
    if event.lock_reason == "suspicious_activity":
        logger.warning(f"Alerting security team about user_id: {event.user_id}")


async def _track_security_event(event: UserAccountLocked) -> None:
    """Track security event in analytics."""
    # TODO: Connect to security analytics
    logger.info(f"Tracking security event for user_id: {event.user_id}")


async def _initiate_account_unlock_procedure(event: UserAccountLocked) -> None:
    """Initiate account unlock procedure."""
    # TODO: Send unlock instructions or auto-unlock after timeout
    logger.info(f"Initiating unlock procedure for user_id: {event.user_id}")


async def _sync_profile_across_services(event: UserProfileUpdated) -> None:
    """Sync profile updates across all services."""
    # TODO: Update profile cache, sync with other modules
    logger.info(f"Syncing profile across services for user_id: {event.user_id}")


async def _update_location_based_features(event: UserProfileUpdated) -> None:
    """Update location-based features when location changes."""
    # TODO: Update weather data, local plant recommendations
    logger.info(f"Updating location-based features for user_id: {event.user_id}")


async def _process_privacy_changes(event: UserProfileUpdated) -> None:
    """Process privacy setting changes."""
    # TODO: Update data visibility, sync with community features
    logger.info(f"Processing privacy changes for user_id: {event.user_id}")


async def _track_profile_update(event: UserProfileUpdated) -> None:
    """Track profile update in analytics."""
    # TODO: Connect to analytics service
    logger.info(f"Tracking profile update for user_id: {event.user_id}")


# Utility Functions

def _is_upgrade_to_premium(event: UserSubscriptionChanged) -> bool:
    """Check if subscription change is an upgrade to premium."""
    return (
        event.previous_tier == "free" and 
        event.new_tier in ["premium_monthly", "premium_yearly"]
    )


def _is_downgrade_to_free(event: UserSubscriptionChanged) -> bool:
    """Check if subscription change is a downgrade to free."""
    return (
        event.previous_tier in ["premium_monthly", "premium_yearly"] and
        event.new_tier == "free"
    )


# Event Handler Registry
EVENT_HANDLERS = {
    "user.created": handle_user_created,
    "user.email_verified": handle_user_email_verified,
    "user.subscription_changed": handle_user_subscription_changed,
    "user.login_successful": handle_user_login_events,
    "user.login_failed": handle_user_login_events,
    "user.account_locked": handle_user_account_locked,
    "user.profile_updated": handle_user_profile_updated,
}


async def get_event_handler(event_type: str):
    """
    Get event handler for specific event type.
    
    Args:
        event_type: Type of event to handle
        
    Returns:
        Event handler function or None if not found
    """
    return EVENT_HANDLERS.get(event_type)