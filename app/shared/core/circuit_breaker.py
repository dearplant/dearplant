"""
Circuit breaker implementation for Plant Care Application.
Prevents cascading failures when external services are unavailable.
"""

import logging
import time
from enum import Enum
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
from functools import wraps
import asyncio
from datetime import datetime, timedelta

from .exceptions import CircuitBreakerError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back, limited requests


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5           # Number of failures to open circuit
    recovery_timeout: int = 60           # Seconds to wait before trying again
    success_threshold: int = 3           # Successes needed to close circuit in half-open
    timeout: int = 30                    # Request timeout in seconds
    expected_exception: type = Exception # Exception type that triggers circuit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "expected_exception": self.expected_exception.__name__
        }


class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.state_changes: list = []
        self.created_at = datetime.utcnow()
    
    def record_success(self):
        """Record a successful request."""
        self.success_count += 1
        self.total_requests += 1
        self.last_success_time = datetime.utcnow()
    
    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.total_requests += 1
        self.last_failure_time = datetime.utcnow()
    
    def record_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState):
        """Record state transition."""
        self.state_changes.append({
            "timestamp": datetime.utcnow().isoformat(),
            "from_state": old_state.value,
            "to_state": new_state.value
        })
    
    def get_failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failure_count / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "failure_rate": self.get_failure_rate(),
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "uptime_seconds": int((datetime.utcnow() - self.created_at).total_seconds()),
            "state_changes": len(self.state_changes)
        }


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    Implements the circuit breaker pattern to prevent cascading failures.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats()
        self.last_failure_time: Optional[float] = None
        self.half_open_successes = 0
        self._lock = asyncio.Lock()
    
    async def __call__(self, func: Callable[..., T]) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            
        Returns:
            T: Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        await self._check_state()
        
        if self.state == CircuitBreakerState.OPEN:
            logger.warning(f"Circuit breaker '{self.name}' is OPEN - failing fast")
            raise CircuitBreakerError(
                message=f"Service '{self.name}' is temporarily unavailable",
                service_name=self.name,
                failure_count=self.stats.failure_count,
                reset_time=int(self.config.recovery_timeout - (time.time() - (self.last_failure_time or 0)))
            )
        
        try:
            # Execute function with timeout
            result = await asyncio.wait_for(func(), timeout=self.config.timeout)
            await self._on_success()
            return result
            
        except asyncio.TimeoutError as e:
            logger.warning(f"Circuit breaker '{self.name}' - request timeout")
            await self._on_failure()
            raise CircuitBreakerError(f"Request timeout for service '{self.name}'")
            
        except self.config.expected_exception as e:
            logger.warning(f"Circuit breaker '{self.name}' - expected failure: {e}")
            await self._on_failure()
            raise
            
        except Exception as e:
            logger.error(f"Circuit breaker '{self.name}' - unexpected error: {e}")
            await self._on_failure()
            raise
    
    async def _check_state(self):
        """Check and potentially update circuit breaker state."""
        async with self._lock:
            current_time = time.time()
            
            if self.state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has elapsed
                if (self.last_failure_time and 
                    current_time - self.last_failure_time >= self.config.recovery_timeout):
                    
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    await self._change_state(CircuitBreakerState.HALF_OPEN)
                    self.half_open_successes = 0
    
    async def _on_success(self):
        """Handle successful request."""
        async with self._lock:
            self.stats.record_success()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_successes += 1
                
                if self.half_open_successes >= self.config.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                    await self._change_state(CircuitBreakerState.CLOSED)
            
            logger.debug(f"Circuit breaker '{self.name}' - success recorded")
    
    async def _on_failure(self):
        """Handle failed request."""
        async with self._lock:
            self.stats.record_failure()
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state goes back to open
                logger.warning(f"Circuit breaker '{self.name}' transitioning back to OPEN")
                await self._change_state(CircuitBreakerState.OPEN)
                
            elif self.state == CircuitBreakerState.CLOSED:
                # Check if failure threshold is reached
                if self.stats.failure_count >= self.config.failure_threshold:
                    logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN")
                    await self._change_state(CircuitBreakerState.OPEN)
            
            logger.debug(f"Circuit breaker '{self.name}' - failure recorded")
    
    async def _change_state(self, new_state: CircuitBreakerState):
        """Change circuit breaker state."""
        old_state = self.state
        self.state = new_state
        self.stats.record_state_change(old_state, new_state)
        
        logger.info(f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}")
    
    async def reset(self):
        """Manually reset circuit breaker to closed state."""
        async with self._lock:
            logger.info(f"Manually resetting circuit breaker '{self.name}'")
            await self._change_state(CircuitBreakerState.CLOSED)
            self.stats = CircuitBreakerStats()
            self.last_failure_time = None
            self.half_open_successes = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "config": self.config.to_dict(),
            "stats": self.stats.to_dict(),
            "is_available": self.state != CircuitBreakerState.OPEN,
            "last_failure_time": self.last_failure_time,
            "half_open_successes": self.half_open_successes if self.state == CircuitBreakerState.HALF_OPEN else None
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = {}
    
    def register(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Register a new circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Circuit breaker configuration
            
        Returns:
            CircuitBreaker: Configured circuit breaker
        """
        if name in self._breakers:
            return self._breakers[name]
        
        if config is None:
            config = CircuitBreakerConfig()
        
        breaker = CircuitBreaker(name, config)
        self._breakers[name] = breaker
        self._configs[name] = config
        
        logger.info(f"Circuit breaker '{name}' registered")
        return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status() 
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()
        logger.info("All circuit breakers reset")
    
    async def reset_by_name(self, name: str):
        """Reset specific circuit breaker."""
        breaker = self._breakers.get(name)
        if breaker:
            await breaker.reset()
            logger.info(f"Circuit breaker '{name}' reset")
        else:
            logger.warning(f"Circuit breaker '{name}' not found")


# Global circuit breaker registry
_circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    return _circuit_breaker_registry


def get_circuit_breaker(
    name: str, 
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create circuit breaker.
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        
    Returns:
        CircuitBreaker: Circuit breaker instance
    """
    return _circuit_breaker_registry.register(name, config)


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    timeout: int = 30,
    expected_exception: type = Exception
):
    """
    Decorator for applying circuit breaker to functions.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures to open circuit
        recovery_timeout: Seconds to wait before trying again
        timeout: Request timeout in seconds
        expected_exception: Exception type that triggers circuit
    
    Returns:
        function: Decorated function
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        timeout=timeout,
        expected_exception=expected_exception
    )
    
    breaker = get_circuit_breaker(name, config)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def execute():
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            return await breaker(execute)
        return wrapper
    
    return decorator


# Predefined circuit breaker configurations for common services
EXTERNAL_API_CONFIGS = {
    "plantnet": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,  # 5 minutes
        timeout=30,
        expected_exception=Exception
    ),
    "trefle": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,
        timeout=30,
        expected_exception=Exception
    ),
    "plant_id": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=600,  # 10 minutes
        timeout=45,
        expected_exception=Exception
    ),
    "kindwise": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,
        timeout=30,
        expected_exception=Exception
    ),
    "openweather": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=180,  # 3 minutes
        timeout=15,
        expected_exception=Exception
    ),
    "tomorrow_io": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=180,
        timeout=15,
        expected_exception=Exception
    ),
    "weatherstack": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=180,
        timeout=15,
        expected_exception=Exception
    ),
    "visual_crossing": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=180,
        timeout=15,
        expected_exception=Exception
    ),
    "openai": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,
        timeout=60,  # AI requests can take longer
        expected_exception=Exception
    ),
    "gemini": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,
        timeout=60,
        expected_exception=Exception
    ),
    "claude": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,
        timeout=60,
        expected_exception=Exception
    ),
}


def initialize_external_api_breakers():
    """Initialize circuit breakers for all external APIs."""
    registry = get_circuit_breaker_registry()
    
    for api_name, config in EXTERNAL_API_CONFIGS.items():
        registry.register(api_name, config)
        logger.info(f"Initialized circuit breaker for {api_name}")
    
    logger.info("All external API circuit breakers initialized")


async def get_healthy_services() -> list:
    """
    Get list of healthy (available) services.
    
    Returns:
        list: Names of healthy services
    """
    registry = get_circuit_breaker_registry()
    healthy_services = []
    
    for name, breaker in registry._breakers.items():
        if breaker.state != CircuitBreakerState.OPEN:
            healthy_services.append(name)
    
    return healthy_services


async def get_unhealthy_services() -> list:
    """
    Get list of unhealthy (unavailable) services.
    
    Returns:
        list: Names of unhealthy services
    """
    registry = get_circuit_breaker_registry()
    unhealthy_services = []
    
    for name, breaker in registry._breakers.items():
        if breaker.state == CircuitBreakerState.OPEN:
            unhealthy_services.append({
                "name": name,
                "failure_count": breaker.stats.failure_count,
                "last_failure": breaker.stats.last_failure_time,
                "recovery_time": breaker.config.recovery_timeout
            })
    
    return unhealthy_services