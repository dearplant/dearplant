# 📄 File: app/api/middleware/rate_limiting.py
# 🧭 Purpose (Layman Explanation): 
# This file prevents users from making too many requests too quickly, like a bouncer at a club
# who limits how often someone can enter to prevent overcrowding and ensure fair access for everyone.
# 🧪 Purpose (Technical Summary): 
# Rate limiting middleware that tracks and enforces request limits per user/IP, with Redis-based
# storage, tiered limits for different user types, and endpoint-specific rate limiting.
# 🔗 Dependencies: 
# FastAPI, Redis, app.shared.infrastructure.cache, datetime, typing
# 🔄 Connected Modules / Calls From: 
# app.main.py (middleware registration), all API endpoints, Redis cache system

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.shared.config.settings import get_settings
from app.shared.infrastructure.cache.redis_client import get_redis_client
from . import should_exclude_path, get_middleware_config

logger = logging.getLogger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API endpoints
    
    Features:
    - Per-user and per-IP rate limiting
    - Tiered limits (free, premium, admin users)
    - Endpoint-specific rate limits
    - Redis-based distributed rate limiting
    - Sliding window algorithm
    - Burst protection
    - Rate limit headers in responses
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        global_rate_limit: str = "100/minute",
        premium_rate_limit: str = "500/minute",
        admin_rate_limit: str = "1000/minute"
    ):
        super().__init__(app)
        self.settings = get_settings()
        
        # Default rate limits
        self.global_rate_limit = self._parse_rate_limit(str(global_rate_limit))
        self.premium_rate_limit = self._parse_rate_limit(str(premium_rate_limit))
        self.admin_rate_limit = self._parse_rate_limit(str(admin_rate_limit))
        
        # Endpoint-specific rate limits
        self.endpoint_limits = {
            # Authentication endpoints (more restrictive)
            "/api/v1/auth/login": self._parse_rate_limit("5/minute"),
            "/api/v1/auth/register": self._parse_rate_limit("3/minute"),
            "/api/v1/auth/refresh": self._parse_rate_limit("10/minute"),
            "/api/v1/auth/forgot-password": self._parse_rate_limit("3/minute"),
            
            # Plant identification (API usage limited)
            "/api/v1/plants/identify": self._parse_rate_limit("10/minute"),
            
            # AI features (compute intensive)
            "/api/v1/ai/chat": self._parse_rate_limit("30/minute"),
            "/api/v1/ai/recommendations": self._parse_rate_limit("20/minute"),
            
            # File uploads (bandwidth limited)
            "/api/v1/plants/photos": self._parse_rate_limit("20/minute"),
            "/api/v1/growth/photos": self._parse_rate_limit("20/minute"),
            
            # Community actions (spam prevention)
            "/api/v1/community/posts": self._parse_rate_limit("15/minute"),
            "/api/v1/community/comments": self._parse_rate_limit("30/minute"),
            
            # Payment endpoints (security)
            "/api/v1/payments/process": self._parse_rate_limit("5/minute"),
            "/api/v1/subscriptions/create": self._parse_rate_limit("2/minute"),
        }
        
        # Burst limits (allow short bursts above rate limit)
        self.burst_limit = 10  # Allow 10 extra requests in burst
        self.burst_window = 60  # Burst window in seconds
        
        # Redis key prefixes
        self.rate_limit_prefix = "rate_limit:"
        self.burst_prefix = "burst_limit:"
        
        # Redis client
        self.redis = None
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process rate limiting for incoming requests
        
        Args:
            request: HTTP request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response or rate limit error
        """
        # Skip rate limiting for excluded paths
        if should_exclude_path("rate_limiting", request.url.path):
            return await call_next(request)
        
        # Initialize Redis client if needed
        if not self.redis:
            try:
                self.redis = await get_redis_client()
            except Exception as e:
                logger.warning(f"Redis not available for rate limiting: {e}")
                # Continue without rate limiting if Redis is down
                return await call_next(request)
        
        # Check rate limits
        rate_limit_result = await self._check_rate_limits(request)
        
        if rate_limit_result["allowed"]:
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            self._add_rate_limit_headers(response, rate_limit_result)
            
            return response
        else:
            # Rate limit exceeded
            return self._create_rate_limit_response(rate_limit_result)
    
    async def _check_rate_limits(self, request: Request) -> Dict[str, Any]:
        """
        Check if request is within rate limits
        
        Args:
            request: HTTP request
            
        Returns:
            Rate limit check result
        """
        try:
            # Get rate limit key and limits
            rate_key, rate_limit = await self._get_rate_limit_info(request)
            
            # Check main rate limit
            current_count, reset_time = await self._get_current_usage(rate_key, rate_limit["window"])
            
            # Check if within limit
            within_limit = current_count < rate_limit["limit"]
            
            # If over limit, check burst allowance
            burst_allowed = False
            if not within_limit:
                burst_key = f"{self.burst_prefix}{rate_key}"
                burst_count, _ = await self._get_current_usage(burst_key, self.burst_window)
                burst_allowed = burst_count < self.burst_limit
            
            allowed = within_limit or burst_allowed
            
            if allowed:
                # Increment counters
                await self._increment_usage(rate_key, rate_limit["window"])
                if not within_limit:
                    await self._increment_usage(f"{self.burst_prefix}{rate_key}", self.burst_window)
            
            return {
                "allowed": allowed,
                "current_count": current_count,
                "limit": rate_limit["limit"],
                "window": rate_limit["window"],
                "reset_time": reset_time,
                "remaining": max(0, rate_limit["limit"] - current_count - 1),
                "burst_used": not within_limit,
                "rate_key": rate_key
            }
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Allow request if rate limiting fails
            return {
                "allowed": True,
                "current_count": 0,
                "limit": float('inf'),
                "window": 60,
                "reset_time": datetime.now() + timedelta(minutes=1),
                "remaining": float('inf'),
                "burst_used": False,
                "error": str(e)
            }
    
    async def _get_rate_limit_info(self, request: Request) -> Tuple[str, Dict[str, Any]]:
        """
        Get rate limit key and configuration for request
        
        Args:
            request: HTTP request
            
        Returns:
            Tuple of (rate_key, rate_limit_config)
        """
        # Determine user type and ID
        user_id = None
        user_type = "anonymous"
        
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user["id"]
            if getattr(request.state, "is_admin", False):
                user_type = "admin"
            elif getattr(request.state, "is_premium", False):
                user_type = "premium"
            else:
                user_type = "user"
        
        # Get client IP for anonymous users
        client_ip = self._get_client_ip(request)
        
        # Build rate limit key
        if user_id:
            rate_key = f"user:{user_id}"
        else:
            rate_key = f"ip:{client_ip}"
        
        # Get endpoint-specific limit or default
        endpoint_limit = self._get_endpoint_limit(request.url.path)
        
        if endpoint_limit:
            # Use endpoint-specific limit
            rate_limit = endpoint_limit
            rate_key = f"{rate_key}:endpoint:{request.url.path}"
        else:
            # Use user type default limit
            if user_type == "admin":
                rate_limit = self.admin_rate_limit
            elif user_type == "premium":
                rate_limit = self.premium_rate_limit
            else:
                rate_limit = self.global_rate_limit
            
            rate_key = f"{rate_key}:global"
        
        # Add method to key for more granular limiting
        rate_key = f"{self.rate_limit_prefix}{rate_key}:{request.method}"
        
        return rate_key, rate_limit
    
    def _get_endpoint_limit(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get endpoint-specific rate limit
        
        Args:
            path: Request path
            
        Returns:
            Rate limit config or None
        """
        # Check exact path matches
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check pattern matches
        for endpoint_pattern, limit in self.endpoint_limits.items():
            if self._path_matches_pattern(path, endpoint_pattern):
                return limit
        
        return None
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if path matches endpoint pattern
        
        Args:
            path: Request path
            pattern: Endpoint pattern
            
        Returns:
            True if path matches pattern
        """
        # Simple pattern matching (can be enhanced with regex)
        if "*" in pattern:
            # Wildcard pattern
            pattern_regex = pattern.replace("*", ".*")
            return bool(re.match(pattern_regex, path))
        else:
            # Exact match or prefix match
            return path == pattern or path.startswith(pattern + "/")
    
    async def _get_current_usage(self, key: str, window: int) -> Tuple[int, datetime]:
        """
        Get current usage count and reset time
        
        Args:
            key: Redis key
            window: Time window in seconds
            
        Returns:
            Tuple of (current_count, reset_time)
        """
        try:
            if not self.redis:
                return 0, datetime.now() + timedelta(seconds=window)
            
            # Use sliding window log algorithm
            now = datetime.now()
            window_start = now - timedelta(seconds=window)
            
            # Remove old entries and count current ones
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start.timestamp())
            pipe.zcard(key)
            pipe.ttl(key)
            
            results = await pipe.execute()
            current_count = results[1] if len(results) > 1 else 0
            ttl = results[2] if len(results) > 2 else window
            
            # Calculate reset time
            if ttl > 0:
                reset_time = now + timedelta(seconds=ttl)
            else:
                reset_time = now + timedelta(seconds=window)
            
            return current_count, reset_time
            
        except Exception as e:
            logger.error(f"Error getting rate limit usage: {e}")
            return 0, datetime.now() + timedelta(seconds=window)
    
    async def _increment_usage(self, key: str, window: int) -> None:
        """
        Increment usage counter
        
        Args:
            key: Redis key
            window: Time window in seconds
        """
        try:
            if not self.redis:
                return
            
            now = datetime.now()
            score = now.timestamp()
            
            # Add current timestamp to sorted set
            pipe = self.redis.pipeline()
            pipe.zadd(key, {str(score): score})
            pipe.expire(key, window)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error incrementing rate limit: {e}")
    
    def _parse_rate_limit(self, rate_limit_str: str) -> Dict[str, Any]:
        """
        Parse rate limit string into configuration
        
        Args:
            rate_limit_str: Rate limit string (e.g., "100/minute", "10/second")
            
        Returns:
            Rate limit configuration
        """
        # Type checking and casting
        if isinstance(rate_limit_str, int):
            raise ValueError(f"Expected string for rate limit like '100/minute', got int: {rate_limit_str}")
        if not isinstance(rate_limit_str, str):
            raise TypeError(f"Expected string for rate limit, got {type(rate_limit_str)}")
        try:
            limit_str, period_str = rate_limit_str.split("/")
            limit = int(limit_str)
            
            # Convert period to seconds
            period_map = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }
            
            # Handle plural forms
            if period_str.endswith("s"):
                period_str = period_str[:-1]
            
            window = period_map.get(period_str, 60)
            
            return {
                "limit": limit,
                "window": window,
                "period": period_str
            }
            
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid rate limit format '{rate_limit_str}': {e}")
            # Return default limit
            return {"limit": 100, "window": 60, "period": "minute"}
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _add_rate_limit_headers(self, response: Response, rate_result: Dict[str, Any]) -> None:
        """
        Add rate limit headers to response
        
        Args:
            response: HTTP response
            rate_result: Rate limit check result
        """
        try:
            response.headers["X-Rate-Limit-Limit"] = str(rate_result["limit"])
            response.headers["X-Rate-Limit-Remaining"] = str(rate_result["remaining"])
            response.headers["X-Rate-Limit-Reset"] = str(int(rate_result["reset_time"].timestamp()))
            response.headers["X-Rate-Limit-Window"] = str(rate_result["window"])
            
            if rate_result.get("burst_used"):
                response.headers["X-Rate-Limit-Burst-Used"] = "true"
                
        except Exception as e:
            logger.warning(f"Error adding rate limit headers: {e}")
    
    def _create_rate_limit_response(self, rate_result: Dict[str, Any]) -> JSONResponse:
        """
        Create rate limit exceeded response
        
        Args:
            rate_result: Rate limit check result
            
        Returns:
            JSON error response
        """
        reset_time = rate_result["reset_time"]
        retry_after = max(1, int((reset_time - datetime.now()).total_seconds()))
        
        response = JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {rate_result['limit']} requests per {rate_result['window']} seconds exceeded",
                    "details": {
                        "limit": rate_result["limit"],
                        "window_seconds": rate_result["window"],
                        "current_usage": rate_result["current_count"],
                        "reset_time": reset_time.isoformat(),
                        "retry_after_seconds": retry_after
                    },
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
        
        # Add rate limit headers
        response.headers["X-Rate-Limit-Limit"] = str(rate_result["limit"])
        response.headers["X-Rate-Limit-Remaining"] = "0"
        response.headers["X-Rate-Limit-Reset"] = str(int(reset_time.timestamp()))
        response.headers["Retry-After"] = str(retry_after)
        
        return response


# Utility functions for rate limiting
async def check_rate_limit(
    key: str, 
    limit: int, 
    window: int,
    redis_client=None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check rate limit for a specific key
    
    Args:
        key: Rate limit key
        limit: Request limit
        window: Time window in seconds
        redis_client: Redis client (optional)
        
    Returns:
        Tuple of (allowed, rate_info)
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()
        
        now = datetime.now()
        window_start = now - timedelta(seconds=window)
        
        # Remove old entries and count current ones
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start.timestamp())
        pipe.zcard(key)
        
        results = await pipe.execute()
        current_count = results[1] if len(results) > 1 else 0
        
        allowed = current_count < limit
        
        if allowed:
            # Increment counter
            score = now.timestamp()
            pipe = redis_client.pipeline()
            pipe.zadd(key, {str(score): score})
            pipe.expire(key, window)
            await pipe.execute()
        
        return allowed, {
            "current_count": current_count,
            "limit": limit,
            "remaining": max(0, limit - current_count - (1 if allowed else 0)),
            "reset_time": now + timedelta(seconds=window),
            "window": window
        }
        
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        # Allow request if check fails
        return True, {
            "current_count": 0,
            "limit": limit,
            "remaining": limit,
            "reset_time": datetime.now() + timedelta(seconds=window),
            "window": window,
            "error": str(e)
        }


async def reset_rate_limit(key: str, redis_client=None) -> bool:
    """
    Reset rate limit for a specific key
    
    Args:
        key: Rate limit key
        redis_client: Redis client (optional)
        
    Returns:
        True if reset successful
    """
    try:
        if not redis_client:
            redis_client = await get_redis_client()
        
        await redis_client.delete(key)
        return True
        
    except Exception as e:
        logger.error(f"Rate limit reset error: {e}")
        return False


def create_rate_limit_decorator(limit: int, window: int):
    """
    Create a rate limit decorator for functions
    
    Args:
        limit: Request limit
        window: Time window in seconds
        
    Returns:
        Rate limit decorator
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                # Create rate limit key from function name and user
                func_key = f"func:{func.__name__}"
                if hasattr(request.state, "user") and request.state.user:
                    rate_key = f"user:{request.state.user['id']}:{func_key}"
                else:
                    client_ip = request.client.host if request.client else "unknown"
                    rate_key = f"ip:{client_ip}:{func_key}"
                
                # Check rate limit
                allowed, rate_info = await check_rate_limit(rate_key, limit, window)
                
                if not allowed:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {limit} requests per {window} seconds"
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator