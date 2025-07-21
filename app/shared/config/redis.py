# 📄 File: app/shared/config/redis.py
#
# 🧭 Purpose (Layman Explanation):
# Configuration for our Redis cache system that helps our Plant Care app run faster
# by remembering frequently used data like plant information and user preferences.
#
# 🧪 Purpose (Technical Summary):
# Redis configuration with connection pooling, caching strategies, and
# environment-specific settings for session storage and application caching.
#
# 🔗 Dependencies:
# - redis Python package
# - aioredis for async operations
# - app.shared.config.settings
#
# 🔄 Connected Modules / Calls From:
# - app.shared.infrastructure.cache.redis_client
# - Cache management services
# - Session storage systems

import json
from typing import Any, Dict, Optional, Union

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from .settings import get_settings

settings = get_settings()


# =============================================================================
# REDIS CONFIGURATION CLASS
# =============================================================================

class RedisConfig:
    """Redis configuration class with connection management and caching strategies."""
    
    def __init__(self):
        self.settings = settings
        self._connection_pool: ConnectionPool | None = None
        self._redis_client: Redis | None = None
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return self.settings.redis_url
    
    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get Redis connection configuration."""
        
        base_config = {
            "encoding": "utf-8",
            "decode_responses": True,
            "retry_on_timeout": True,
            "retry_on_error": [
                redis.ConnectionError,
                redis.TimeoutError,
            ],
            "health_check_interval": 30,
        }
        
        # Environment-specific configurations
        if self.settings.is_production:
            base_config.update({
                "socket_timeout": 5.0,
                "socket_connect_timeout": 5.0,
                "socket_keepalive": True,
                "socket_keepalive_options": {
                    "TCP_KEEPIDLE": 60,
                    "TCP_KEEPINTVL": 30,
                    "TCP_KEEPCNT": 3,
                },
            })
        elif self.settings.is_development:
            base_config.update({
                "socket_timeout": 10.0,
                "socket_connect_timeout": 10.0,
            })
        
        return base_config
    
    @property
    def pool_kwargs(self) -> Dict[str, Any]:
        """Get Redis connection pool configuration."""
        return {
            "max_connections": self.settings.REDIS_MAX_CONNECTIONS,
            "retry_on_timeout": True,
            "retry_on_error": [
                redis.ConnectionError,
                redis.TimeoutError,
            ],
            **self.connection_kwargs
        }
    
    def create_connection_pool(self) -> ConnectionPool:
        """Create Redis connection pool."""
        if self._connection_pool is None:
            self._connection_pool = ConnectionPool.from_url(
                self.redis_url,
                **self.pool_kwargs
            )
        return self._connection_pool
    
    def create_redis_client(self) -> Redis:
        """Create Redis client with connection pool."""
        if self._redis_client is None:
            pool = self.create_connection_pool()
            self._redis_client = Redis(connection_pool=pool)
        return self._redis_client
    
    async def close_connections(self):
        """Close Redis connections and cleanup."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
        
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

class CacheConfig:
    """Cache configuration with TTL settings and key patterns."""
    
    # Cache TTL settings (in seconds)
    DEFAULT_TTL = settings.CACHE_DEFAULT_TTL
    PLANT_LIBRARY_TTL = settings.CACHE_PLANT_LIBRARY_TTL
    WEATHER_TTL = settings.CACHE_WEATHER_TTL
    API_RESPONSE_TTL = settings.CACHE_API_RESPONSE_TTL
    
    # Cache key patterns
    KEY_PATTERNS = {
        # User-related caches
        "user_profile": "user:profile:{user_id}",
        "user_session": "user:session:{session_id}",
        "user_preferences": "user:preferences:{user_id}",
        "user_subscription": "user:subscription:{user_id}",
        
        # Plant-related caches
        "plant_library": "plant:library:{species_id}",
        "plant_details": "plant:details:{plant_id}",
        "plant_collection": "user:plants:{user_id}",
        "plant_identification": "plant:identify:{image_hash}",
        
        # Care-related caches
        "care_schedule": "care:schedule:{plant_id}",
        "care_history": "care:history:{plant_id}:{date}",
        "care_reminders": "care:reminders:{user_id}",
        
        # Weather-related caches
        "weather_current": "weather:current:{lat}:{lon}",
        "weather_forecast": "weather:forecast:{lat}:{lon}",
        "weather_location": "weather:location:{location_key}",
        
        # API response caches
        "api_response": "api:{provider}:{endpoint}:{params_hash}",
        "api_rate_limit": "rate_limit:{user_id}:{api_provider}",
        
        # AI/ML caches
        "ai_chat_session": "ai:chat:{user_id}:{session_id}",
        "ai_recommendations": "ai:recommendations:{user_id}",
        
        # System caches
        "system_config": "system:config:{config_key}",
        "feature_flags": "system:flags:{flag_key}",
        "admin_session": "admin:session:{admin_id}",
    }
    
    # Cache TTL mappings
    TTL_MAPPINGS = {
        "user_profile": DEFAULT_TTL,
        "user_session": DEFAULT_TTL * 4,  # 4 hours
        "user_preferences": DEFAULT_TTL * 2,  # 2 hours
        "user_subscription": DEFAULT_TTL,
        
        "plant_library": PLANT_LIBRARY_TTL,
        "plant_details": DEFAULT_TTL,
        "plant_collection": DEFAULT_TTL // 2,  # 30 minutes
        "plant_identification": API_RESPONSE_TTL * 4,  # 20 minutes
        
        "care_schedule": DEFAULT_TTL,
        "care_history": DEFAULT_TTL * 2,
        "care_reminders": DEFAULT_TTL // 6,  # 10 minutes
        
        "weather_current": WEATHER_TTL,
        "weather_forecast": WEATHER_TTL * 2,
        "weather_location": WEATHER_TTL * 4,
        
        "api_response": API_RESPONSE_TTL,
        "api_rate_limit": 86400,  # 24 hours
        
        "ai_chat_session": DEFAULT_TTL,
        "ai_recommendations": DEFAULT_TTL * 2,
        
        "system_config": DEFAULT_TTL * 24,  # 24 hours
        "feature_flags": DEFAULT_TTL,
        "admin_session": DEFAULT_TTL * 2,
    }
    
    @classmethod
    def get_cache_key(cls, pattern_name: str, **kwargs) -> str:
        """
        Generate cache key from pattern and parameters.
        
        Args:
            pattern_name: Name of the key pattern
            **kwargs: Parameters to substitute in the pattern
            
        Returns:
            Formatted cache key string
        """
        if pattern_name not in cls.KEY_PATTERNS:
            raise ValueError(f"Unknown cache key pattern: {pattern_name}")
        
        pattern = cls.KEY_PATTERNS[pattern_name]
        try:
            return pattern.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing parameter {e} for pattern {pattern_name}")
    
    @classmethod
    def get_ttl(cls, pattern_name: str, custom_ttl: Optional[int] = None) -> int:
        """
        Get TTL for cache key pattern.
        
        Args:
            pattern_name: Name of the key pattern
            custom_ttl: Override TTL value
            
        Returns:
            TTL in seconds
        """
        if custom_ttl is not None:
            return custom_ttl
        
        return cls.TTL_MAPPINGS.get(pattern_name, cls.DEFAULT_TTL)


