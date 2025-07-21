# 📄 File: app/shared/infrastructure/external_apis/api_rotation.py

# 🧭 Purpose (Layman Explanation):
# This file manages multiple backup services - if one plant identification service is down,
# it automatically tries the next one, ensuring the app always works even when some services fail.

# 🧪 Purpose (Technical Summary):
# Implements API rotation, circuit breaker pattern, and failover logic to provide resilient
# external service integration with automatic fallback and load distribution.

# 🔗 Dependencies:
# - api_client: HTTP client instances
# - asyncio: Async operations and timing
# - circuit_breaker: Circuit breaker implementation
# - cache: State persistence and caching

# 🔄 Connected Modules / Calls From:
# Used by: Plant identification services, Weather data fetching, AI service calls,
# Payment processing, Any module requiring external API resilience

import asyncio
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field

from app.shared.infrastructure.external_apis.api_client import APIClient
from app.shared.infrastructure.cache.cache_manager import get_cache_manager
from app.shared.core.exceptions import (
    ExternalAPIError,
    APIRateLimitError,
    APITimeoutError,
    APICircuitBreakerError,
    APIRotationError
)
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit tripped, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # successes needed to close circuit
    timeout: int = 30
    expected_exceptions: tuple = (ExternalAPIError, APITimeoutError, APIRateLimitError)


@dataclass
class APIEndpoint:
    """API endpoint configuration."""
    name: str
    client: APIClient
    priority: int = 1
    weight: float = 1.0
    enabled: bool = True
    circuit_breaker: Optional['CircuitBreaker'] = None
    last_used: Optional[datetime] = None
    success_rate: float = 1.0
    avg_response_time: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker implementation for API resilience.
    
    Prevents cascading failures by monitoring API health and
    temporarily disabling failing services.
    """
    
    def __init__(self, api_name: str, config: CircuitBreakerConfig):
        self.api_name = api_name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None
        self.call_history: List[Dict] = []
        self.max_history = 100
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function call through circuit breaker."""
        current_time = datetime.utcnow()
        
        # Check if circuit is open and recovery time hasn't passed
        if self.state == CircuitBreakerState.OPEN:
            if self.next_attempt_time and current_time < self.next_attempt_time:
                raise APICircuitBreakerError(
                    f"Circuit breaker open for {self.api_name}. "
                    f"Next attempt at {self.next_attempt_time}"
                )
            else:
                # Move to half-open state for testing
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker for {self.api_name} moved to HALF_OPEN")
        
        # Execute the function call
        start_time = time.time()
        call_record = {
            'timestamp': current_time.isoformat(),
            'state': self.state.value,
            'success': False,
            'error': None,
            'response_time': 0
        }
        
        try:
            result = await func(*args, **kwargs)
            
            # Record success
            response_time = time.time() - start_time
            call_record.update({
                'success': True,
                'response_time': response_time
            })
            
            await self._record_success()
            return result
            
        except Exception as e:
            # Record failure
            response_time = time.time() - start_time
            call_record.update({
                'error': str(e),
                'error_type': type(e).__name__,
                'response_time': response_time
            })
            
            # Only count certain exceptions as failures
            if isinstance(e, self.config.expected_exceptions):
                await self._record_failure()
            
            raise e
            
        finally:
            # Add to call history
            self.call_history.append(call_record)
            if len(self.call_history) > self.max_history:
                self.call_history = self.call_history[-self.max_history:]
    
    async def _record_success(self):
        """Record a successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            
            # If enough successes, close the circuit
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.next_attempt_time = None
                logger.info(f"Circuit breaker for {self.api_name} CLOSED after recovery")
        
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
    
    async def _record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Return to open state if failure in half-open
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = datetime.utcnow() + timedelta(
                seconds=self.config.recovery_timeout
            )
            logger.warning(f"Circuit breaker for {self.api_name} returned to OPEN")
        
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            # Trip the circuit
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = datetime.utcnow() + timedelta(
                seconds=self.config.recovery_timeout
            )
            logger.error(
                f"Circuit breaker TRIPPED for {self.api_name} "
                f"after {self.failure_count} failures"
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            'api_name': self.api_name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'next_attempt_time': self.next_attempt_time.isoformat() if self.next_attempt_time else None,
            'call_history_count': len(self.call_history),
            'recent_success_rate': self._calculate_recent_success_rate()
        }
    
    def _calculate_recent_success_rate(self, window_minutes: int = 10) -> float:
        """Calculate success rate in recent time window."""
        if not self.call_history:
            return 1.0
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_calls = [
            call for call in self.call_history 
            if datetime.fromisoformat(call['timestamp']) > cutoff_time
        ]
        
        if not recent_calls:
            return 1.0
        
        successful_calls = sum(1 for call in recent_calls if call['success'])
        return successful_calls / len(recent_calls)


class APIRotationManager:
    """
    Manages rotation and failover between multiple API endpoints.
    
    Features:
    - Priority-based routing
    - Weighted round-robin distribution
    - Circuit breaker integration
    - Performance-based selection
    - Automatic failover
    """
    
    def __init__(self, category: str):
        self.category = category
        self.endpoints: List[APIEndpoint] = []
        self.cache_manager = None
        self.current_index = 0
        
        # Performance tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'failover_count': 0,
            'endpoints_used': {},
            'average_response_time': 0
        }
        
        # Rotation strategies
        self.rotation_strategy = 'priority_weighted'  # priority_weighted, round_robin, performance_based
        self.enable_circuit_breakers = True
        self.enable_performance_tracking = True
    
    async def initialize(self):
        """Initialize the rotation manager."""
        try:
            self.cache_manager = await get_cache_manager()
            logger.info(f"API rotation manager initialized for category: {self.category}")
        except Exception as e:
            logger.warning(f"Failed to initialize cache for rotation manager: {e}")
    
    def add_endpoint(
        self,
        name: str,
        client: APIClient,
        priority: int = 1,
        weight: float = 1.0,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """Add an API endpoint to the rotation."""
        # Create circuit breaker if enabled
        circuit_breaker = None
        if self.enable_circuit_breakers:
            config = circuit_breaker_config or CircuitBreakerConfig()
            circuit_breaker = CircuitBreaker(name, config)
        
        endpoint = APIEndpoint(
            name=name,
            client=client,
            priority=priority,
            weight=weight,
            circuit_breaker=circuit_breaker
        )
        
        self.endpoints.append(endpoint)
        self.endpoints.sort(key=lambda x: x.priority)  # Sort by priority
        
        logger.info(f"Added endpoint {name} to {self.category} rotation (priority: {priority})")
    
    def remove_endpoint(self, name: str):
        """Remove an endpoint from rotation."""
        self.endpoints = [ep for ep in self.endpoints if ep.name != name]
        logger.info(f"Removed endpoint {name} from {self.category} rotation")
    
    def enable_endpoint(self, name: str):
        """Enable an endpoint."""
        for endpoint in self.endpoints:
            if endpoint.name == name:
                endpoint.enabled = True
                logger.info(f"Enabled endpoint {name} in {self.category} rotation")
                break
    
    def disable_endpoint(self, name: str):
        """Disable an endpoint."""
        for endpoint in self.endpoints:
            if endpoint.name == name:
                endpoint.enabled = False
                logger.info(f"Disabled endpoint {name} in {self.category} rotation")
                break
    
    async def call_with_rotation(
        self,
        method: str,
        endpoint: str,
        max_attempts: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Make API call with automatic rotation and failover.
        
        Args:
            method: HTTP method (get, post, put, delete)
            endpoint: API endpoint path
            max_attempts: Maximum attempts across all APIs
            **kwargs: Additional arguments for the API call
        
        Returns:
            API response data
        
        Raises:
            APIRotationError: If all APIs fail
        """
        if not self.endpoints:
            raise APIRotationError(f"No endpoints configured for {self.category}")
        
        max_attempts = max_attempts or len(self.endpoints)
        attempts = 0
        last_exception = None
        
        # Get ordered list of endpoints to try
        endpoint_order = self._get_endpoint_order()
        
        for api_endpoint in endpoint_order:
            if attempts >= max_attempts:
                break
            
            if not api_endpoint.enabled:
                continue
            
            attempts += 1
            
            try:
                # Update stats
                self.stats['total_requests'] += 1
                endpoint_stats = self.stats['endpoints_used'].get(api_endpoint.name, 0)
                self.stats['endpoints_used'][api_endpoint.name] = endpoint_stats + 1
                
                # Make the API call
                start_time = time.time()
                
                if api_endpoint.circuit_breaker:
                    # Call through circuit breaker
                    result = await api_endpoint.circuit_breaker.call(
                        self._make_api_call,
                        api_endpoint.client,
                        method,
                        endpoint,
                        **kwargs
                    )
                else:
                    # Direct call
                    result = await self._make_api_call(
                        api_endpoint.client,
                        method,
                        endpoint,
                        **kwargs
                    )
                
                response_time = time.time() - start_time
                
                # Update endpoint performance metrics
                await self._update_endpoint_performance(api_endpoint, response_time, True)
                
                # Update overall stats
                self.stats['successful_requests'] += 1
                
                logger.info(
                    f"API call successful via {api_endpoint.name} "
                    f"(attempt {attempts}/{max_attempts}) - {response_time:.2f}s"
                )
                
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                await self._update_endpoint_performance(api_endpoint, response_time, False)
                
                last_exception = e
                
                logger.warning(
                    f"API call failed via {api_endpoint.name} "
                    f"(attempt {attempts}/{max_attempts}): {e}"
                )
                
                # Check if we should continue trying other endpoints
                if isinstance(e, (APIRateLimitError, APICircuitBreakerError)):
                    # These errors suggest trying another endpoint
                    self.stats['failover_count'] += 1
                    continue
                elif isinstance(e, ExternalAPIError):
                    # Generic API error, might be worth trying another endpoint
                    self.stats['failover_count'] += 1
                    continue
                else:
                    # Other errors might not be worth retrying
                    break
        
        # All endpoints failed
        self.stats['failed_requests'] += 1
        
        error_msg = (
            f"All API endpoints failed for {self.category} after {attempts} attempts. "
            f"Last error: {last_exception}"
        )
        
        logger.error(error_msg)
        raise APIRotationError(error_msg)
    
    async def _make_api_call(
        self,
        client: APIClient,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """Make the actual API call."""
        method_func = getattr(client, method.lower())
        if not method_func:
            raise ValueError(f"Unsupported method: {method}")
        
        return await method_func(endpoint, **kwargs)
    
    def _get_endpoint_order(self) -> List[APIEndpoint]:
        """Get ordered list of endpoints based on rotation strategy."""
        available_endpoints = [ep for ep in self.endpoints if ep.enabled]
        
        if not available_endpoints:
            return []
        
        if self.rotation_strategy == 'priority_weighted':
            return self._priority_weighted_order(available_endpoints)
        elif self.rotation_strategy == 'round_robin':
            return self._round_robin_order(available_endpoints)
        elif self.rotation_strategy == 'performance_based':
            return self._performance_based_order(available_endpoints)
        else:
            # Default to priority order
            return sorted(available_endpoints, key=lambda x: x.priority)
    
    def _priority_weighted_order(self, endpoints: List[APIEndpoint]) -> List[APIEndpoint]:
        """Order endpoints by priority with weighted selection within same priority."""
        # Group by priority
        priority_groups = {}
        for ep in endpoints:
            if ep.priority not in priority_groups:
                priority_groups[ep.priority] = []
            priority_groups[ep.priority].append(ep)
        
        ordered_endpoints = []
        
        # Process each priority group
        for priority in sorted(priority_groups.keys()):
            group = priority_groups[priority]
            
            if len(group) == 1:
                ordered_endpoints.extend(group)
            else:
                # Weighted random selection within priority group
                weights = [ep.weight * ep.success_rate for ep in group]
                total_weight = sum(weights)
                
                if total_weight > 0:
                    # Sort by weighted score (descending)
                    scored_endpoints = list(zip(group, weights))
                    scored_endpoints.sort(key=lambda x: x[1], reverse=True)
                    ordered_endpoints.extend([ep for ep, _ in scored_endpoints])
                else:
                    ordered_endpoints.extend(group)
        
        return ordered_endpoints
    
    def _round_robin_order(self, endpoints: List[APIEndpoint]) -> List[APIEndpoint]:
        """Round-robin ordering of endpoints."""
        if not endpoints:
            return []
        
        # Start from current index and wrap around
        ordered = []
        for i in range(len(endpoints)):
            index = (self.current_index + i) % len(endpoints)
            ordered.append(endpoints[index])
        
        # Update current index for next call
        self.current_index = (self.current_index + 1) % len(endpoints)
        
        return ordered
    
    def _performance_based_order(self, endpoints: List[APIEndpoint]) -> List[APIEndpoint]:
        """Order endpoints by performance metrics."""
        # Calculate performance score (higher is better)
        def performance_score(ep):
            response_time_score = 1.0 / (ep.avg_response_time + 0.1)  # Avoid division by zero
            success_rate_score = ep.success_rate
            circuit_breaker_score = 1.0
            
            if ep.circuit_breaker:
                if ep.circuit_breaker.state == CircuitBreakerState.OPEN:
                    circuit_breaker_score = 0.0
                elif ep.circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                    circuit_breaker_score = 0.5
            
            return response_time_score * success_rate_score * circuit_breaker_score
        
        return sorted(endpoints, key=performance_score, reverse=True)
    
    async def _update_endpoint_performance(
        self,
        endpoint: APIEndpoint,
        response_time: float,
        success: bool
    ):
        """Update endpoint performance metrics."""
        if not self.enable_performance_tracking:
            return
        
        # Update last used time
        endpoint.last_used = datetime.utcnow()
        
        # Update average response time (exponential moving average)
        if endpoint.avg_response_time == 0:
            endpoint.avg_response_time = response_time
        else:
            endpoint.avg_response_time = (
                endpoint.avg_response_time * 0.7 + response_time * 0.3
            )
        
        # Update success rate (exponential moving average)
        success_value = 1.0 if success else 0.0
        endpoint.success_rate = endpoint.success_rate * 0.9 + success_value * 0.1
        
        # Ensure success rate doesn't go below a minimum threshold
        endpoint.success_rate = max(endpoint.success_rate, 0.1)
    
    async def get_endpoint_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of specific endpoint."""
        for endpoint in self.endpoints:
            if endpoint.name == name:
                status = {
                    'name': endpoint.name,
                    'enabled': endpoint.enabled,
                    'priority': endpoint.priority,
                    'weight': endpoint.weight,
                    'success_rate': endpoint.success_rate,
                    'avg_response_time': endpoint.avg_response_time,
                    'last_used': endpoint.last_used.isoformat() if endpoint.last_used else None
                }
                
                if endpoint.circuit_breaker:
                    status['circuit_breaker'] = endpoint.circuit_breaker.get_status()
                
                return status
        
        return None
    
    def get_rotation_stats(self) -> Dict[str, Any]:
        """Get rotation manager statistics."""
        return {
            'category': self.category,
            'total_endpoints': len(self.endpoints),
            'enabled_endpoints': len([ep for ep in self.endpoints if ep.enabled]),
            'rotation_strategy': self.rotation_strategy,
            'stats': self.stats,
            'endpoints': [
                {
                    'name': ep.name,
                    'enabled': ep.enabled,
                    'priority': ep.priority,
                    'success_rate': ep.success_rate,
                    'avg_response_time': ep.avg_response_time
                }
                for ep in self.endpoints
            ]
        }
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all endpoints."""
        results = {}
        
        for endpoint in self.endpoints:
            if endpoint.enabled:
                try:
                    health_result = await endpoint.client.health_check()
                    results[endpoint.name] = health_result
                except Exception as e:
                    results[endpoint.name] = {
                        'status': 'unhealthy',
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    }
            else:
                results[endpoint.name] = {
                    'status': 'disabled',
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return results


# Factory function for creating rotation managers
def create_rotation_manager(category: str) -> APIRotationManager:
    """Create and configure rotation manager for category."""
    manager = APIRotationManager(category)
    return manager


# Utility functions for common rotation patterns
async def call_with_plant_apis(endpoint: str, **kwargs) -> Any:
    """Make call with plant identification API rotation."""
    # This would be used by plant identification services
    # Implementation would get the rotation manager and make the call
    pass


async def call_with_weather_apis(endpoint: str, **kwargs) -> Any:
    """Make call with weather API rotation."""
    # This would be used by weather services
    # Implementation would get the rotation manager and make the call
    pass


async def call_with_ai_apis(endpoint: str, **kwargs) -> Any:
    """Make call with AI service API rotation."""
    # This would be used by AI services
    # Implementation would get the rotation manager and make the call
    pass