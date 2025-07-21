# 📄 File: app/shared/events/__init__.py

# 🧭 Purpose (Layman Explanation):
# This file sets up an event system that lets different parts of the app communicate with each other,
# like sending notifications when a plant is watered or alerting when a plant needs care.

# 🧪 Purpose (Technical Summary):
# Initializes the domain events system for decoupled communication between modules using
# the publisher-subscriber pattern with async support and event persistence.

# 🔗 Dependencies:
# - base: Base event classes and interfaces
# - handlers: Event handler registration and execution
# - publisher: Event publishing and distribution system

# 🔄 Connected Modules / Calls From:
# Used by: All domain modules for publishing events (user actions, plant care, health changes),
# Background jobs for event processing, Analytics for event tracking

"""
Domain Events System

This package implements a comprehensive event-driven architecture for the Plant Care Application.
It enables loose coupling between modules through domain events.

Key Features:
- Domain event publishing and subscription
- Async event handling
- Event persistence and replay
- Event-driven analytics
- Cross-module communication
- Background event processing

Event Categories:
- User events (registration, login, profile changes)
- Plant events (creation, updates, care actions)
- Care events (scheduled tasks, completions, reminders)
- Health events (status changes, diagnoses, treatments)
- Growth events (measurements, milestones, photos)
- Community events (posts, interactions, follows)
- System events (startup, shutdown, errors)
"""

from typing import Dict, List, Type, Any, Optional
import asyncio
import logging
from datetime import datetime
from enum import Enum

from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

# Event categories for organization
class EventCategory(Enum):
    """Standard event categories."""
    USER = "user"
    PLANT = "plant"
    CARE = "care"
    HEALTH = "health"
    GROWTH = "growth"
    COMMUNITY = "community"
    ANALYTICS = "analytics"
    NOTIFICATION = "notification"
    SYSTEM = "system"
    INTEGRATION = "integration"


