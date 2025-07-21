# 📄 File: app/shared/events/handlers.py
# 🧭 Purpose (Layman Explanation): 
# This file contains event handlers that listen for important things happening in the app (like when a plant is added or watered)
# and automatically trigger other actions (like sending notifications or updating analytics).
# 🧪 Purpose (Technical Summary): 
# Implements event handler implementations for domain events, providing decoupled communication between modules
# through publish-subscribe pattern with async processing and error handling.
# 🔗 Dependencies: 
# base.py, publisher.py, typing, asyncio, logging, datetime, traceback
# 🔄 Connected Modules / Calls From: 
# All domain modules, notification system, analytics system, audit logging, integration services

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Callable, Awaitable, Union
from datetime import datetime, timedelta
import traceback
import inspect
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque
import weakref

from .base import DomainEvent, EventHandler, EventHandlerRegistry

logger = logging.getLogger(__name__)


class HandlerPriority(Enum):
    """Event handler execution priority levels"""
    CRITICAL = 1    # Must execute immediately (e.g., security events)
    HIGH = 2        # Important but can tolerate slight delay (e.g., notifications)
    NORMAL = 3      # Standard business logic (e.g., analytics updates)
    LOW = 4         # Background processing (e.g., data cleanup)


class HandlerExecutionMode(Enum):
    """Event handler execution modes"""
    SYNC = "sync"           # Execute synchronously in order
    ASYNC = "async"         # Execute asynchronously in parallel
    BACKGROUND = "background"  # Execute in background task


@dataclass
class HandlerMetadata:
    """Metadata for event handlers"""
    name: str
    priority: HandlerPriority = HandlerPriority.NORMAL
    execution_mode: HandlerExecutionMode = HandlerExecutionMode.ASYNC
    retry_count: int = 3
    timeout_seconds: float = 30.0
    ignore_errors: bool = False
    required_permissions: List[str] = field(default_factory=list)
    rate_limit_per_minute: Optional[int] = None
    
    # Handler state tracking
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    last_execution: Optional[datetime] = None
    last_error: Optional[str] = None
    average_execution_time: float = 0.0


@dataclass
class HandlerExecutionResult:
    """Result of handler execution"""
    handler_name: str
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0


class EventHandlerError(Exception):
    """Base exception for event handler errors"""
    def __init__(self, message: str, handler_name: str, event_type: str):
        self.handler_name = handler_name
        self.event_type = event_type
        super().__init__(message)


class HandlerTimeoutError(EventHandlerError):
    """Exception raised when handler execution times out"""
    pass


class HandlerRateLimitError(EventHandlerError):
    """Exception raised when handler rate limit is exceeded"""
    pass


