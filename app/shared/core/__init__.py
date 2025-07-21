"""
Core utilities package for Plant Care Application.
Provides security, middleware, dependencies, and system utilities.
"""

from .security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    SecurityManager,
    get_security_manager
)

from .exceptions import (
    PlantCareException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    ExternalAPIError,
    DatabaseError
)

from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_db,
    get_redis,
    get_supabase,
    verify_api_key,
    check_rate_limit,
    require_premium_subscription
)

from .middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    LoggingMiddleware,
    CORSCustomMiddleware,
    SecurityHeadersMiddleware
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerError,
    get_circuit_breaker
)

from .rate_limiter import (
    RateLimiter,
    RateLimitRule,
    RateLimitExceeded,
    get_rate_limiter
)

from .event_bus import (
    EventBus,
    DomainEvent,
    EventHandler,
    get_event_bus,
    publish_event,
    subscribe_to_event
)

__all__ = [
    # Security
    "create_access_token",
    "verify_token", 
    "get_password_hash",
    "verify_password",
    "SecurityManager",
    "get_security_manager",
    
    # Exceptions
    "PlantCareException",
    "AuthenticationError",
    "AuthorizationError", 
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ExternalAPIError",
    "DatabaseError",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_db",
    "get_redis",
    "get_supabase",
    "verify_api_key",
    "check_rate_limit",
    "require_premium_subscription",
    
    # Middleware
    "AuthenticationMiddleware",
    "RateLimitMiddleware", 
    "LoggingMiddleware",
    "CORSCustomMiddleware",
    "SecurityHeadersMiddleware",
    
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerError",
    "get_circuit_breaker",
    
    # Rate Limiter
    "RateLimiter",
    "RateLimitRule",
    "RateLimitExceeded",
    "get_rate_limiter",
    
    # Event Bus
    "EventBus",
    "DomainEvent",
    "EventHandler", 
    "get_event_bus",
    "publish_event",
    "subscribe_to_event",
]