# =============================================================================
# REDIS UTILITIES
# =============================================================================

class RedisUtils:
    """Utility functions for Redis operations."""
    
    @staticmethod
    def serialize_value(value: Any) -> str:
        """
        Serialize Python object to JSON string for Redis storage.
        
        Args:
            value: Python object to serialize
            
        Returns:
            JSON string representation
        """
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize value: {e}")
    
    @staticmethod
    def deserialize_value(value: str, value_type: type = dict) -> Any:
        """
        Deserialize JSON string from Redis to Python object.
        
        Args:
            value: JSON string from Redis
            value_type: Expected type of the deserialized value
            
        Returns:
            Deserialized Python object
        """
        if not value:
            return None
        
        # Handle simple types
        if value_type in (str, int, float, bool):
            try:
                if value_type == bool:
                    return value.lower() in ('true', '1', 'yes')
                return value_type(value)
            except (ValueError, TypeError):
                return None
        
        # Handle complex types (JSON)
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value  # Return as string if JSON parsing fails
    
    @staticmethod
    def create_hash_key(*args) -> str:
        """
        Create a hash-based cache key from multiple arguments.
        
        Args:
            *args: Arguments to hash
            
        Returns:
            MD5 hash string
        """
        import hashlib
        
        # Convert all arguments to strings and join
        key_string = "|".join(str(arg) for arg in args)
        
        # Create MD5 hash
        return hashlib.md5(key_string.encode()).hexdigest()


# =============================================================================
# GLOBAL REDIS CONFIGURATION INSTANCE
# =============================================================================

# Global Redis configuration instance
redis_config = RedisConfig()
cache_config = CacheConfig()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_redis_client() -> Redis:
    """Get Redis client instance."""
    return redis_config.create_redis_client()


async def check_redis_health() -> Dict[str, Any]:
    """
    Check Redis connectivity and performance.
    
    Returns:
        Dict containing Redis health status and metrics
    """
    try:
        client = get_redis_client()
        
        # Test basic connectivity
        ping_result = await client.ping()
        
        # Get Redis info
        info = await client.info()
        
        # Get memory usage
        memory_info = {
            "used_memory": info.get("used_memory_human", "Unknown"),
            "used_memory_peak": info.get("used_memory_peak_human", "Unknown"),
            "total_system_memory": info.get("total_system_memory_human", "Unknown"),
        }
        
        # Test set/get operation
        test_key = "health_check_test"
        await client.set(test_key, "test_value", ex=60)
        test_value = await client.get(test_key)
        await client.delete(test_key)
        
        return {
            "status": "healthy",
            "ping": ping_result,
            "version": info.get("redis_version", "Unknown"),
            "memory": memory_info,
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "test_operation": test_value == "test_value",
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "type": type(e).__name__,
        }


# =============================================================================
# TESTING UTILITIES
# =============================================================================

async def clear_test_cache():
    """Clear all cache data (for testing only)."""
    if not settings.is_testing:
        raise RuntimeError("Cache clearing only allowed in test environment")
    
    client = get_redis_client()
    await client.flushdb()