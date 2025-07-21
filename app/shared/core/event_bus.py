"""
Event bus system for Plant Care Application.
Enables decoupled communication between modules through domain events.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Callable, Optional, Type, TypeVar, Generic
from dataclasses import dataclass, asdict
from datetime import datetime
from abc import ABC, abstractmethod
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='DomainEvent')


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class DomainEvent:
    """
    Base class for all domain events.
    Events represent something that happened in the domain.
    """
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    user_id: Optional[str]
    timestamp: datetime
    version: int = 1
    priority: EventPriority = EventPriority.NORMAL
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize event after creation."""
        if not self.event_id:
            self.event_id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
        if not self.metadata:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Create event from dictionary."""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['priority'] = EventPriority(data['priority'])
        return cls(**data)
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to event."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for event tracing."""
        if self.metadata:
            return self.metadata.get('correlation_id')
        return None
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for event tracing."""
        self.add_metadata('correlation_id', correlation_id)


class EventHandler(ABC, Generic[T]):
    """
    Abstract base class for event handlers.
    Each handler processes specific types of domain events.
    """
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Event type this handler processes."""
        pass
    
    @abstractmethod
    async def handle(self, event: T) -> bool:
        """
        Handle the domain event.
        
        Args:
            event: Domain event to handle
            
        Returns:
            bool: True if handled successfully
        """
        pass
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can process the event."""
        return event.event_type == self.event_type
    
    async def on_error(self, event: T, error: Exception):
        """Handle errors during event processing."""
        logger.error(f"Error handling event {event.event_id}: {error}", exc_info=True)


@dataclass
class EventSubscription:
    """Event subscription configuration."""
    handler: EventHandler
    event_type: str
    priority: int = 1
    retry_count: int = 3
    timeout: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary."""
        return {
            "handler_name": self.handler.__class__.__name__,
            "event_type": self.event_type,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "timeout": self.timeout
        }


