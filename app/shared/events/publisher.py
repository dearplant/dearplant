# 📄 File: app/shared/events/publisher.py
# 🧭 Purpose (Layman Explanation): 
# This file is like a postal service for the app - when something important happens (like watering a plant),
# it makes sure the right people/systems get notified so they can take appropriate actions.
# 🧪 Purpose (Technical Summary): 
# Implements event publishing system with async processing, event persistence, delivery guarantees,
# and integration with message queues for reliable inter-module communication.
# 🔗 Dependencies: 
# base.py, handlers.py, typing, asyncio, logging, datetime, json, redis, celery
# 🔄 Connected Modules / Calls From: 
# All domain modules, background jobs, notification system, audit logging, external integrations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type, Callable, Set, Union
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback
from collections import defaultdict, deque
import weakref
import pickle
import gzip
from concurrent.futures import ThreadPoolExecutor

from .base import DomainEvent, EventMetadata
from .handlers import EnhancedEventHandlerRegistry, HandlerExecutionResult, enhanced_event_registry

logger = logging.getLogger(__name__)


class EventDeliveryMode(Enum):
    """Event delivery modes"""
    IMMEDIATE = "immediate"      # Process immediately in current context
    ASYNC = "async"             # Process asynchronously in background
    PERSISTENT = "persistent"   # Persist event and process reliably
    BATCH = "batch"             # Batch events for efficient processing


class EventPriority(Enum):
    """Event priority levels"""
    CRITICAL = 1    # System critical events (security, data integrity)
    HIGH = 2        # Important business events (user actions, notifications)
    NORMAL = 3      # Standard events (analytics, logging)
    LOW = 4         # Background events (cleanup, maintenance)


class EventStatus(Enum):
    """Event processing status"""
    PENDING = "pending"         # Event created but not processed
    PROCESSING = "processing"   # Event currently being processed
    COMPLETED = "completed"     # Event successfully processed
    FAILED = "failed"          # Event processing failed
    RETRYING = "retrying"      # Event being retried after failure
    DEAD_LETTER = "dead_letter" # Event failed all retries


@dataclass
class EventDeliveryConfig:
    """Configuration for event delivery"""
    delivery_mode: EventDeliveryMode = EventDeliveryMode.ASYNC
    priority: EventPriority = EventPriority.NORMAL
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_multiplier: float = 2.0
    max_retry_delay_seconds: float = 300.0
    timeout_seconds: float = 60.0
    persist_event: bool = True
    compress_payload: bool = False
    dead_letter_queue: bool = True


@dataclass
class PublishedEvent:
    """Published event with metadata and tracking"""
    event_id: str
    event_type: str
    event_data: Dict[str, Any]
    metadata: EventMetadata
    config: EventDeliveryConfig
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    handler_results: Dict[str, HandlerExecutionResult] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None


class EventPersistence:
    """Interface for event persistence"""
    
    async def save_event(self, published_event: PublishedEvent) -> bool:
        """Save event to persistent storage"""
        raise NotImplementedError
    
    async def get_event(self, event_id: str) -> Optional[PublishedEvent]:
        """Retrieve event from storage"""
        raise NotImplementedError
    
    async def update_event_status(self, event_id: str, status: EventStatus, 
                                 error_message: Optional[str] = None) -> bool:
        """Update event status"""
        raise NotImplementedError
    
    async def get_pending_events(self, limit: int = 100) -> List[PublishedEvent]:
        """Get pending events for processing"""
        raise NotImplementedError
    
    async def get_failed_events(self, limit: int = 100) -> List[PublishedEvent]:
        """Get failed events for retry"""
        raise NotImplementedError
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """Clean up old events"""
        raise NotImplementedError


