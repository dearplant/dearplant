# 📄 File: app/shared/events/base.py

# 🧭 Purpose (Layman Explanation):
# This file defines the basic building blocks for events - like templates that define what information
# an event should contain when something important happens in the app.

# 🧪 Purpose (Technical Summary):
# Base event classes and interfaces for domain events, providing structure for event data,
# metadata, and processing requirements across the Plant Care Application.

# 🔗 Dependencies:
# - uuid: Event unique identifiers
# - datetime: Event timestamps
# - dataclasses: Event structure definitions
# - typing: Type annotations

# 🔄 Connected Modules / Calls From:
# Used by: All domain modules for creating specific event types, Event handlers for processing,
# Event publisher for distribution, Analytics for event tracking

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EventMetadata:
    """
    Metadata for domain events.
    
    Contains common information about event processing,
    routing, and tracking.
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"
    source: str = "plant-care-api"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Processing metadata
    priority: int = 2  # 1=low, 2=normal, 3=high, 4=critical
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    
    # Routing metadata
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    route_to: List[str] = field(default_factory=list)  # Specific handlers
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMetadata':
        """Create metadata from dictionary."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class DomainEvent(ABC):
    """
    Base class for all domain events.
    
    Provides common structure and functionality for events
    throughout the Plant Care Application.
    """
    
    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
        **kwargs
    ):
        """
        Initialize domain event.
        
        Args:
            event_type: Type identifier for the event
            data: Event payload data
            metadata: Event metadata
            **kwargs: Additional metadata fields
        """
        self.event_type = event_type
        self.data = data or {}
        
        # Create or update metadata
        if metadata is None:
            metadata = EventMetadata()
        
        # Update metadata with kwargs
        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        self.metadata = metadata
        
        # Validate event
        self._validate()
    
    def _validate(self):
        """Validate event structure and data."""
        if not self.event_type:
            raise ValueError("Event type is required")
        
        if not isinstance(self.data, dict):
            raise ValueError("Event data must be a dictionary")
        
        # Validate required fields based on event type
        self._validate_event_data()
    
    @abstractmethod
    def _validate_event_data(self):
        """Validate event-specific data. Override in subclasses."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            'event_type': self.event_type,
            'data': self.data,
            'metadata': self.metadata.to_dict()
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Create event from dictionary."""
        metadata_dict = data.get('metadata', {})
        metadata = EventMetadata.from_dict(metadata_dict)
        
        return cls(
            event_type=data['event_type'],
            data=data.get('data', {}),
            metadata=metadata
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DomainEvent':
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_tag(self, tag: str):
        """Add tag to event metadata."""
        if tag not in self.metadata.tags:
            self.metadata.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """Remove tag from event metadata."""
        if tag in self.metadata.tags:
            self.metadata.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if event has specific tag."""
        return tag in self.metadata.tags
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for event tracking."""
        self.metadata.correlation_id = correlation_id
    
    def set_causation_id(self, causation_id: str):
        """Set causation ID for event chaining."""
        self.metadata.causation_id = causation_id
    
    def set_user_context(self, user_id: str, session_id: str = None):
        """Set user context for the event."""
        self.metadata.user_id = user_id
        self.metadata.session_id = session_id
    
    def increment_retry(self):
        """Increment retry count."""
        self.metadata.retry_count += 1
    
    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return self.metadata.retry_count < self.metadata.max_retries
    
    def __str__(self) -> str:
        return f"{self.event_type}({self.metadata.event_id})"
    
    def __repr__(self) -> str:
        return f"DomainEvent(type='{self.event_type}', id='{self.metadata.event_id}')"


class UserEvent(DomainEvent):
    """Base class for user-related events."""
    
    def __init__(self, event_type: str, user_id: str, data: Dict[str, Any] = None, **kwargs):
        data = data or {}
        data['user_id'] = user_id
        
        kwargs.setdefault('category', 'user')
        kwargs.setdefault('user_id', user_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate user event data."""
        if 'user_id' not in self.data:
            raise ValueError("User events must contain user_id")
    
    @property
    def user_id(self) -> str:
        """Get user ID from event data."""
        return self.data['user_id']


class PlantEvent(DomainEvent):
    """Base class for plant-related events."""
    
    def __init__(
        self,
        event_type: str,
        plant_id: str,
        user_id: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data.update({
            'plant_id': plant_id,
            'user_id': user_id
        })
        
        kwargs.setdefault('category', 'plant')
        kwargs.setdefault('user_id', user_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate plant event data."""
        required_fields = ['plant_id', 'user_id']
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Plant events must contain {field}")
    
    @property
    def plant_id(self) -> str:
        """Get plant ID from event data."""
        return self.data['plant_id']
    
    @property
    def user_id(self) -> str:
        """Get user ID from event data."""
        return self.data['user_id']


class CareEvent(DomainEvent):
    """Base class for care-related events."""
    
    def __init__(
        self,
        event_type: str,
        plant_id: str,
        user_id: str,
        care_type: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data.update({
            'plant_id': plant_id,
            'user_id': user_id,
            'care_type': care_type
        })
        
        kwargs.setdefault('category', 'care')
        kwargs.setdefault('user_id', user_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate care event data."""
        required_fields = ['plant_id', 'user_id', 'care_type']
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Care events must contain {field}")
    
    @property
    def plant_id(self) -> str:
        """Get plant ID from event data."""
        return self.data['plant_id']
    
    @property
    def user_id(self) -> str:
        """Get user ID from event data."""
        return self.data['user_id']
    
    @property
    def care_type(self) -> str:
        """Get care type from event data."""
        return self.data['care_type']


class HealthEvent(DomainEvent):
    """Base class for health-related events."""
    
    def __init__(
        self,
        event_type: str,
        plant_id: str,
        user_id: str,
        health_status: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data.update({
            'plant_id': plant_id,
            'user_id': user_id,
            'health_status': health_status
        })
        
        kwargs.setdefault('category', 'health')
        kwargs.setdefault('user_id', user_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate health event data."""
        required_fields = ['plant_id', 'user_id', 'health_status']
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Health events must contain {field}")
    
    @property
    def plant_id(self) -> str:
        """Get plant ID from event data."""
        return self.data['plant_id']
    
    @property
    def user_id(self) -> str:
        """Get user ID from event data."""
        return self.data['user_id']
    
    @property
    def health_status(self) -> str:
        """Get health status from event data."""
        return self.data['health_status']


class GrowthEvent(DomainEvent):
    """Base class for growth-related events."""
    
    def __init__(
        self,
        event_type: str,
        plant_id: str,
        user_id: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data.update({
            'plant_id': plant_id,
            'user_id': user_id
        })
        
        kwargs.setdefault('category', 'growth')
        kwargs.setdefault('user_id', user_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate growth event data."""
        required_fields = ['plant_id', 'user_id']
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Growth events must contain {field}")
    
    @property
    def plant_id(self) -> str:
        """Get plant ID from event data."""
        return self.data['plant_id']
    
    @property
    def user_id(self) -> str:
        """Get user ID from event data."""
        return self.data['user_id']


class CommunityEvent(DomainEvent):
    """Base class for community-related events."""
    
    def __init__(
        self,
        event_type: str,
        user_id: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data['user_id'] = user_id
        
        kwargs.setdefault('category', 'community')
        kwargs.setdefault('user_id', user_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate community event data."""
        if 'user_id' not in self.data:
            raise ValueError("Community events must contain user_id")
    
    @property
    def user_id(self) -> str:
        """Get user ID from event data."""
        return self.data['user_id']


class SystemEvent(DomainEvent):
    """Base class for system-related events."""
    
    def __init__(self, event_type: str, data: Dict[str, Any] = None, **kwargs):
        kwargs.setdefault('category', 'system')
        super().__init__(event_type, data or {}, **kwargs)
    
    def _validate_event_data(self):
        """Validate system event data."""
        # System events have no required fields
        pass


class AnalyticsEvent(DomainEvent):
    """Base class for analytics-related events."""
    
    def __init__(
        self,
        event_type: str,
        action: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data['action'] = action
        
        kwargs.setdefault('category', 'analytics')
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate analytics event data."""
        if 'action' not in self.data:
            raise ValueError("Analytics events must contain action")
    
    @property
    def action(self) -> str:
        """Get action from event data."""
        return self.data['action']


class NotificationEvent(DomainEvent):
    """Base class for notification-related events."""
    
    def __init__(
        self,
        event_type: str,
        recipient_id: str,
        notification_type: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data.update({
            'recipient_id': recipient_id,
            'notification_type': notification_type
        })
        
        kwargs.setdefault('category', 'notification')
        kwargs.setdefault('user_id', recipient_id)
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate notification event data."""
        required_fields = ['recipient_id', 'notification_type']
        for field in required_fields:
            if field not in self.data:
                raise ValueError(f"Notification events must contain {field}")
    
    @property
    def recipient_id(self) -> str:
        """Get recipient ID from event data."""
        return self.data['recipient_id']
    
    @property
    def notification_type(self) -> str:
        """Get notification type from event data."""
        return self.data['notification_type']


class IntegrationEvent(DomainEvent):
    """Base class for integration-related events."""
    
    def __init__(
        self,
        event_type: str,
        integration_name: str,
        data: Dict[str, Any] = None,
        **kwargs
    ):
        data = data or {}
        data['integration_name'] = integration_name
        
        kwargs.setdefault('category', 'integration')
        
        super().__init__(event_type, data, **kwargs)
    
    def _validate_event_data(self):
        """Validate integration event data."""
        if 'integration_name' not in self.data:
            raise ValueError("Integration events must contain integration_name")
    
    @property
    def integration_name(self) -> str:
        """Get integration name from event data."""
        return self.data['integration_name']


# Event handler interface
class EventHandler(ABC):
    """
    Abstract base class for event handlers.
    
    Event handlers process domain events and perform
    side effects or trigger additional actions.
    """
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> bool:
        """
        Handle a domain event.
        
        Args:
            event: Domain event to handle
        
        Returns:
            True if handled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """
        Check if handler can process event type.
        
        Args:
            event_type: Event type to check
        
        Returns:
            True if handler can process event type
        """
        pass
    
    def get_handler_name(self) -> str:
        """Get handler name for logging and debugging."""
        return self.__class__.__name__


# Event stream interface
class EventStream(ABC):
    """
    Abstract interface for event streams.
    
    Event streams store and retrieve events for
    persistence, replay, and auditing.
    """
    
    @abstractmethod
    async def append(self, event: DomainEvent) -> bool:
        """
        Append event to stream.
        
        Args:
            event: Event to append
        
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def read(
        self,
        stream_id: str,
        from_version: int = 0,
        max_count: int = 100
    ) -> List[DomainEvent]:
        """
        Read events from stream.
        
        Args:
            stream_id: Stream identifier
            from_version: Starting version number
            max_count: Maximum events to read
        
        Returns:
            List of events
        """
        pass
    
    @abstractmethod
    async def read_by_type(
        self,
        event_type: str,
        from_timestamp: datetime = None,
        to_timestamp: datetime = None,
        max_count: int = 100
    ) -> List[DomainEvent]:
        """
        Read events by type and time range.
        
        Args:
            event_type: Event type to filter
            from_timestamp: Start time filter
            to_timestamp: End time filter
            max_count: Maximum events to read
        
        Returns:
            List of events
        """
        pass


# Factory functions for creating events
def create_user_event(event_type: str, user_id: str, **kwargs) -> UserEvent:
    """Create a user event with standard structure."""
    return UserEvent(event_type, user_id, **kwargs)


def create_plant_event(event_type: str, plant_id: str, user_id: str, **kwargs) -> PlantEvent:
    """Create a plant event with standard structure."""
    return PlantEvent(event_type, plant_id, user_id, **kwargs)


def create_care_event(
    event_type: str,
    plant_id: str,
    user_id: str,
    care_type: str,
    **kwargs
) -> CareEvent:
    """Create a care event with standard structure."""
    return CareEvent(event_type, plant_id, user_id, care_type, **kwargs)


def create_health_event(
    event_type: str,
    plant_id: str,
    user_id: str,
    health_status: str,
    **kwargs
) -> HealthEvent:
    """Create a health event with standard structure."""
    return HealthEvent(event_type, plant_id, user_id, health_status, **kwargs)


def create_growth_event(
    event_type: str,
    plant_id: str,
    user_id: str,
    **kwargs
) -> GrowthEvent:
    """Create a growth event with standard structure."""
    return GrowthEvent(event_type, plant_id, user_id, **kwargs)


def create_community_event(event_type: str, user_id: str, **kwargs) -> CommunityEvent:
    """Create a community event with standard structure."""
    return CommunityEvent(event_type, user_id, **kwargs)


def create_system_event(event_type: str, **kwargs) -> SystemEvent:
    """Create a system event with standard structure."""
    return SystemEvent(event_type, **kwargs)


def create_analytics_event(event_type: str, action: str, **kwargs) -> AnalyticsEvent:
    """Create an analytics event with standard structure."""
    return AnalyticsEvent(event_type, action, **kwargs)


def create_notification_event(
    event_type: str,
    recipient_id: str,
    notification_type: str,
    **kwargs
) -> NotificationEvent:
    """Create a notification event with standard structure."""
    return NotificationEvent(event_type, recipient_id, notification_type, **kwargs)


def create_integration_event(
    event_type: str,
    integration_name: str,
    **kwargs
) -> IntegrationEvent:
    """Create an integration event with standard structure."""
    return IntegrationEvent(event_type, integration_name, **kwargs)


# Export all event classes and utilities
__all__ = [
    'EventMetadata',
    'DomainEvent',
    'UserEvent',
    'PlantEvent',
    'CareEvent',
    'HealthEvent',
    'GrowthEvent',
    'CommunityEvent',
    'SystemEvent',
    'AnalyticsEvent',
    'NotificationEvent',
    'IntegrationEvent',
    'EventHandler',
    'EventStream',
    'create_user_event',
    'create_plant_event',
    'create_care_event',
    'create_health_event',
    'create_growth_event',
    'create_community_event',
    'create_system_event',
    'create_analytics_event',
    'create_notification_event',
    'create_integration_event'
]