class AsyncEventHandler(EventHandler):
    """
    Enhanced event handler with async support and advanced features
    """
    
    def __init__(self, 
                 handler_func: Callable[[DomainEvent], Awaitable[Any]],
                 metadata: Optional[HandlerMetadata] = None):
        self.handler_func = handler_func
        self.metadata = metadata or HandlerMetadata(
            name=getattr(handler_func, '__name__', 'unknown_handler')
        )
        self.execution_history = deque(maxlen=100)
        self._rate_limit_calls = deque(maxlen=1000)
        
        # Ensure handler function is async
        if not asyncio.iscoroutinefunction(handler_func):
            # Wrap sync function to make it async
            async def async_wrapper(event: DomainEvent) -> Any:
                return handler_func(event)
            self.handler_func = async_wrapper
    
    async def handle(self, event: DomainEvent) -> HandlerExecutionResult:
        """
        Handle domain event with full error handling and metrics
        
        Args:
            event: Domain event to handle
            
        Returns:
            HandlerExecutionResult with execution details
        """
        start_time = datetime.now()
        result = HandlerExecutionResult(
            handler_name=self.metadata.name,
            success=False,
            execution_time=0.0
        )
        
        try:
            # Check rate limiting
            self._check_rate_limit()
            
            # Execute handler with timeout
            await asyncio.wait_for(
                self._execute_with_retry(event),
                timeout=self.metadata.timeout_seconds
            )
            
            result.success = True
            self.metadata.successful_executions += 1
            
        except asyncio.TimeoutError:
            error_msg = f"Handler '{self.metadata.name}' timed out after {self.metadata.timeout_seconds}s"
            result.error_message = error_msg
            result.error_type = "TimeoutError"
            self.metadata.failed_executions += 1
            self.metadata.last_error = error_msg
            
            if not self.metadata.ignore_errors:
                logger.error(f"Handler timeout: {error_msg}")
            
        except HandlerRateLimitError as e:
            result.error_message = str(e)
            result.error_type = "RateLimitError"
            self.metadata.failed_executions += 1
            self.metadata.last_error = str(e)
            
            if not self.metadata.ignore_errors:
                logger.warning(f"Handler rate limited: {e}")
            
        except Exception as e:
            error_msg = f"Handler '{self.metadata.name}' failed: {str(e)}"
            result.error_message = error_msg
            result.error_type = type(e).__name__
            self.metadata.failed_executions += 1
            self.metadata.last_error = error_msg
            
            if not self.metadata.ignore_errors:
                logger.error(f"Handler error: {error_msg}\n{traceback.format_exc()}")
        
        finally:
            # Update metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            self.metadata.total_executions += 1
            self.metadata.last_execution = start_time
            
            # Update average execution time
            if self.metadata.total_executions == 1:
                self.metadata.average_execution_time = execution_time
            else:
                # Exponential moving average
                alpha = 0.1
                self.metadata.average_execution_time = (
                    alpha * execution_time + 
                    (1 - alpha) * self.metadata.average_execution_time
                )
            
            # Record execution history
            self.execution_history.append({
                'timestamp': start_time,
                'execution_time': execution_time,
                'success': result.success,
                'error_type': result.error_type
            })
        
        return result
    
    async def _execute_with_retry(self, event: DomainEvent) -> Any:
        """Execute handler with retry logic"""
        last_exception = None
        
        for attempt in range(self.metadata.retry_count + 1):
            try:
                return await self.handler_func(event)
            except Exception as e:
                last_exception = e
                if attempt < self.metadata.retry_count:
                    # Exponential backoff for retries
                    delay = min(2 ** attempt, 30)  # Max 30 seconds
                    await asyncio.sleep(delay)
                    logger.warning(f"Handler '{self.metadata.name}' retry {attempt + 1}/{self.metadata.retry_count} after error: {e}")
        
        raise last_exception
    
    def _check_rate_limit(self):
        """Check if handler rate limit is exceeded"""
        if self.metadata.rate_limit_per_minute is None:
            return
        
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old calls
        while self._rate_limit_calls and self._rate_limit_calls[0] < minute_ago:
            self._rate_limit_calls.popleft()
        
        # Check rate limit
        if len(self._rate_limit_calls) >= self.metadata.rate_limit_per_minute:
            raise HandlerRateLimitError(
                f"Rate limit exceeded for handler '{self.metadata.name}' "
                f"({self.metadata.rate_limit_per_minute} calls/minute)",
                self.metadata.name,
                "rate_limit"
            )
        
        # Record this call
        self._rate_limit_calls.append(now)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get handler performance metrics"""
        success_rate = (
            self.metadata.successful_executions / self.metadata.total_executions
            if self.metadata.total_executions > 0 else 0
        )
        
        return {
            'name': self.metadata.name,
            'priority': self.metadata.priority.name,
            'execution_mode': self.metadata.execution_mode.value,
            'total_executions': self.metadata.total_executions,
            'successful_executions': self.metadata.successful_executions,
            'failed_executions': self.metadata.failed_executions,
            'success_rate': success_rate,
            'average_execution_time': self.metadata.average_execution_time,
            'last_execution': self.metadata.last_execution.isoformat() if self.metadata.last_execution else None,
            'last_error': self.metadata.last_error,
            'rate_limit_per_minute': self.metadata.rate_limit_per_minute,
            'recent_executions': list(self.execution_history)[-10:]  # Last 10 executions
        }


class EnhancedEventHandlerRegistry(EventHandlerRegistry):
    """
    Enhanced event handler registry with priority handling and execution modes
    """
    
    def __init__(self):
        super().__init__()
        self.handler_metadata: Dict[str, HandlerMetadata] = {}
        self.execution_results: Dict[str, List[HandlerExecutionResult]] = defaultdict(list)
        self.background_tasks: List[asyncio.Task] = []
        
    def register(self, 
                 event_type: Type[DomainEvent], 
                 handler: Union[EventHandler, Callable],
                 metadata: Optional[HandlerMetadata] = None) -> str:
        """
        Register an event handler with metadata
        
        Args:
            event_type: Type of event to handle
            handler: Handler function or EventHandler instance
            metadata: Handler metadata
            
        Returns:
            Handler ID for tracking
        """
        # Convert function to AsyncEventHandler if needed
        if not isinstance(handler, EventHandler):
            if metadata is None:
                metadata = HandlerMetadata(
                    name=getattr(handler, '__name__', 'unknown_handler')
                )
            handler = AsyncEventHandler(handler, metadata)
        
        # Register handler
        handler_id = super().register(event_type, handler)
        
        # Store metadata
        if isinstance(handler, AsyncEventHandler):
            self.handler_metadata[handler_id] = handler.metadata
        
        logger.info(f"Registered event handler '{handler_id}' for {event_type.__name__}")
        return handler_id
    
    def unregister(self, event_type: Type[DomainEvent], handler_id: str) -> bool:
        """
        Unregister an event handler
        
        Args:
            event_type: Event type
            handler_id: Handler ID
            
        Returns:
            True if unregistered successfully
        """
        success = super().unregister(event_type, handler_id)
        
        if success and handler_id in self.handler_metadata:
            del self.handler_metadata[handler_id]
            if handler_id in self.execution_results:
                del self.execution_results[handler_id]
        
        return success
    
    async def publish(self, event: DomainEvent) -> Dict[str, HandlerExecutionResult]:
        """
        Publish event to all registered handlers
        
        Args:
            event: Domain event to publish
            
        Returns:
            Dictionary of handler results keyed by handler ID
        """
        event_type = type(event)
        handlers = self.get_handlers(event_type)
        
        if not handlers:
            logger.debug(f"No handlers registered for event type: {event_type.__name__}")
            return {}
        
        logger.info(f"Publishing event {event_type.__name__} to {len(handlers)} handlers")
        
        # Group handlers by execution mode and priority
        sync_handlers = []
        async_handlers = []
        background_handlers = []
        
        for handler_id, handler in handlers.items():
            if isinstance(handler, AsyncEventHandler):
                mode = handler.metadata.execution_mode
                priority = handler.metadata.priority
                
                handler_info = (priority.value, handler_id, handler)
                
                if mode == HandlerExecutionMode.SYNC:
                    sync_handlers.append(handler_info)
                elif mode == HandlerExecutionMode.ASYNC:
                    async_handlers.append(handler_info)
                else:  # BACKGROUND
                    background_handlers.append(handler_info)
            else:
                # Default to async for non-AsyncEventHandler
                async_handlers.append((HandlerPriority.NORMAL.value, handler_id, handler))
        
        # Sort by priority (lower number = higher priority)
        sync_handlers.sort(key=lambda x: x[0])
        async_handlers.sort(key=lambda x: x[0])
        background_handlers.sort(key=lambda x: x[0])
        
        results = {}
        
        # Execute synchronous handlers first (in priority order)
        for _, handler_id, handler in sync_handlers:
            try:
                if isinstance(handler, AsyncEventHandler):
                    result = await handler.handle(event)
                else:
                    # Legacy handler support
                    start_time = datetime.now()
                    await handler.handle(event)
                    execution_time = (datetime.now() - start_time).total_seconds()
                    result = HandlerExecutionResult(
                        handler_name=handler_id,
                        success=True,
                        execution_time=execution_time
                    )
                
                results[handler_id] = result
                self.execution_results[handler_id].append(result)
                
            except Exception as e:
                error_result = HandlerExecutionResult(
                    handler_name=handler_id,
                    success=False,
                    execution_time=0.0,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                results[handler_id] = error_result
                self.execution_results[handler_id].append(error_result)
                logger.error(f"Sync handler '{handler_id}' failed: {e}")
        
        # Execute asynchronous handlers in parallel
        if async_handlers:
            async_tasks = []
            for _, handler_id, handler in async_handlers:
                if isinstance(handler, AsyncEventHandler):
                    task = asyncio.create_task(handler.handle(event))
                else:
                    # Legacy handler support
                    async def legacy_wrapper(h=handler, hid=handler_id):
                        start_time = datetime.now()
                        try:
                            await h.handle(event)
                            execution_time = (datetime.now() - start_time).total_seconds()
                            return HandlerExecutionResult(
                                handler_name=hid,
                                success=True,
                                execution_time=execution_time
                            )
                        except Exception as e:
                            return HandlerExecutionResult(
                                handler_name=hid,
                                success=False,
                                execution_time=0.0,
                                error_message=str(e),
                                error_type=type(e).__name__
                            )
                    task = asyncio.create_task(legacy_wrapper())
                
                async_tasks.append((handler_id, task))
            
            # Wait for all async handlers to complete
            for handler_id, task in async_tasks:
                try:
                    result = await task
                    results[handler_id] = result
                    self.execution_results[handler_id].append(result)
                except Exception as e:
                    error_result = HandlerExecutionResult(
                        handler_name=handler_id,
                        success=False,
                        execution_time=0.0,
                        error_message=str(e),
                        error_type=type(e).__name__
                    )
                    results[handler_id] = error_result
                    self.execution_results[handler_id].append(error_result)
                    logger.error(f"Async handler '{handler_id}' failed: {e}")
        
        # Execute background handlers (fire and forget)
        for _, handler_id, handler in background_handlers:
            if isinstance(handler, AsyncEventHandler):
                task = asyncio.create_task(self._execute_background_handler(handler_id, handler, event))
            else:
                # Legacy handler support
                async def legacy_background_wrapper():
                    try:
                        await handler.handle(event)
                        logger.debug(f"Background handler '{handler_id}' completed")
                    except Exception as e:
                        logger.error(f"Background handler '{handler_id}' failed: {e}")
                
                task = asyncio.create_task(legacy_background_wrapper())
            
            self.background_tasks.append(task)
            
            # Clean up completed background tasks
            self.background_tasks = [t for t in self.background_tasks if not t.done()]
        
        # Log execution summary
        successful_count = sum(1 for r in results.values() if r.success)
        total_count = len(results)
        
        logger.info(f"Event {event_type.__name__} published: {successful_count}/{total_count} handlers succeeded")
        
        return results
    
    async def _execute_background_handler(self, handler_id: str, handler: AsyncEventHandler, event: DomainEvent):
        """Execute background handler with result tracking"""
        try:
            result = await handler.handle(event)
            self.execution_results[handler_id].append(result)
            logger.debug(f"Background handler '{handler_id}' completed successfully")
        except Exception as e:
            error_result = HandlerExecutionResult(
                handler_name=handler_id,
                success=False,
                execution_time=0.0,
                error_message=str(e),
                error_type=type(e).__name__
            )
            self.execution_results[handler_id].append(error_result)
            logger.error(f"Background handler '{handler_id}' failed: {e}")
    
    def get_handler_metrics(self, handler_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics for handlers
        
        Args:
            handler_id: Specific handler ID (optional)
            
        Returns:
            Handler metrics
        """
        if handler_id:
            # Get metrics for specific handler
            if handler_id in self.handler_metadata:
                metadata = self.handler_metadata[handler_id]
                # Find the actual handler to get detailed metrics
                for event_type, handlers in self.handlers.items():
                    if handler_id in handlers and isinstance(handlers[handler_id], AsyncEventHandler):
                        return handlers[handler_id].get_metrics()
                
                # Fallback to basic metadata
                return {
                    'name': metadata.name,
                    'total_executions': metadata.total_executions,
                    'successful_executions': metadata.successful_executions,
                    'failed_executions': metadata.failed_executions
                }
            return {}
        else:
            # Get metrics for all handlers
            all_metrics = {}
            for event_type, handlers in self.handlers.items():
                for hid, handler in handlers.items():
                    if isinstance(handler, AsyncEventHandler):
                        all_metrics[hid] = handler.get_metrics()
                    elif hid in self.handler_metadata:
                        metadata = self.handler_metadata[hid]
                        all_metrics[hid] = {
                            'name': metadata.name,
                            'total_executions': metadata.total_executions,
                            'successful_executions': metadata.successful_executions,
                            'failed_executions': metadata.failed_executions
                        }
            
            return all_metrics
    
    def get_execution_history(self, handler_id: str, limit: int = 50) -> List[HandlerExecutionResult]:
        """
        Get execution history for a handler
        
        Args:
            handler_id: Handler ID
            limit: Maximum number of results
            
        Returns:
            List of execution results
        """
        if handler_id in self.execution_results:
            return list(self.execution_results[handler_id])[-limit:]
        return []
    
    def cleanup_background_tasks(self):
        """Clean up completed background tasks"""
        self.background_tasks = [t for t in self.background_tasks if not t.done()]
    
    async def shutdown(self):
        """Shutdown registry and wait for background tasks"""
        logger.info("Shutting down event handler registry...")
        
        # Wait for background tasks to complete (with timeout)
        if self.background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some background tasks did not complete within shutdown timeout")
        
        logger.info("Event handler registry shutdown complete")