class MemoryEventPersistence(EventPersistence):
    """In-memory event persistence for development/testing"""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: Dict[str, PublishedEvent] = {}
        self.event_queue = deque(maxlen=max_events)
    
    async def save_event(self, published_event: PublishedEvent) -> bool:
        """Save event to memory"""
        self.events[published_event.event_id] = published_event
        self.event_queue.append(published_event.event_id)
        
        # Remove oldest events if limit exceeded
        if len(self.events) > self.max_events:
            oldest_id = self.event_queue.popleft()
            if oldest_id in self.events:
                del self.events[oldest_id]
        
        return True
    
    async def get_event(self, event_id: str) -> Optional[PublishedEvent]:
        """Retrieve event from memory"""
        return self.events.get(event_id)
    
    async def update_event_status(self, event_id: str, status: EventStatus, 
                                 error_message: Optional[str] = None) -> bool:
        """Update event status in memory"""
        if event_id in self.events:
            self.events[event_id].status = status
            if error_message:
                self.events[event_id].last_error = error_message
            if status == EventStatus.COMPLETED:
                self.events[event_id].completed_at = datetime.now()
            return True
        return False
    
    async def get_pending_events(self, limit: int = 100) -> List[PublishedEvent]:
        """Get pending events from memory"""
        pending = [event for event in self.events.values() 
                  if event.status == EventStatus.PENDING]
        return sorted(pending, key=lambda x: x.created_at)[:limit]
    
    async def get_failed_events(self, limit: int = 100) -> List[PublishedEvent]:
        """Get failed events from memory"""
        failed = [event for event in self.events.values() 
                 if event.status == EventStatus.FAILED]
        return sorted(failed, key=lambda x: x.created_at)[:limit]
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """Clean up old events from memory"""
        old_event_ids = [
            event_id for event_id, event in self.events.items()
            if event.created_at < older_than and event.status in [EventStatus.COMPLETED, EventStatus.DEAD_LETTER]
        ]
        
        for event_id in old_event_ids:
            del self.events[event_id]
        
        return len(old_event_ids)


