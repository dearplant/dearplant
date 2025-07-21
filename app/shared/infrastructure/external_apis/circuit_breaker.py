# 📄 File: app/shared/infrastructure/external_apis/circuit_breaker.py
# 🧭 Purpose (Layman Explanation): 
# This file acts like an electrical circuit breaker for API calls - when an external service fails too many times,
# it "trips" and stops trying for a while to prevent overwhelming the failing service and wasting resources.
# 🧪 Purpose (Technical Summary): 
# Implements the Circuit Breaker pattern for external API resilience, providing automatic failure detection,
# service isolation, and recovery mechanisms to prevent cascade failures and improve system stability.
# 🔗 Dependencies: 
# asyncio, time, enum, typing, dataclasses, threading, logging
# 🔄 Connected Modules / Calls From: 
# api_client.py, api_rotation.py, all external API clients, health monitoring, metrics collection

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from dataclasses import dataclass, field
from threading import Lock
import logging
from datetime import datetime, timedelta
import statistics
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation, requests flow through
    OPEN = "open"           # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open" # Testing if service recovered


class FailureType(Enum):
    """Types of failures that can trigger circuit breaker"""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """Record of a failure occurrence"""
    timestamp: float
    failure_type: FailureType
    error_message: str
    response_time: Optional[float] = None
    status_code: Optional[int] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    # Failure threshold
    failure_threshold: int = 5
    failure_rate_threshold: float = 0.5  # 50% failure rate
    
    # Time windows
    failure_window_seconds: int = 60
    recovery_timeout_seconds: int = 60
    
    # Half-open state testing
    half_open_max_calls: int = 3
    
    # Response time monitoring
    slow_call_threshold_seconds: float = 10.0
    slow_call_rate_threshold: float = 0.5
    
    # Minimum calls for rate calculation
    minimum_calls_threshold: int = 10
    
    # Expected exceptions that should trigger the circuit breaker
    expected_exceptions: List[type] = field(default_factory=lambda: [
        ConnectionError, TimeoutError, OSError
    ])


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, message: str, circuit_name: str, state: CircuitState):
        self.circuit_name = circuit_name
        self.state = state
        super().__init__(message)


class CircuitBreakerMetrics:
    """Metrics collector for circuit breaker performance"""
    
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.call_records = deque(maxlen=max_records)
        self.failure_records = deque(maxlen=max_records)
        self.state_changes = deque(maxlen=100)
        self._lock = Lock()
    
    def record_call(self, success: bool, response_time: float, 
                   failure_type: Optional[FailureType] = None):
        """Record a call attempt"""
        with self._lock:
            record = {
                'timestamp': time.time(),
                'success': success,
                'response_time': response_time,
                'failure_type': failure_type
            }
            self.call_records.append(record)
    
    def record_failure(self, failure_record: FailureRecord):
        """Record a failure occurrence"""
        with self._lock:
            self.failure_records.append(failure_record)
    
    def record_state_change(self, old_state: CircuitState, new_state: CircuitState, reason: str):
        """Record a state change"""
        with self._lock:
            self.state_changes.append({
                'timestamp': time.time(),
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason
            })
    
    def get_failure_rate(self, window_seconds: int) -> float:
        """Calculate failure rate in the given time window"""
        with self._lock:
            cutoff_time = time.time() - window_seconds
            recent_calls = [r for r in self.call_records if r['timestamp'] > cutoff_time]
            
            if not recent_calls:
                return 0.0
            
            failed_calls = sum(1 for r in recent_calls if not r['success'])
            return failed_calls / len(recent_calls)
    
    def get_slow_call_rate(self, window_seconds: int, threshold_seconds: float) -> float:
        """Calculate slow call rate in the given time window"""
        with self._lock:
            cutoff_time = time.time() - window_seconds
            recent_calls = [r for r in self.call_records if r['timestamp'] > cutoff_time]
            
            if not recent_calls:
                return 0.0
            
            slow_calls = sum(1 for r in recent_calls if r['response_time'] > threshold_seconds)
            return slow_calls / len(recent_calls)
    
    def get_recent_failures(self, window_seconds: int) -> List[FailureRecord]:
        """Get failures in the recent time window"""
        with self._lock:
            cutoff_time = time.time() - window_seconds
            return [r for r in self.failure_records if r.timestamp > cutoff_time]
    
    def get_call_count(self, window_seconds: int) -> int:
        """Get total call count in the time window"""
        with self._lock:
            cutoff_time = time.time() - window_seconds
            return sum(1 for r in self.call_records if r['timestamp'] > cutoff_time)
    
    def get_average_response_time(self, window_seconds: int) -> float:
        """Get average response time in the time window"""
        with self._lock:
            cutoff_time = time.time() - window_seconds
            recent_calls = [r for r in self.call_records if r['timestamp'] > cutoff_time]
            
            if not recent_calls:
                return 0.0
            
            response_times = [r['response_time'] for r in recent_calls if r['response_time'] is not None]
            return statistics.mean(response_times) if response_times else 0.0