# Decorator for registering event handlers
def event_handler(event_type: Type[DomainEvent], 
                 priority: HandlerPriority = HandlerPriority.NORMAL,
                 execution_mode: HandlerExecutionMode = HandlerExecutionMode.ASYNC,
                 retry_count: int = 3,
                 timeout_seconds: float = 30.0,
                 ignore_errors: bool = False,
                 rate_limit_per_minute: Optional[int] = None):
    """
    Decorator for registering event handlers
    
    Args:
        event_type: Type of event to handle
        priority: Handler execution priority
        execution_mode: Handler execution mode
        retry_count: Number of retries on failure
        timeout_seconds: Handler timeout
        ignore_errors: Whether to ignore handler errors
        rate_limit_per_minute: Rate limit for handler execution
        
    Returns:
        Decorated function
    """
    def decorator(func):
        # Store metadata on function for later registration
        func._event_handler_metadata = HandlerMetadata(
            name=func.__name__,
            priority=priority,
            execution_mode=execution_mode,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
            ignore_errors=ignore_errors,
            rate_limit_per_minute=rate_limit_per_minute
        )
        func._event_type = event_type
        
        return func
    
    return decorator


# Global enhanced registry instance
enhanced_event_registry = EnhancedEventHandlerRegistry()


# Helper functions for common handler patterns
async def create_notification_handler(event: DomainEvent) -> None:
    """Template for notification handlers"""
    logger.info(f"Notification handler triggered by {type(event).__name__}")
    # Implementation would integrate with notification system
    pass