class EventPriority(Enum):
    """Event processing priorities."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# Global event configuration
EVENT_CONFIG = {
    'enable_persistence': True,
    'enable_replay': True,
    'max_retry_attempts': 3,
    'retry_delay_seconds': 1.0,
    'batch_size': 100,
    'processing_timeout': 30.0
}

# Event type registry
_event_types_registry: Dict[str, Type] = {}
_event_handlers_registry: Dict[str, List[callable]] = {}
_event_publisher = None

# Event statistics
_event_stats = {
    'published': 0,
    'processed': 0,
    'failed': 0,
    'retried': 0
}


class EventError(Exception):
    """Base exception for event system errors."""
    pass


class EventPublishError(EventError):
    """Exception for event publishing errors."""
    pass


class EventHandlingError(EventError):
    """Exception for event handling errors."""
    pass


def register_event_type(event_type: str, event_class: Type):
    """
    Register an event type with its class.
    
    Args:
        event_type: Event type identifier
        event_class: Event class
    """
    _event_types_registry[event_type] = event_class
    logger.info(f"Registered event type: {event_type}")


def register_event_handler(event_type: str, handler: callable):
    """
    Register an event handler for specific event type.
    
    Args:
        event_type: Event type to handle
        handler: Handler function (async or sync)
    """
    if event_type not in _event_handlers_registry:
        _event_handlers_registry[event_type] = []
    
    _event_handlers_registry[event_type].append(handler)
    logger.info(f"Registered handler for event type: {event_type}")


def get_registered_event_types() -> List[str]:
    """Get list of registered event types."""
    return list(_event_types_registry.keys())


def get_event_handlers(event_type: str) -> List[callable]:
    """Get handlers for specific event type."""
    return _event_handlers_registry.get(event_type, [])


def get_event_stats() -> Dict[str, Any]:
    """Get event system statistics."""
    return {
        **_event_stats,
        'registered_types': len(_event_types_registry),
        'registered_handlers': sum(len(handlers) for handlers in _event_handlers_registry.values()),
        'config': EVENT_CONFIG
    }


async def initialize_event_system():
    """Initialize the event system."""
    try:
        global _event_publisher
        
        # Import here to avoid circular imports
        from .publisher import EventPublisher
        
        _event_publisher = EventPublisher()
        await _event_publisher.initialize()
        
        logger.info("Event system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize event system: {e}")
        raise EventError(f"Event system initialization failed: {e}")


async def cleanup_event_system():
    """Cleanup event system resources."""
    try:
        global _event_publisher
        
        if _event_publisher:
            await _event_publisher.cleanup()
            _event_publisher = None
        
        # Clear registries
        _event_types_registry.clear()
        _event_handlers_registry.clear()
        
        logger.info("Event system cleaned up")
        
    except Exception as e:
        logger.error(f"Failed to cleanup event system: {e}")


def get_event_publisher():
    """Get the global event publisher instance."""
    return _event_publisher


# Event decorators for easy handler registration
def event_handler(event_type: str):
    """
    Decorator to register function as event handler.
    
    Args:
        event_type: Event type to handle
    
    Returns:
        Decorated function
    """
    def decorator(func):
        register_event_handler(event_type, func)
        return func
    
    return decorator


def events_handler(*event_types: str):
    """
    Decorator to register function as handler for multiple event types.
    
    Args:
        *event_types: Event types to handle
    
    Returns:
        Decorated function
    """
    def decorator(func):
        for event_type in event_types:
            register_event_handler(event_type, func)
        return func
    
    return decorator


# Convenience functions for common event operations
async def publish_event(event_type: str, data: Dict[str, Any], **kwargs):
    """
    Publish an event with data.
    
    Args:
        event_type: Type of event
        data: Event data
        **kwargs: Additional event properties
    """
    if not _event_publisher:
        raise EventError("Event system not initialized")
    
    await _event_publisher.publish(event_type, data, **kwargs)
    _event_stats['published'] += 1


async def publish_user_event(event_name: str, user_id: str, data: Dict[str, Any] = None):
    """Publish user-related event."""
    event_data = {
        'user_id': user_id,
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('user.event', event_data, category=EventCategory.USER)


async def publish_plant_event(event_name: str, plant_id: str, user_id: str, data: Dict[str, Any] = None):
    """Publish plant-related event."""
    event_data = {
        'plant_id': plant_id,
        'user_id': user_id,
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('plant.event', event_data, category=EventCategory.PLANT)


async def publish_care_event(event_name: str, plant_id: str, user_id: str, data: Dict[str, Any] = None):
    """Publish care-related event."""
    event_data = {
        'plant_id': plant_id,
        'user_id': user_id,
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('care.event', event_data, category=EventCategory.CARE)


async def publish_health_event(event_name: str, plant_id: str, user_id: str, data: Dict[str, Any] = None):
    """Publish health-related event."""
    event_data = {
        'plant_id': plant_id,
        'user_id': user_id,
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('health.event', event_data, category=EventCategory.HEALTH)


async def publish_growth_event(event_name: str, plant_id: str, user_id: str, data: Dict[str, Any] = None):
    """Publish growth-related event."""
    event_data = {
        'plant_id': plant_id,
        'user_id': user_id,
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('growth.event', event_data, category=EventCategory.GROWTH)


async def publish_community_event(event_name: str, user_id: str, data: Dict[str, Any] = None):
    """Publish community-related event."""
    event_data = {
        'user_id': user_id,
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('community.event', event_data, category=EventCategory.COMMUNITY)


async def publish_system_event(event_name: str, data: Dict[str, Any] = None):
    """Publish system-related event."""
    event_data = {
        'event_name': event_name,
        **(data or {})
    }
    await publish_event('system.event', event_data, category=EventCategory.SYSTEM)


# Standard event type definitions
STANDARD_EVENT_TYPES = {
    # User events
    'user.registered': 'User registration completed',
    'user.login': 'User logged in',
    'user.logout': 'User logged out',
    'user.profile_updated': 'User profile updated',
    'user.subscription_changed': 'User subscription changed',
    'user.deleted': 'User account deleted',
    
    # Plant events
    'plant.created': 'Plant added to collection',
    'plant.updated': 'Plant information updated',
    'plant.deleted': 'Plant removed from collection',
    'plant.identified': 'Plant species identified',
    'plant.photo_added': 'Plant photo uploaded',
    
    # Care events
    'care.task_created': 'Care task scheduled',
    'care.task_completed': 'Care task completed',
    'care.task_overdue': 'Care task overdue',
    'care.reminder_sent': 'Care reminder sent',
    'care.schedule_updated': 'Care schedule modified',
    
    # Health events
    'health.status_changed': 'Plant health status changed',
    'health.diagnosis_created': 'Health diagnosis performed',
    'health.treatment_started': 'Treatment plan initiated',
    'health.treatment_completed': 'Treatment completed',
    'health.alert_triggered': 'Health alert triggered',
    
    # Growth events
    'growth.measurement_recorded': 'Growth measurement added',
    'growth.milestone_achieved': 'Growth milestone reached',
    'growth.photo_added': 'Growth journal photo added',
    'growth.analysis_completed': 'Growth analysis performed',
    
    # Community events
    'community.post_created': 'Community post created',
    'community.post_liked': 'Post liked',
    'community.comment_added': 'Comment added to post',
    'community.user_followed': 'User followed',
    'community.expert_advice_requested': 'Expert advice requested',
    
    # Analytics events
    'analytics.user_action': 'User action tracked',
    'analytics.feature_used': 'Feature usage tracked',
    'analytics.error_occurred': 'Error tracked',
    'analytics.performance_measured': 'Performance metric recorded',
    
    # Notification events
    'notification.sent': 'Notification sent',
    'notification.delivered': 'Notification delivered',
    'notification.opened': 'Notification opened',
    'notification.failed': 'Notification failed',
    
    # System events
    'system.startup': 'System started',
    'system.shutdown': 'System shutdown',
    'system.health_check': 'Health check performed',
    'system.error': 'System error occurred',
    'system.maintenance_started': 'Maintenance mode started',
    'system.maintenance_ended': 'Maintenance mode ended'
}


def get_standard_event_types() -> Dict[str, str]:
    """Get dictionary of standard event types and descriptions."""
    return STANDARD_EVENT_TYPES.copy()


# Event middleware for common processing
class EventMiddleware:
    """Base class for event middleware."""
    
    async def before_publish(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process event data before publishing."""
        return data
    
    async def after_publish(self, event_type: str, data: Dict[str, Any], success: bool):
        """Process after event publishing."""
        pass
    
    async def before_handle(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process event data before handling."""
        return data
    
    async def after_handle(self, event_type: str, data: Dict[str, Any], success: bool):
        """Process after event handling."""
        pass


# Global middleware registry
_middleware_registry: List[EventMiddleware] = []


def register_middleware(middleware: EventMiddleware):
    """Register event middleware."""
    _middleware_registry.append(middleware)
    logger.info(f"Registered event middleware: {type(middleware).__name__}")


def get_middleware() -> List[EventMiddleware]:
    """Get registered middleware."""
    return _middleware_registry.copy()


# Export public interface
__all__ = [
    'EventCategory',
    'EventPriority',
    'EventError',
    'EventPublishError',
    'EventHandlingError',
    'register_event_type',
    'register_event_handler',
    'get_registered_event_types',
    'get_event_handlers',
    'get_event_stats',
    'initialize_event_system',
    'cleanup_event_system',
    'get_event_publisher',
    'event_handler',
    'events_handler',
    'publish_event',
    'publish_user_event',
    'publish_plant_event',
    'publish_care_event',
    'publish_health_event',
    'publish_growth_event',
    'publish_community_event',
    'publish_system_event',
    'get_standard_event_types',
    'EventMiddleware',
    'register_middleware',
    'get_middleware'
]  