class CircuitBreaker:
    """
    Circuit breaker implementation for external API resilience
    
    Implements the three states: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0.0
        self.last_state_change_time = time.time()
        self.half_open_call_count = 0
        self.half_open_success_count = 0
        self.metrics = CircuitBreakerMetrics()
        self._lock = Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized in CLOSED state")
    
    def _should_trip(self) -> bool:
        """Check if circuit breaker should trip to OPEN state"""
        failure_rate = self.metrics.get_failure_rate(self.config.failure_window_seconds)
        call_count = self.metrics.get_call_count(self.config.failure_window_seconds)
        
        # Need minimum calls to calculate failure rate
        if call_count < self.config.minimum_calls_threshold:
            return False
        
        # Check failure rate threshold
        if failure_rate >= self.config.failure_rate_threshold:
            return True
        
        # Check slow call rate
        slow_call_rate = self.metrics.get_slow_call_rate(
            self.config.failure_window_seconds,
            self.config.slow_call_threshold_seconds
        )
        
        if slow_call_rate >= self.config.slow_call_rate_threshold:
            return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset to HALF_OPEN"""
        time_since_open = time.time() - self.last_state_change_time
        return time_since_open >= self.config.recovery_timeout_seconds
    
    def _transition_to_state(self, new_state: CircuitState, reason: str):
        """Transition circuit breaker to new state"""
        old_state = self.state
        self.state = new_state
        self.last_state_change_time = time.time()
        
        if new_state == CircuitState.HALF_OPEN:
            self.half_open_call_count = 0
            self.half_open_success_count = 0
        
        self.metrics.record_state_change(old_state, new_state, reason)
        
        logger.info(f"Circuit breaker '{self.name}' transitioned from {old_state.value} to {new_state.value}: {reason}")
    
    def _record_success(self, response_time: float):
        """Record a successful call"""
        self.metrics.record_call(True, response_time)
        
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_success_count += 1
                self.half_open_call_count += 1
                
                # If we've had enough successful calls, close the circuit
                if self.half_open_success_count >= self.config.half_open_max_calls:
                    self._transition_to_state(CircuitState.CLOSED, "Successful recovery verified")
            
            elif self.state == CircuitState.CLOSED:
                # Check if we should trip due to accumulated failures
                if self._should_trip():
                    self._transition_to_state(CircuitState.OPEN, "Failure threshold exceeded")
    
    def _record_failure(self, failure_type: FailureType, error_message: str, 
                       response_time: Optional[float] = None, status_code: Optional[int] = None):
        """Record a failed call"""
        failure_record = FailureRecord(
            timestamp=time.time(),
            failure_type=failure_type,
            error_message=error_message,
            response_time=response_time,
            status_code=status_code
        )
        
        self.metrics.record_call(False, response_time or 0.0, failure_type)
        self.metrics.record_failure(failure_record)
        self.last_failure_time = time.time()
        
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state trips the circuit
                self._transition_to_state(CircuitState.OPEN, f"Failure during recovery test: {failure_type.value}")
            
            elif self.state == CircuitState.CLOSED:
                # Check if we should trip
                if self._should_trip():
                    self._transition_to_state(CircuitState.OPEN, f"Failure threshold exceeded: {failure_type.value}")
    
    def _get_failure_type(self, exception: Exception) -> FailureType:
        """Determine failure type from exception"""
        if isinstance(exception, TimeoutError):
            return FailureType.TIMEOUT
        elif isinstance(exception, ConnectionError):
            return FailureType.CONNECTION_ERROR
        elif hasattr(exception, 'status_code'):
            status_code = getattr(exception, 'status_code')
            if status_code == 429:
                return FailureType.RATE_LIMIT
            elif status_code >= 500:
                return FailureType.SERVICE_UNAVAILABLE
            else:
                return FailureType.HTTP_ERROR
        else:
            return FailureType.UNKNOWN
    
    def _is_expected_exception(self, exception: Exception) -> bool:
        """Check if exception should trigger circuit breaker"""
        return any(isinstance(exception, exc_type) for exc_type in self.config.expected_exceptions)
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerException: When circuit is open
            Original exception: When call fails
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN and self._should_attempt_reset():
                self._transition_to_state(CircuitState.HALF_OPEN, "Attempting recovery")
            
            # Fail fast if circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerException(
                    f"Circuit breaker '{self.name}' is OPEN. Last failure: {datetime.fromtimestamp(self.last_failure_time)}",
                    self.name,
                    CircuitState.OPEN
                )
            
            # Limit calls in half-open state
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_call_count >= self.config.half_open_max_calls:
                    raise CircuitBreakerException(
                        f"Circuit breaker '{self.name}' is HALF_OPEN and max test calls exceeded",
                        self.name,
                        CircuitState.HALF_OPEN
                    )
                self.half_open_call_count += 1
        
        # Execute the function call
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            response_time = time.time() - start_time
            self._record_success(response_time)
            return result
        
        except Exception as e:
            response_time = time.time() - start_time
            
            # Only record failure for expected exceptions
            if self._is_expected_exception(e):
                failure_type = self._get_failure_type(e)
                status_code = getattr(e, 'status_code', None)
                self._record_failure(failure_type, str(e), response_time, status_code)
            else:
                # For unexpected exceptions, still record the call but don't trigger circuit breaker
                self.metrics.record_call(False, response_time)
            
            raise
    
    def call_sync(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute a synchronous function call through the circuit breaker
        
        Args:
            func: Synchronous function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerException: When circuit is open
            Original exception: When call fails
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN and self._should_attempt_reset():
                self._transition_to_state(CircuitState.HALF_OPEN, "Attempting recovery")
            
            # Fail fast if circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerException(
                    f"Circuit breaker '{self.name}' is OPEN. Last failure: {datetime.fromtimestamp(self.last_failure_time)}",
                    self.name,
                    CircuitState.OPEN
                )
            
            # Limit calls in half-open state
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_call_count >= self.config.half_open_max_calls:
                    raise CircuitBreakerException(
                        f"Circuit breaker '{self.name}' is HALF_OPEN and max test calls exceeded",
                        self.name,
                        CircuitState.HALF_OPEN
                    )
                self.half_open_call_count += 1
        
        # Execute the function call
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            response_time = time.time() - start_time
            self._record_success(response_time)
            return result
        
        except Exception as e:
            response_time = time.time() - start_time
            
            # Only record failure for expected exceptions
            if self._is_expected_exception(e):
                failure_type = self._get_failure_type(e)
                status_code = getattr(e, 'status_code', None)
                self._record_failure(failure_type, str(e), response_time, status_code)
            else:
                # For unexpected exceptions, still record the call but don't trigger circuit breaker
                self.metrics.record_call(False, response_time)
            
            raise
    
    def force_open(self, reason: str = "Manually opened"):
        """Manually force circuit breaker to OPEN state"""
        with self._lock:
            self._transition_to_state(CircuitState.OPEN, reason)
    
    def force_close(self, reason: str = "Manually closed"):
        """Manually force circuit breaker to CLOSED state"""
        with self._lock:
            self._transition_to_state(CircuitState.CLOSED, reason)
    
    def force_half_open(self, reason: str = "Manually set to half-open"):
        """Manually force circuit breaker to HALF_OPEN state"""
        with self._lock:
            self._transition_to_state(CircuitState.HALF_OPEN, reason)
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics and statistics"""
        with self._lock:
            return {
                'name': self.name,
                'state': self.state.value,
                'last_state_change': datetime.fromtimestamp(self.last_state_change_time).isoformat(),
                'last_failure_time': datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None,
                'failure_rate': self.metrics.get_failure_rate(self.config.failure_window_seconds),
                'slow_call_rate': self.metrics.get_slow_call_rate(
                    self.config.failure_window_seconds,
                    self.config.slow_call_threshold_seconds
                ),
                'recent_call_count': self.metrics.get_call_count(self.config.failure_window_seconds),
                'average_response_time': self.metrics.get_average_response_time(self.config.failure_window_seconds),
                'recent_failures': len(self.metrics.get_recent_failures(self.config.failure_window_seconds)),
                'half_open_calls': self.half_open_call_count if self.state == CircuitState.HALF_OPEN else 0,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'failure_rate_threshold': self.config.failure_rate_threshold,
                    'failure_window_seconds': self.config.failure_window_seconds,
                    'recovery_timeout_seconds': self.config.recovery_timeout_seconds,
                    'half_open_max_calls': self.config.half_open_max_calls
                }
            }
    
    def reset_metrics(self):
        """Reset all metrics and statistics"""
        with self._lock:
            self.metrics = CircuitBreakerMetrics()
            logger.info(f"Circuit breaker '{self.name}' metrics reset")


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker by name
        
        Args:
            name: Circuit breaker name
            config: Configuration (optional)
            
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(name, config)
            return self.circuit_breakers[name]
    
    def remove_circuit_breaker(self, name: str) -> bool:
        """
        Remove a circuit breaker
        
        Args:
            name: Circuit breaker name
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self.circuit_breakers:
                del self.circuit_breakers[name]
                return True
            return False
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        with self._lock:
            return {name: cb.get_metrics() for name, cb in self.circuit_breakers.items()}
    
    def get_healthy_circuits(self) -> List[str]:
        """Get names of healthy (CLOSED) circuit breakers"""
        with self._lock:
            return [name for name, cb in self.circuit_breakers.items() 
                   if cb.get_state() == CircuitState.CLOSED]
    
    def get_unhealthy_circuits(self) -> List[str]:
        """Get names of unhealthy (OPEN/HALF_OPEN) circuit breakers"""
        with self._lock:
            return [name for name, cb in self.circuit_breakers.items() 
                   if cb.get_state() != CircuitState.CLOSED]
    
    def force_close_all(self, reason: str = "Bulk close operation"):
        """Force all circuit breakers to CLOSED state"""
        with self._lock:
            for cb in self.circuit_breakers.values():
                cb.force_close(reason)
    
    def reset_all_metrics(self):
        """Reset metrics for all circuit breakers"""
        with self._lock:
            for cb in self.circuit_breakers.values():
                cb.reset_metrics()


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for applying circuit breaker pattern to functions
    
    Args:
        name: Circuit breaker name
        config: Configuration (optional)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        cb = circuit_breaker_manager.get_circuit_breaker(name, config)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await cb.call(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return cb.call_sync(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


# Helper functions for common use cases
def create_api_circuit_breaker(api_name: str, 
                              failure_threshold: int = 5,
                              recovery_timeout: int = 60) -> CircuitBreaker:
    """
    Create a circuit breaker configured for API calls
    
    Args:
        api_name: API service name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before retry
        
    Returns:
        Configured CircuitBreaker
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        failure_rate_threshold=0.5,
        failure_window_seconds=60,
        recovery_timeout_seconds=recovery_timeout,
        half_open_max_calls=3,
        slow_call_threshold_seconds=10.0,
        minimum_calls_threshold=5
    )
    
    return circuit_breaker_manager.get_circuit_breaker(f"api_{api_name}", config)


def create_database_circuit_breaker(db_name: str) -> CircuitBreaker:
    """
    Create a circuit breaker configured for database calls
    
    Args:
        db_name: Database name
        
    Returns:
        Configured CircuitBreaker
    """
    config = CircuitBreakerConfig(
        failure_threshold=3,
        failure_rate_threshold=0.3,
        failure_window_seconds=30,
        recovery_timeout_seconds=30,
        half_open_max_calls=2,
        slow_call_threshold_seconds=5.0,
        minimum_calls_threshold=3
    )
    
    return circuit_breaker_manager.get_circuit_breaker(f"db_{db_name}", config)