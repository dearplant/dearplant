"""
Rate limiting implementation for Plant Care Application.
Provides user-specific and global rate limiting with Redis backend.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import redis.asyncio as redis

from .exceptions import RateLimitError
from ..config.redis import get_redis_client

logger = logging.getLogger(__name__)


class RateLimitWindow(Enum):
    """Rate limit time windows."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    identifier: str           # User ID, IP, API key, etc.
    limit: int                # Maximum requests allowed
    window: str               # Time window (second, minute, hour, day)
    endpoint: Optional[str] = None  # Specific endpoint (optional)
    
    def __post_init__(self):
        """Validate rule configuration."""
        if self.limit <= 0:
            raise ValueError("Rate limit must be positive")
        
        if self.window not in [w.value for w in RateLimitWindow]:
            raise ValueError(f"Invalid window: {self.window}")
    
    def get_key(self) -> str:
        """Generate Redis key for this rule."""
        base_key = f"rate_limit:{self.identifier}:{self.window}"
        if self.endpoint:
            base_key += f":{self.endpoint}"
        return base_key
    
    def get_window_seconds(self) -> int:
        """Get window duration in seconds."""
        window_map = {
            RateLimitWindow.SECOND.value: 1,
            RateLimitWindow.MINUTE.value: 60,
            RateLimitWindow.HOUR.value: 3600,
            RateLimitWindow.DAY.value: 86400,
            RateLimitWindow.MONTH.value: 2592000  # 30 days
        }
        return window_map[self.window]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "identifier": self.identifier,
            "limit": self.limit,
            "window": self.window,
            "endpoint": self.endpoint,
            "window_seconds": self.get_window_seconds()
        }


class RateLimitResult:
    """Result of rate limit check."""
    
    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_time: int,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "allowed": self.allowed,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_time": self.reset_time,
            "retry_after": self.retry_after
        }