class EventStore:
    """
    Event store for persisting domain events.
    Simple in-memory implementation for now.
    """
    
    def __init__(self):
        self.events: List[DomainEvent] = []
        self._lock = asyncio.Lock()
    
    async def append(self, event: DomainEvent):
        """Store an event."""
        async with self._lock:
            self.events.append(event)
            logger.debug(f"Event stored: {event.event_type} - {event.event_id}")
    
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events with optional filtering."""
        async with self._lock:
            filtered_events = self.events
            
            if aggregate_id:
                filtered_events = [e for e in filtered_events if e.aggregate_id == aggregate_id]
            
            if event_type:
                filtered_events = [e for e in filtered_events if e.event_type == event_type]
            
            if since:
                filtered_events = [e for e in filtered_events if e.timestamp >= since]
            
            # Sort by timestamp
            filtered_events.sort(key=lambda e: e.timestamp)
            
            if limit:
                filtered_events = filtered_events[:limit]
            
            return filtered_events
    
    async def get_event_count(self) -> int:
        """Get total number of stored events."""
        async with self._lock:
            return len(self.events)
    
    async def clear(self):
        """Clear all stored events."""
        async with self._lock:
            self.events.clear()
            logger.info("Event store cleared")


class EventBus:
    """
    Event bus for publishing and subscribing to domain events.
    Handles asynchronous event processing and error handling.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.event_store = event_store or EventStore()
        self._processing_queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._worker_count = 3
        self._running = False
        self._stats = {
            "published": 0,
            "processed": 0,
            "failed": 0,
            "retries": 0
        }
    
    async def start(self):
        """Start event processing workers."""
        if self._running:
            return
        
        self._running = True
        
        # Start worker tasks
        for i in range(self._worker_count):
            worker = asyncio.create_task(self._event_worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Event bus started with {self._worker_count} workers")
    
    async def stop(self):
        """Stop event processing workers."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("Event bus stopped")
    
    async def _event_worker(self, worker_name: str):
        """Worker task for processing events."""
        logger.info(f"Event worker {worker_name} started")
        
        while self._running:
            try:
                # Get event from queue with timeout
                try:
                    event, correlation_id = await asyncio.wait_for(
                        self._processing_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                logger.debug(f"Worker {worker_name} processing event: {event.event_type}")
                
                # Process event
                await self._process_event(event, correlation_id)
                
                # Mark task as done
                self._processing_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info(f"Event worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Event worker {worker_name} error: {e}", exc_info=True)
        
        logger.info(f"Event worker {worker_name} stopped")
    
    async def _process_event(self, event: DomainEvent, correlation_id: Optional[str]):
        """Process a single event through all subscribed handlers."""
        event_type = event.event_type
        
        if event_type not in self.subscriptions:
            logger.debug(f"No handlers for event type: {event_type}")
            return
        
        # Set correlation ID if provided
        if correlation_id:
            event.set_correlation_id(correlation_id)
        
        handlers = self.subscriptions[event_type]
        
        # Sort handlers by priority
        handlers.sort(key=lambda s: s.priority, reverse=True)
        
        for subscription in handlers:
            await self._execute_handler(event, subscription)
    
    async def _execute_handler(self, event: DomainEvent, subscription: EventSubscription):
        """Execute a single event handler with retry logic."""
        handler = subscription.handler
        retry_count = subscription.retry_count
        timeout = subscription.timeout
        
        for attempt in range(retry_count + 1):
            try:
                # Execute handler with optional timeout
                if timeout:
                    success = await asyncio.wait_for(
                        handler.handle(event), 
                        timeout=timeout
                    )
                else:
                    success = await handler.handle(event)
                
                if success:
                    self._stats["processed"] += 1
                    logger.debug(f"Event {event.event_id} handled by {handler.__class__.__name__}")
                    return
                else:
                    raise Exception("Handler returned False")
                
            except asyncio.TimeoutError:
                error_msg = f"Handler {handler.__class__.__name__} timed out for event {event.event_id}"
                logger.warning(error_msg)
                
                if attempt < retry_count:
                    self._stats["retries"] += 1
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    self._stats["failed"] += 1
                    await handler.on_error(event, TimeoutError(error_msg))
                
            except Exception as e:
                error_msg = f"Handler {handler.__class__.__name__} failed for event {event.event_id}: {e}"
                logger.warning(error_msg)
                
                if attempt < retry_count:
                    self._stats["retries"] += 1
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    self._stats["failed"] += 1
                    await handler.on_error(event, e)
    
    def subscribe(
        self,
        handler: EventHandler,
        event_type: Optional[str] = None,
        priority: int = 1,
        retry_count: int = 3,
        timeout: Optional[int] = None
    ):
        """
        Subscribe handler to event type.
        
        Args:
            handler: Event handler instance
            event_type: Event type to subscribe to (uses handler.event_type if None)
            priority: Handler priority (higher = executed first)
            retry_count: Number of retry attempts on failure
            timeout: Handler timeout in seconds
        """
        if event_type is None:
            event_type = handler.event_type
        
        subscription = EventSubscription(
            handler=handler,
            event_type=event_type,
            priority=priority,
            retry_count=retry_count,
            timeout=timeout
        )
        
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        
        self.subscriptions[event_type].append(subscription)
        
        logger.info(f"Handler {handler.__class__.__name__} subscribed to {event_type}")
    
    def unsubscribe(self, handler: EventHandler, event_type: Optional[str] = None):
        """
        Unsubscribe handler from event type.
        
        Args:
            handler: Event handler instance
            event_type: Event type to unsubscribe from
        """
        if event_type is None:
            event_type = handler.event_type
        
        if event_type in self.subscriptions:
            self.subscriptions[event_type] = [
                s for s in self.subscriptions[event_type] 
                if s.handler != handler
            ]
            
            if not self.subscriptions[event_type]:
                del self.subscriptions[event_type]
        
        logger.info(f"Handler {handler.__class__.__name__} unsubscribed from {event_type}")
    
    async def publish(
        self, 
        event: DomainEvent,
        correlation_id: Optional[str] = None
    ):
        """
        Publish event to the bus.
        
        Args:
            event: Domain event to publish
            correlation_id: Optional correlation ID for tracing
        """
        # Store event for persistence
        await self.event_store.append(event)
        
        # Add to processing queue
        await self._processing_queue.put((event, correlation_id))
        
        self._stats["published"] += 1
        
        logger.info(f"Event published: {event.event_type} - {event.event_id}")
    
    async def publish_and_wait(
        self,
        event: DomainEvent,
        correlation_id: Optional[str] = None,
        timeout: Optional[int] = 30
    ):
        """
        Publish event and wait for all handlers to complete.
        
        Args:
            event: Domain event to publish
            correlation_id: Optional correlation ID for tracing
            timeout: Timeout for waiting
        """
        await self.publish(event, correlation_id)
        
        # Wait for queue to be processed
        try:
            await asyncio.wait_for(self._processing_queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for event {event.event_id} to be processed")
    
    def get_subscriptions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all current subscriptions."""
        return {
            event_type: [sub.to_dict() for sub in subscriptions]
            for event_type, subscriptions in self.subscriptions.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "queue_size": self._processing_queue.qsize(),
            "worker_count": len(self._workers),
            "subscription_count": sum(len(subs) for subs in self.subscriptions.values()),
            "event_types": list(self.subscriptions.keys())
        }
    
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Get events from event store."""
        return await self.event_store.get_events(aggregate_id, event_type, since, limit)
    
    async def clear_events(self):
        """Clear all stored events."""
        await self.event_store.clear()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on event bus."""
        return {
            "service": "event_bus",
            "status": "healthy" if self._running else "stopped",
            "workers_running": len([w for w in self._workers if not w.done()]),
            "queue_size": self._processing_queue.qsize(),
            "stats": self.get_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }


# Domain event implementations for Plant Care modules
@dataclass
class UserEvent(DomainEvent):
    """Base class for user-related events."""
    pass


@dataclass
class UserRegisteredEvent(UserEvent):
    """Event fired when a new user registers."""
    email: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.email is None:
            raise ValueError("email is required for UserRegisteredEvent")
        self.event_type = "user.registered"
        self.aggregate_type = "user"

@dataclass
class UserUpdatedEvent(UserEvent):
    changes: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.changes is None:
            raise ValueError("changes is required for UserUpdatedEvent")
        self.event_type = "user.updated"
        self.aggregate_type = "user"
        

@dataclass
class PlantEvent(DomainEvent):
    """Base class for plant-related events."""
    plant_name: Optional[str] = None


@dataclass
class PlantAddedEvent(PlantEvent):
    plant_species: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.plant_species is None:
            raise ValueError("plant_species is required for PlantAddedEvent")
        self.event_type = "plant.added"
        self.aggregate_type = "plant"


@dataclass
class PlantCareCompletedEvent(PlantEvent):
    care_type: Optional[str] = None
    care_notes: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.care_type is None:
            raise ValueError("care_type is required for PlantCareCompletedEvent")
        self.event_type = "plant.care_completed"
        self.aggregate_type = "plant"

@dataclass
class PlantHealthChangedEvent(PlantEvent):
    old_health_status: Optional[str] = None
    new_health_status: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.old_health_status is None:
            raise ValueError("old_health_status is required for PlantHealthChangedEvent")
        if self.new_health_status is None:
            raise ValueError("new_health_status is required for PlantHealthChangedEvent")
        self.event_type = "plant.health_changed"
        self.aggregate_type = "plant"

@dataclass
class PlantMilestoneEvent(PlantEvent):
    milestone_type: Optional[str] = None
    milestone_description: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.milestone_type is None:
            raise ValueError("milestone_type is required for PlantMilestoneEvent")
        if self.milestone_description is None:
            raise ValueError("milestone_description is required for PlantMilestoneEvent")
        self.event_type = "plant.milestone_reached"
        self.aggregate_type = "plant"

# Global event bus instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """
    Get global event bus instance.
    
    Returns:
        EventBus: Event bus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.start()
    return _event_bus


async def publish_event(
    event: DomainEvent,
    correlation_id: Optional[str] = None
):
    """
    Publish event to global event bus.
    
    Args:
        event: Domain event to publish
        correlation_id: Optional correlation ID for tracing
    """
    event_bus = await get_event_bus()
    await event_bus.publish(event, correlation_id)


def subscribe_to_event(
    handler: EventHandler,
    event_type: Optional[str] = None,
    priority: int = 1,
    retry_count: int = 3,
    timeout: Optional[int] = None
):
    """
    Subscribe handler to event type on global event bus.
    
    Args:
        handler: Event handler instance
        event_type: Event type to subscribe to
        priority: Handler priority
        retry_count: Number of retry attempts
        timeout: Handler timeout
    """
    async def _subscribe():
        event_bus = await get_event_bus()
        event_bus.subscribe(handler, event_type, priority, retry_count, timeout)
    
    # Schedule subscription
    asyncio.create_task(_subscribe())


async def shutdown_event_bus():
    """Shutdown global event bus."""
    global _event_bus
    if _event_bus:
        await _event_bus.stop()
        _event_bus = None
        logger.info("Global event bus shutdown")


# Event handler decorators and utilities
def event_handler(event_type: str, priority: int = 1):
    """
    Decorator for marking methods as event handlers.
    
    Args:
        event_type: Event type to handle
        priority: Handler priority
    """
    def decorator(func):
        func._event_type = event_type
        func._priority = priority
        func._is_event_handler = True
        return func
    return decorator


class BaseEventHandler(EventHandler[DomainEvent]):
    """Base implementation of event handler with common functionality."""
    
    def __init__(self, name: str):
        self.name = name
        self.processed_count = 0
        self.error_count = 0
    
    @property
    def event_type(self) -> str:
        """Must be implemented by subclasses."""
        raise NotImplementedError
    
    async def handle(self, event: DomainEvent) -> bool:
        """Must be implemented by subclasses."""
        raise NotImplementedError
    
    async def on_error(self, event: DomainEvent, error: Exception):
        """Enhanced error handling with metrics."""
        self.error_count += 1
        logger.error(
            f"Handler {self.name} error processing {event.event_type}: {error}",
            extra={
                "handler_name": self.name,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "error_count": self.error_count
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            "name": self.name,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count) 
                if (self.processed_count + self.error_count) > 0 
                else 0.0
            )
        }


# Example event handlers for core functionality
class UserRegistrationHandler(BaseEventHandler):
    """Handler for user registration events."""
    
    def __init__(self):
        super().__init__("user_registration_handler")
    
    @property
    def event_type(self) -> str:
        return "user.registered"
    
    async def handle(self, event: UserRegisteredEvent) -> bool:
        """Handle user registration event."""
        try:
            logger.info(f"Processing user registration for {event.email}")
            
            # Example: Send welcome email, set up default preferences, etc.
            # This would integrate with notification system
            
            self.processed_count += 1
            return True
            
        except Exception as e:
            await self.on_error(event, e)
            return False


class PlantCareReminderHandler(BaseEventHandler):
    """Handler for plant care completion events."""
    
    def __init__(self):
        super().__init__("plant_care_reminder_handler")
    
    @property
    def event_type(self) -> str:
        return "plant.care_completed"
    
    async def handle(self, event: PlantCareCompletedEvent) -> bool:
        """Handle plant care completion event."""
        try:
            logger.info(f"Processing care completion for plant {event.aggregate_id}")
            
            # Example: Update care schedule, send congratulations, update analytics
            # This would integrate with care management system
            
            self.processed_count += 1
            return True
            
        except Exception as e:
            await self.on_error(event, e)
            return False