async def create_analytics_handler(event: DomainEvent) -> None:
    """Template for analytics handlers"""
    logger.info(f"Analytics handler triggered by {type(event).__name__}")
    # Implementation would integrate with analytics system
    pass


async def create_audit_handler(event: DomainEvent) -> None:
    """Template for audit log handlers"""
    logger.info(f"Audit handler triggered by {type(event).__name__}")
    # Implementation would integrate with audit logging system
    pass


# Utility functions for handler management
def register_handlers_from_module(module, registry: Optional[EnhancedEventHandlerRegistry] = None):
    """
    Register all decorated handlers from a module
    
    Args:
        module: Python module containing decorated handlers
        registry: Registry to use (defaults to global registry)
    """
    if registry is None:
        registry = enhanced_event_registry
    
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and hasattr(obj, '_event_handler_metadata'):
            event_type = obj._event_type
            metadata = obj._event_handler_metadata
            registry.register(event_type, obj, metadata)
            logger.info(f"Auto-registered handler '{name}' for {event_type.__name__}")


def create_handler_health_check() -> Dict[str, Any]:
    """
    Create health check information for event handlers
    
    Returns:
        Health check data
    """
    metrics = enhanced_event_registry.get_handler_metrics()
    
    total_handlers = len(metrics)
    healthy_handlers = 0
    failing_handlers = []
    
    for handler_id, handler_metrics in metrics.items():
        total_executions = handler_metrics.get('total_executions', 0)
        success_rate = handler_metrics.get('success_rate', 1.0)
        
        if total_executions == 0 or success_rate >= 0.9:  # 90% success rate threshold
            healthy_handlers += 1
        else:
            failing_handlers.append({
                'handler_id': handler_id,
                'success_rate': success_rate,
                'total_executions': total_executions,
                'last_error': handler_metrics.get('last_error')
            })
    
    return {
        'status': 'healthy' if len(failing_handlers) == 0 else 'degraded',
        'total_handlers': total_handlers,
        'healthy_handlers': healthy_handlers,
        'failing_handlers': failing_handlers,
        'background_tasks': len(enhanced_event_registry.background_tasks),
        'timestamp': datetime.now().isoformat()
    }