class RateLimiter:
    """
    Redis-based rate limiter with sliding window algorithm.
    Supports multiple time windows and endpoint-specific limits.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or get_redis_client()
        self.lua_script = self._get_lua_script()
    
    def _get_lua_script(self) -> str:
        """
        Lua script for atomic rate limit operations.
        Implements sliding window rate limiting.
        """
        return """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, 0, current_time - window)
        
        -- Count current requests
        local current_count = redis.call('ZCARD', key)
        
        -- Check if limit exceeded
        if current_count >= limit then
            -- Get oldest entry timestamp for retry calculation
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = 0
            if oldest[2] then
                retry_after = math.ceil(tonumber(oldest[2]) + window - current_time)
            end
            return {0, limit, 0, current_time + window, retry_after}
        end
        
        -- Add current request
        redis.call('ZADD', key, current_time, current_time .. ':' .. math.random())
        redis.call('EXPIRE', key, window)
        
        local remaining = limit - current_count - 1
        return {1, limit, remaining, current_time + window, 0}
        """
    
    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window: str,
        endpoint: Optional[str] = None
    ) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: User ID, IP address, or API key
            limit: Maximum requests allowed
            window: Time window (second, minute, hour, day)
            endpoint: Optional endpoint identifier
            
        Returns:
            bool: True if request is allowed
        """
        result = await self.check_limit(identifier, limit, window, endpoint)
        return result.allowed
    
    async def check_limit(
        self,
        identifier: str,
        limit: int,
        window: str,
        endpoint: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check rate limit and return detailed result.
        
        Args:
            identifier: User ID, IP address, or API key
            limit: Maximum requests allowed
            window: Time window (second, minute, hour, day)
            endpoint: Optional endpoint identifier
            
        Returns:
            RateLimitResult: Detailed rate limit result
        """
        try:
            rule = RateLimitRule(identifier, limit, window, endpoint)
            key = rule.get_key()
            window_seconds = rule.get_window_seconds()
            current_time = int(time.time())
            
            # Execute Lua script for atomic operation
            result = await self.redis.eval(
                self.lua_script,
                1,  # Number of keys
                key,
                window_seconds,
                limit,
                current_time
            )
            
            allowed, limit_val, remaining, reset_time, retry_after = result
            
            rate_limit_result = RateLimitResult(
                allowed=bool(allowed),
                limit=int(limit_val),
                remaining=int(remaining),
                reset_time=int(reset_time),
                retry_after=int(retry_after) if retry_after > 0 else None
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"{limit}/{window} ({endpoint or 'global'})"
                )
            
            return rate_limit_result
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Default to allowing request on error
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_time=int(time.time() + 3600)
            )
    
    async def record_request(
        self,
        identifier: str,
        limit: int,
        window: str,
        endpoint: Optional[str] = None
    ) -> int:
        """
        Record a request and return remaining count.
        Use check_limit() instead for better control.
        
        Args:
            identifier: User ID, IP address, or API key
            limit: Maximum requests allowed
            window: Time window
            endpoint: Optional endpoint identifier
            
        Returns:
            int: Remaining requests
        """
        result = await self.check_limit(identifier, limit, window, endpoint)
        return result.remaining
    
    async def get_reset_time(
        self,
        identifier: str,
        window: str,
        endpoint: Optional[str] = None
    ) -> int:
        """
        Get time when rate limit resets.
        
        Args:
            identifier: User ID, IP address, or API key
            window: Time window
            endpoint: Optional endpoint identifier
            
        Returns:
            int: Reset time timestamp
        """
        rule = RateLimitRule(identifier, 1, window, endpoint)  # Limit doesn't matter for this
        window_seconds = rule.get_window_seconds()
        return int(time.time()) + window_seconds
    
    async def reset_limit(
        self,
        identifier: str,
        window: str,
        endpoint: Optional[str] = None
    ):
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: User ID, IP address, or API key
            window: Time window
            endpoint: Optional endpoint identifier
        """
        try:
            rule = RateLimitRule(identifier, 1, window, endpoint)
            key = rule.get_key()
            await self.redis.delete(key)
            logger.info(f"Rate limit reset for {identifier}: {window} ({endpoint or 'global'})")
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
    
    async def get_usage_stats(
        self,
        identifier: str,
        window: str,
        endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for identifier.
        
        Args:
            identifier: User ID, IP address, or API key
            window: Time window
            endpoint: Optional endpoint identifier
            
        Returns:
            dict: Usage statistics
        """
        try:
            rule = RateLimitRule(identifier, 1, window, endpoint)
            key = rule.get_key()
            current_time = int(time.time())
            window_seconds = rule.get_window_seconds()
            
            # Remove expired entries
            await self.redis.zremrangebyscore(
                key, 0, current_time - window_seconds
            )
            
            # Get current count
            current_count = await self.redis.zcard(key)
            
            # Get request timestamps
            requests = await self.redis.zrange(key, 0, -1, withscores=True)
            request_times = [int(score) for _, score in requests]
            
            return {
                "identifier": identifier,
                "window": window,
                "endpoint": endpoint,
                "current_count": current_count,
                "request_times": request_times,
                "window_start": current_time - window_seconds,
                "window_end": current_time
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    async def get_all_limits(self, identifier: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all rate limits for identifier.
        
        Args:
            identifier: User ID, IP address, or API key
            
        Returns:
            dict: All rate limit information
        """
        try:
            pattern = f"rate_limit:{identifier}:*"
            keys = await self.redis.keys(pattern)
            
            limits = {}
            for key in keys:
                # Parse key to extract window and endpoint
                key_parts = key.decode().split(':')
                if len(key_parts) >= 3:
                    window = key_parts[2]
                    endpoint = key_parts[3] if len(key_parts) > 3 else None
                    
                    stats = await self.get_usage_stats(identifier, window, endpoint)
                    limit_key = f"{window}:{endpoint}" if endpoint else window
                    limits[limit_key] = stats
            
            return limits
            
        except Exception as e:
            logger.error(f"Failed to get all limits: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on rate limiter.
        
        Returns:
            dict: Health status
        """
        health_status = {
            "service": "rate_limiter",
            "status": "healthy",
            "redis_connection": False,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Test Redis connection
            await self.redis.ping()
            health_status["redis_connection"] = True
            
            # Test basic operation
            test_key = "rate_limit:health_check:test"
            await self.redis.set(test_key, "test", ex=10)
            await self.redis.delete(test_key)
            
            logger.debug("Rate limiter health check passed")
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            logger.error(f"Rate limiter health check failed: {e}")
        
        return health_status


class RateLimitExceeded(RateLimitError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self,
        identifier: str,
        limit: int,
        window: str,
        retry_after: Optional[int] = None,
        endpoint: Optional[str] = None
    ):
        message = f"Rate limit exceeded: {limit} requests per {window}"
        if endpoint:
            message += f" for {endpoint}"
        
        super().__init__(
            message=message,
            limit=limit,
            window=window,
            reset_time=retry_after
        )
        self.identifier = identifier
        self.endpoint = endpoint


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance.
    
    Returns:
        RateLimiter: Rate limiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# Rate limiting decorators and utilities
def rate_limit(
    limit: int,
    window: str,
    per: str = "user",
    endpoint: Optional[str] = None
):
    """
    Decorator for rate limiting functions.
    
    Args:
        limit: Maximum requests allowed
        window: Time window (second, minute, hour, day)
        per: Rate limit scope (user, ip, global)
        endpoint: Optional endpoint identifier
        
    Returns:
        function: Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented with proper request context
            # For now, it's a placeholder
            logger.debug(f"Rate limit check: {limit}/{window} per {per}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Common rate limiting configurations
RATE_LIMIT_CONFIGS = {
    "api_calls": {
        "free_user": {"limit": 1000, "window": "hour"},
        "premium_user": {"limit": 5000, "window": "hour"},
        "admin": {"limit": 10000, "window": "hour"}
    },
    "plant_identification": {
        "free_user": {"limit": 10, "window": "day"},
        "premium_user": {"limit": 100, "window": "day"}
    },
    "ai_chat": {
        "free_user": {"limit": 20, "window": "hour"},
        "premium_user": {"limit": 200, "window": "hour"}
    },
    "file_upload": {
        "all_users": {"limit": 50, "window": "hour"}
    },
    "auth_attempts": {
        "by_ip": {"limit": 10, "window": "minute"}
    },
    "password_reset": {
        "by_email": {"limit": 3, "window": "hour"}
    }
}


def get_rate_limit_config(feature: str, user_type: str) -> Optional[Dict[str, Union[int, str]]]:
    """
    Get rate limit configuration for feature and user type.
    
    Args:
        feature: Feature name (api_calls, plant_identification, etc.)
        user_type: User type (free_user, premium_user, admin)
        
    Returns:
        dict: Rate limit configuration or None
    """
    config = RATE_LIMIT_CONFIGS.get(feature, {})
    return config.get(user_type) or config.get("all_users")


async def apply_user_rate_limit(
    user_id: str,
    feature: str,
    is_premium: bool = False,
    is_admin: bool = False,
    endpoint: Optional[str] = None
) -> RateLimitResult:
    """
    Apply rate limit for user and feature.
    
    Args:
        user_id: User identifier
        feature: Feature being accessed
        is_premium: Whether user has premium subscription
        is_admin: Whether user has admin privileges
        endpoint: Optional endpoint identifier
        
    Returns:
        RateLimitResult: Rate limit check result
        
    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    # Determine user type
    if is_admin:
        user_type = "admin"
    elif is_premium:
        user_type = "premium_user"
    else:
        user_type = "free_user"
    
    # Get configuration
    config = get_rate_limit_config(feature, user_type)
    if not config:
        logger.warning(f"No rate limit config found for {feature}:{user_type}")
        return RateLimitResult(True, 999999, 999999, int(time.time() + 3600))
    
    # Check rate limit
    rate_limiter = get_rate_limiter()
    result = await rate_limiter.check_limit(
        identifier=user_id,
        limit=config["limit"],
        window=config["window"],
        endpoint=endpoint
    )
    
    # Raise exception if exceeded
    if not result.allowed:
        raise RateLimitExceeded(
            identifier=user_id,
            limit=config["limit"],
            window=config["window"],
            retry_after=result.retry_after,
            endpoint=endpoint
        )
    
    return result