class RedisEventPersistence(EventPersistence):
    """Redis-based event persistence"""
    
    def __init__(self, redis_client, key_prefix: str = "events:"):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.event_key = f"{key_prefix}event:"
        self.pending_key = f"{key_prefix}pending"
        self.failed_key = f"{key_prefix}failed"
        self.processing_key = f"{key_prefix}processing"
    
    def _serialize_event(self, event: PublishedEvent) -> bytes:
        """Serialize event for storage"""
        data = asdict(event)
        # Convert datetime objects to ISO strings
        data['created_at'] = event.created_at.isoformat()
        if event.processing_started_at:
            data['processing_started_at'] = event.processing_started_at.isoformat()
        if event.completed_at:
            data['completed_at'] = event.completed_at.isoformat()
        
        serialized = json.dumps(data).encode('utf-8')
        
        # Compress if configured
        if event.config.compress_payload:
            serialized = gzip.compress(serialized)
        
        return serialized
    
    def _deserialize_event(self, data: bytes) -> PublishedEvent:
        """Deserialize event from storage"""
        # Try to decompress first
        try:
            decompressed = gzip.decompress(data)
            data = decompressed
        except gzip.BadGzipFile:
            pass  # Not compressed
        
        event_dict = json.loads(data.decode('utf-8'))
        
        # Convert ISO strings back to datetime objects
        event_dict['created_at'] = datetime.fromisoformat(event_dict['created_at'])
        if event_dict.get('processing_started_at'):
            event_dict['processing_started_at'] = datetime.fromisoformat(event_dict['processing_started_at'])
        if event_dict.get('completed_at'):
            event_dict['completed_at'] = datetime.fromisoformat(event_dict['completed_at'])
        
        # Reconstruct nested objects
        event_dict['metadata'] = EventMetadata(**event_dict['metadata'])
        event_dict['config'] = EventDeliveryConfig(**event_dict['config'])
        event_dict['status'] = EventStatus(event_dict['status'])
        
        # Reconstruct handler results
        handler_results = {}
        for handler_id, result_dict in event_dict.get('handler_results', {}).items():
            handler_results[handler_id] = HandlerExecutionResult(**result_dict)
        event_dict['handler_results'] = handler_results
        
        return PublishedEvent(**event_dict)
    
    async def save_event(self, published_event: PublishedEvent) -> bool:
        """Save event to Redis"""
        try:
            event_key = f"{self.event_key}{published_event.event_id}"
            serialized_event = self._serialize_event(published_event)
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Store event data
            pipe.set(event_key, serialized_event)
            
            # Add to appropriate queue
            if published_event.status == EventStatus.PENDING:
                pipe.zadd(self.pending_key, {published_event.event_id: published_event.created_at.timestamp()})
            elif published_event.status == EventStatus.FAILED:
                pipe.zadd(self.failed_key, {published_event.event_id: published_event.created_at.timestamp()})
            elif published_event.status == EventStatus.PROCESSING:
                pipe.zadd(self.processing_key, {published_event.event_id: published_event.created_at.timestamp()})
            
            # Set TTL for event (30 days)
            pipe.expire(event_key, 30 * 24 * 3600)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save event {published_event.event_id}: {e}")
            return False
    
    async def get_event(self, event_id: str) -> Optional[PublishedEvent]:
        """Retrieve event from Redis"""
        try:
            event_key = f"{self.event_key}{event_id}"
            data = await self.redis.get(event_key)
            
            if data:
                return self._deserialize_event(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            return None
    
    async def update_event_status(self, event_id: str, status: EventStatus, 
                                 error_message: Optional[str] = None) -> bool:
        """Update event status in Redis"""
        try:
            event = await self.get_event(event_id)
            if not event:
                return False
            
            # Update status and error message
            old_status = event.status
            event.status = status
            if error_message:
                event.last_error = error_message
            if status == EventStatus.COMPLETED:
                event.completed_at = datetime.now()
            elif status == EventStatus.PROCESSING:
                event.processing_started_at = datetime.now()
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Save updated event
            event_key = f"{self.event_key}{event_id}"
            serialized_event = self._serialize_event(event)
            pipe.set(event_key, serialized_event)
            
            # Move between queues
            if old_status == EventStatus.PENDING:
                pipe.zrem(self.pending_key, event_id)
            elif old_status == EventStatus.FAILED:
                pipe.zrem(self.failed_key, event_id)
            elif old_status == EventStatus.PROCESSING:
                pipe.zrem(self.processing_key, event_id)
            
            if status == EventStatus.PENDING:
                pipe.zadd(self.pending_key, {event_id: event.created_at.timestamp()})
            elif status == EventStatus.FAILED:
                pipe.zadd(self.failed_key, {event_id: event.created_at.timestamp()})
            elif status == EventStatus.PROCESSING:
                pipe.zadd(self.processing_key, {event_id: event.created_at.timestamp()})
            
            await pipe.execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update event status {event_id}: {e}")
            return False
    
    async def get_pending_events(self, limit: int = 100) -> List[PublishedEvent]:
        """Get pending events from Redis"""
        try:
            # Get oldest pending events
            event_ids = await self.redis.zrange(self.pending_key, 0, limit - 1)
            
            events = []
            for event_id in event_ids:
                event = await self.get_event(event_id.decode('utf-8'))
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get pending events: {e}")
            return []
    
    async def get_failed_events(self, limit: int = 100) -> List[PublishedEvent]:
        """Get failed events from Redis"""
        try:
            # Get oldest failed events
            event_ids = await self.redis.zrange(self.failed_key, 0, limit - 1)
            
            events = []
            for event_id in event_ids:
                event = await self.get_event(event_id.decode('utf-8'))
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get failed events: {e}")
            return []
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """Clean up old events from Redis"""
        try:
            timestamp = older_than.timestamp()
            
            # Get old completed/dead letter events
            old_event_ids = set()
            
            # Check all queues for old events
            for queue_key in [self.pending_key, self.failed_key, self.processing_key]:
                ids = await self.redis.zrangebyscore(queue_key, 0, timestamp)
                old_event_ids.update(id.decode('utf-8') for id in ids)
            
            # Only delete completed or dead letter events
            events_to_delete = []
            for event_id in old_event_ids:
                event = await self.get_event(event_id)
                if event and event.status in [EventStatus.COMPLETED, EventStatus.DEAD_LETTER]:
                    events_to_delete.append(event_id)
            
            if events_to_delete:
                pipe = self.redis.pipeline()
                
                for event_id in events_to_delete:
                    # Delete event data
                    pipe.delete(f"{self.event_key}{event_id}")
                    
                    # Remove from all queues
                    pipe.zrem(self.pending_key, event_id)
                    pipe.zrem(self.failed_key, event_id)
                    pipe.zrem(self.processing_key, event_id)
                
                await pipe.execute()
            
            return len(events_to_delete)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0


class EventPublisher:
    """
    Advanced event publisher with persistence, delivery guarantees, and retry logic
    """
    
    def __init__(self, 
                 registry: Optional[EnhancedEventHandlerRegistry] = None,
                 persistence: Optional[EventPersistence] = None,
                 default_config: Optional[EventDeliveryConfig] = None):
        self.registry = registry or enhanced_event_registry
        self.persistence = persistence or MemoryEventPersistence()
        self.default_config = default_config or EventDeliveryConfig()
        
        # Event processing state
        self.processing_events: Set[str] = set()
        self.event_batches: Dict[str, List[PublishedEvent]] = defaultdict(list)
        self.batch_timers: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.published_count = 0
        self.processed_count = 0
        self.failed_count = 0
        self.last_processing_time = datetime.now()
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.processing_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Thread pool for blocking operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="event_publisher")
        
        logger.info("Event publisher initialized")
    
    async def publish(self, 
                     event: DomainEvent,
                     config: Optional[EventDeliveryConfig] = None,
                     correlation_id: Optional[str] = None,
                     causation_id: Optional[str] = None) -> str:
        """
        Publish a domain event
        
        Args:
            event: Domain event to publish
            config: Delivery configuration (optional)
            correlation_id: Correlation ID for tracing (optional)
            causation_id: Causation ID for event sourcing (optional)
            
        Returns:
            Event ID for tracking
        """
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Use provided config or default
        delivery_config = config or self.default_config
        
        # Create published event
        published_event = PublishedEvent(
            event_id=event_id,
            event_type=type(event).__name__,
            event_data=event.to_dict(),
            metadata=event.metadata,
            config=delivery_config,
            correlation_id=correlation_id,
            causation_id=causation_id
        )
        
        # Persist event if configured
        if delivery_config.persist_event:
            await self.persistence.save_event(published_event)
        
        # Process based on delivery mode
        if delivery_config.delivery_mode == EventDeliveryMode.IMMEDIATE:
            await self._process_event_immediate(published_event, event)
        elif delivery_config.delivery_mode == EventDeliveryMode.ASYNC:
            self._schedule_async_processing(published_event, event)
        elif delivery_config.delivery_mode == EventDeliveryMode.BATCH:
            await self._add_to_batch(published_event, event)
        else:  # PERSISTENT
            # Event is already persisted, will be picked up by background processor
            pass
        
        self.published_count += 1
        logger.debug(f"Published event {event_id} ({type(event).__name__}) with mode {delivery_config.delivery_mode.value}")
        
        return event_id
    
    async def _process_event_immediate(self, published_event: PublishedEvent, event: DomainEvent):
        """Process event immediately in current context"""
        try:
            published_event.status = EventStatus.PROCESSING
            published_event.processing_started_at = datetime.now()
            
            if published_event.config.persist_event:
                await self.persistence.update_event_status(
                    published_event.event_id, 
                    EventStatus.PROCESSING
                )
            
            # Execute handlers
            handler_results = await self.registry.publish(event)
            published_event.handler_results = handler_results
            
            # Check if all handlers succeeded
            all_succeeded = all(result.success for result in handler_results.values())
            
            if all_succeeded:
                published_event.status = EventStatus.COMPLETED
                published_event.completed_at = datetime.now()
                self.processed_count += 1
            else:
                published_event.status = EventStatus.FAILED
                self.failed_count += 1
            
            if published_event.config.persist_event:
                await self.persistence.update_event_status(
                    published_event.event_id,
                    published_event.status
                )
            
        except Exception as e:
            logger.error(f"Immediate processing failed for event {published_event.event_id}: {e}")
            published_event.status = EventStatus.FAILED
            published_event.last_error = str(e)
            self.failed_count += 1
            
            if published_event.config.persist_event:
                await self.persistence.update_event_status(
                    published_event.event_id,
                    EventStatus.FAILED,
                    str(e)
                )
    
    def _schedule_async_processing(self, published_event: PublishedEvent, event: DomainEvent):
        """Schedule asynchronous event processing"""
        task = asyncio.create_task(self._process_event_async(published_event, event))
        self.background_tasks.append(task)
        
        # Clean up completed tasks
        self.background_tasks = [t for t in self.background_tasks if not t.done()]
    
    async def _process_event_async(self, published_event: PublishedEvent, event: DomainEvent):
        """Process event asynchronously"""
        try:
            # Add processing delay based on priority
            if published_event.config.priority == EventPriority.LOW:
                await asyncio.sleep(0.1)  # Small delay for low priority events
            
            await self._process_event_immediate(published_event, event)
            
        except Exception as e:
            logger.error(f"Async processing failed for event {published_event.event_id}: {e}")
    
    async def _add_to_batch(self, published_event: PublishedEvent, event: DomainEvent):
        """Add event to batch for processing"""
        batch_key = f"{published_event.config.priority.name}_{type(event).__name__}"
        self.event_batches[batch_key].append(published_event)
        
        # Set timer for batch processing if not already set
        if batch_key not in self.batch_timers:
            self.batch_timers[batch_key] = asyncio.create_task(
                self._process_batch_after_delay(batch_key, 5.0)  # 5 second batch window
            )
        
        # Process batch immediately if it gets too large
        if len(self.event_batches[batch_key]) >= 10:  # Max batch size
            if batch_key in self.batch_timers:
                self.batch_timers[batch_key].cancel()
                del self.batch_timers[batch_key]
            await self._process_batch(batch_key)
    
    async def _process_batch_after_delay(self, batch_key: str, delay: float):
        """Process batch after delay"""
        await asyncio.sleep(delay)
        await self._process_batch(batch_key)
        if batch_key in self.batch_timers:
            del self.batch_timers[batch_key]
    
    async def _process_batch(self, batch_key: str):
        """Process a batch of events"""
        if batch_key not in self.event_batches or not self.event_batches[batch_key]:
            return
        
        events = self.event_batches[batch_key].copy()
        self.event_batches[batch_key].clear()
        
        logger.info(f"Processing batch {batch_key} with {len(events)} events")
        
        # Process events in batch
        tasks = []
        for published_event in events:
            # Reconstruct domain event from stored data
            try:
                event_class = self._get_event_class(published_event.event_type)
                event = event_class.from_dict(published_event.event_data)
                task = self._process_event_async(published_event, event)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to reconstruct event {published_event.event_id}: {e}")
        
        # Execute all tasks in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def _get_event_class(self, event_type_name: str) -> Type[DomainEvent]:
        """Get event class by name (simplified implementation)"""
        # In a real implementation, this would use a registry of event types
        # For now, return a generic DomainEvent
        return DomainEvent
    
    async def start_background_processing(self):
        """Start background event processing"""
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._background_processor())
            logger.info("Started background event processing")
        
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._background_cleanup())
            logger.info("Started background cleanup task")
    
    async def stop_background_processing(self):
        """Stop background event processing"""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped background event processing")
    
    async def _background_processor(self):
        """Background processor for persistent events"""
        while True:
            try:
                # Process pending events
                pending_events = await self.persistence.get_pending_events(limit=50)
                
                for published_event in pending_events:
                    if published_event.event_id in self.processing_events:
                        continue  # Already being processed
                    
                    self.processing_events.add(published_event.event_id)
                    
                    try:
                        # Reconstruct domain event
                        event_class = self._get_event_class(published_event.event_type)
                        event = event_class.from_dict(published_event.event_data)
                        
                        # Process event
                        await self._process_event_immediate(published_event, event)
                        
                    except Exception as e:
                        logger.error(f"Background processing failed for event {published_event.event_id}: {e}")
                        
                        # Handle retry logic
                        await self._handle_event_retry(published_event, str(e))
                    
                    finally:
                        self.processing_events.discard(published_event.event_id)
                
                # Process failed events that are ready for retry
                await self._process_retry_events()
                
                # Update processing time
                self.last_processing_time = datetime.now()
                
                # Sleep before next processing cycle
                await asyncio.sleep(5.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(10.0)
    
    async def _handle_event_retry(self, published_event: PublishedEvent, error_message: str):
        """Handle event retry logic"""
        published_event.retry_count += 1
        published_event.last_error = error_message
        
        if published_event.retry_count <= published_event.config.max_retries:
            # Calculate retry delay with exponential backoff
            delay = min(
                published_event.config.retry_delay_seconds * 
                (published_event.config.retry_backoff_multiplier ** (published_event.retry_count - 1)),
                published_event.config.max_retry_delay_seconds
            )
            
            # Schedule retry
            published_event.status = EventStatus.RETRYING
            await self.persistence.update_event_status(
                published_event.event_id,
                EventStatus.RETRYING,
                error_message
            )
            
            # Add delay before making it pending again
            asyncio.create_task(self._schedule_retry(published_event, delay))
            
        else:
            # Max retries exceeded
            if published_event.config.dead_letter_queue:
                published_event.status = EventStatus.DEAD_LETTER
                await self.persistence.update_event_status(
                    published_event.event_id,
                    EventStatus.DEAD_LETTER,
                    f"Max retries exceeded: {error_message}"
                )
            else:
                published_event.status = EventStatus.FAILED
                await self.persistence.update_event_status(
                    published_event.event_id,
                    EventStatus.FAILED,
                    f"Max retries exceeded: {error_message}"
                )
            
            self.failed_count += 1
    
    async def _schedule_retry(self, published_event: PublishedEvent, delay: float):
        """Schedule event retry after delay"""
        await asyncio.sleep(delay)
        
        # Set event back to pending for retry
        published_event.status = EventStatus.PENDING
        await self.persistence.update_event_status(
            published_event.event_id,
            EventStatus.PENDING
        )
        
        logger.info(f"Scheduled retry for event {published_event.event_id} after {delay}s delay")
    
    async def _process_retry_events(self):
        """Process events that are ready for retry"""
        failed_events = await self.persistence.get_failed_events(limit=20)
        
        for event in failed_events:
            if event.status == EventStatus.RETRYING:
                # Check if enough time has passed for retry
                if event.processing_started_at:
                    time_since_processing = datetime.now() - event.processing_started_at
                    if time_since_processing.total_seconds() < event.config.retry_delay_seconds:
                        continue  # Not ready for retry yet
                
                # Make event pending for retry
                event.status = EventStatus.PENDING
                await self.persistence.update_event_status(event.event_id, EventStatus.PENDING)
    
    async def _background_cleanup(self):
        """Background cleanup of old events"""
        while True:
            try:
                # Clean up events older than 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                cleaned_count = await self.persistence.cleanup_old_events(cutoff_date)
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} old events")
                
                # Clean up completed background tasks
                self.background_tasks = [t for t in self.background_tasks if not t.done()]
                
                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")
                await asyncio.sleep(3600)
    
    async def get_event_status(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a published event
        
        Args:
            event_id: Event ID
            
        Returns:
            Event status information
        """
        event = await self.persistence.get_event(event_id)
        if not event:
            return None
        
        return {
            'event_id': event.event_id,
            'event_type': event.event_type,
            'status': event.status.value,
            'priority': event.config.priority.name,
            'delivery_mode': event.config.delivery_mode.value,
            'created_at': event.created_at.isoformat(),
            'processing_started_at': event.processing_started_at.isoformat() if event.processing_started_at else None,
            'completed_at': event.completed_at.isoformat() if event.completed_at else None,
            'retry_count': event.retry_count,
            'max_retries': event.config.max_retries,
            'last_error': event.last_error,
            'handler_results': {
                handler_id: {
                    'success': result.success,
                    'execution_time': result.execution_time,
                    'error_message': result.error_message
                }
                for handler_id, result in event.handler_results.items()
            },
            'correlation_id': event.correlation_id,
            'causation_id': event.causation_id
        }
    
    async def retry_failed_event(self, event_id: str) -> bool:
        """
        Manually retry a failed event
        
        Args:
            event_id: Event ID to retry
            
        Returns:
            True if retry was scheduled
        """
        event = await self.persistence.get_event(event_id)
        if not event:
            return False
        
        if event.status not in [EventStatus.FAILED, EventStatus.DEAD_LETTER]:
            return False
        
        # Reset retry count and set to pending
        event.retry_count = 0
        event.status = EventStatus.PENDING
        event.last_error = None
        
        success = await self.persistence.update_event_status(event_id, EventStatus.PENDING)
        
        if success:
            logger.info(f"Manually scheduled retry for event {event_id}")
        
        return success
    
    async def cancel_event(self, event_id: str) -> bool:
        """
        Cancel a pending event
        
        Args:
            event_id: Event ID to cancel
            
        Returns:
            True if event was cancelled
        """
        event = await self.persistence.get_event(event_id)
        if not event:
            return False
        
        if event.status != EventStatus.PENDING:
            return False
        
        success = await self.persistence.update_event_status(
            event_id, 
            EventStatus.DEAD_LETTER,
            "Manually cancelled"
        )
        
        if success:
            logger.info(f"Cancelled event {event_id}")
        
        return success
    
    def get_publisher_metrics(self) -> Dict[str, Any]:
        """
        Get publisher performance metrics
        
        Returns:
            Publisher metrics
        """
        return {
            'published_count': self.published_count,
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'success_rate': self.processed_count / max(self.published_count, 1),
            'processing_events_count': len(self.processing_events),
            'background_tasks_count': len(self.background_tasks),
            'active_batches': len(self.event_batches),
            'batch_events_count': sum(len(events) for events in self.event_batches.values()),
            'last_processing_time': self.last_processing_time.isoformat(),
            'is_processing': self.processing_task is not None and not self.processing_task.done(),
            'is_cleanup_running': self.cleanup_task is not None and not self.cleanup_task.done()
        }
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get event queue status
        
        Returns:
            Queue status information
        """
        try:
            pending_events = await self.persistence.get_pending_events(limit=1000)
            failed_events = await self.persistence.get_failed_events(limit=1000)
            
            # Group by priority and type
            pending_by_priority = defaultdict(int)
            pending_by_type = defaultdict(int)
            failed_by_type = defaultdict(int)
            
            for event in pending_events:
                pending_by_priority[event.config.priority.name] += 1
                pending_by_type[event.event_type] += 1
            
            for event in failed_events:
                failed_by_type[event.event_type] += 1
            
            return {
                'pending_count': len(pending_events),
                'failed_count': len(failed_events),
                'pending_by_priority': dict(pending_by_priority),
                'pending_by_type': dict(pending_by_type),
                'failed_by_type': dict(failed_by_type),
                'oldest_pending': pending_events[0].created_at.isoformat() if pending_events else None,
                'oldest_failed': failed_events[0].created_at.isoformat() if failed_events else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                'pending_count': 0,
                'failed_count': 0,
                'error': str(e)
            }
    
    async def purge_dead_letter_events(self, older_than_hours: int = 24) -> int:
        """
        Purge dead letter events older than specified hours
        
        Args:
            older_than_hours: Age threshold in hours
            
        Returns:
            Number of events purged
        """
        cutoff_date = datetime.now() - timedelta(hours=older_than_hours)
        return await self.persistence.cleanup_old_events(cutoff_date)
    
    async def shutdown(self):
        """Shutdown the event publisher"""
        logger.info("Shutting down event publisher...")
        
        # Stop background processing
        await self.stop_background_processing()
        
        # Wait for background tasks to complete
        if self.background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some background tasks did not complete within shutdown timeout")
        
        # Cancel batch timers
        for timer in self.batch_timers.values():
            timer.cancel()
        self.batch_timers.clear()
        
        # Process remaining batches
        for batch_key in list(self.event_batches.keys()):
            if self.event_batches[batch_key]:
                await self._process_batch(batch_key)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Event publisher shutdown complete")


class EventStreamPublisher(EventPublisher):
    """
    Extended publisher with event streaming capabilities
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_stream: deque = deque(maxlen=1000)  # In-memory event stream
    
    def subscribe_to_stream(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Subscribe to event stream
        
        Args:
            event_type: Event type to subscribe to
            callback: Callback function to receive events
        """
        self.subscribers[event_type].append(callback)
        logger.info(f"Added subscriber for {event_type} events")
    
    def unsubscribe_from_stream(self, event_type: str, callback: Callable):
        """
        Unsubscribe from event stream
        
        Args:
            event_type: Event type to unsubscribe from
            callback: Callback function to remove
        """
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            logger.info(f"Removed subscriber for {event_type} events")
    
    async def publish(self, event: DomainEvent, **kwargs) -> str:
        """
        Publish event with streaming support
        
        Args:
            event: Domain event to publish
            **kwargs: Additional arguments
            
        Returns:
            Event ID
        """
        # Call parent publish method
        event_id = await super().publish(event, **kwargs)
        
        # Add to event stream
        stream_event = {
            'event_id': event_id,
            'event_type': type(event).__name__,
            'event_data': event.to_dict(),
            'timestamp': datetime.now().isoformat(),
            'metadata': event.metadata.to_dict()
        }
        
        self.event_stream.append(stream_event)
        
        # Notify subscribers
        event_type = type(event).__name__
        for callback in self.subscribers.get(event_type, []):
            try:
                # Call subscriber in thread pool to avoid blocking
                self.thread_pool.submit(callback, stream_event)
            except Exception as e:
                logger.error(f"Subscriber callback error for {event_type}: {e}")
        
        # Notify wildcard subscribers
        for callback in self.subscribers.get("*", []):
            try:
                self.thread_pool.submit(callback, stream_event)
            except Exception as e:
                logger.error(f"Wildcard subscriber callback error: {e}")
        
        return event_id
    
    def get_event_stream(self, event_types: Optional[List[str]] = None, 
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events from stream
        
        Args:
            event_types: Filter by event types (optional)
            limit: Maximum number of events
            
        Returns:
            List of stream events
        """
        events = list(self.event_stream)
        
        # Filter by event types if specified
        if event_types:
            events = [e for e in events if e['event_type'] in event_types]
        
        # Return most recent events
        return events[-limit:] if events else []


# Global publisher instance
event_publisher = EventPublisher()
event_stream_publisher = EventStreamPublisher()


# Utility functions for easy event publishing
async def publish_event(event: DomainEvent, 
                       delivery_mode: EventDeliveryMode = EventDeliveryMode.ASYNC,
                       priority: EventPriority = EventPriority.NORMAL,
                       correlation_id: Optional[str] = None) -> str:
    """
    Convenient function to publish events
    
    Args:
        event: Domain event to publish
        delivery_mode: How to deliver the event
        priority: Event priority
        correlation_id: Correlation ID for tracing
        
    Returns:
        Event ID
    """
    config = EventDeliveryConfig(
        delivery_mode=delivery_mode,
        priority=priority
    )
    
    return await event_publisher.publish(
        event, 
        config=config, 
        correlation_id=correlation_id
    )


async def publish_critical_event(event: DomainEvent, 
                                correlation_id: Optional[str] = None) -> str:
    """
    Publish critical event with immediate processing
    
    Args:
        event: Critical domain event
        correlation_id: Correlation ID for tracing
        
    Returns:
        Event ID
    """
    return await publish_event(
        event,
        delivery_mode=EventDeliveryMode.IMMEDIATE,
        priority=EventPriority.CRITICAL,
        correlation_id=correlation_id
    )


async def publish_background_event(event: DomainEvent,
                                  correlation_id: Optional[str] = None) -> str:
    """
    Publish background event with batch processing
    
    Args:
        event: Background domain event
        correlation_id: Correlation ID for tracing
        
    Returns:
        Event ID
    """
    return await publish_event(
        event,
        delivery_mode=EventDeliveryMode.BATCH,
        priority=EventPriority.LOW,
        correlation_id=correlation_id
    )


# Context manager for event correlation
class EventContext:
    """Context manager for event correlation and causation tracking"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.causation_stack: List[str] = []
        self.events_published: List[str] = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Event context error: {exc_val}")
        
        logger.info(f"Event context {self.correlation_id} published {len(self.events_published)} events")
    
    async def publish(self, event: DomainEvent, **kwargs) -> str:
        """Publish event within this context"""
        causation_id = self.causation_stack[-1] if self.causation_stack else None
        
        event_id = await event_publisher.publish(
            event,
            correlation_id=self.correlation_id,
            causation_id=causation_id,
            **kwargs
        )
        
        self.events_published.append(event_id)
        self.causation_stack.append(event_id)
        
        return event_id


# Health check function
async def create_publisher_health_check() -> Dict[str, Any]:
    """
    Create health check for event publisher
    
    Returns:
        Health check data
    """
    try:
        metrics = event_publisher.get_publisher_metrics()
        queue_status = await event_publisher.get_queue_status()
        
        # Determine health status
        success_rate = metrics['success_rate']
        pending_count = queue_status['pending_count']
        failed_count = queue_status['failed_count']
        
        if success_rate >= 0.95 and pending_count < 100 and failed_count < 10:
            status = "healthy"
        elif success_rate >= 0.8 and pending_count < 500 and failed_count < 50:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            'status': status,
            'metrics': metrics,
            'queue_status': queue_status,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }