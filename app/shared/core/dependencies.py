"""
Common FastAPI dependencies for Plant Care Application.
Provides user authentication, database access, caching, and authorization utilities.
"""

import logging
from typing import Optional, Dict, Any, AsyncGenerator
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client
import redis.asyncio as redis

from .security import get_security_manager
from .exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    NotFoundError,
    SubscriptionError
)
from ..config.database import get_async_session
from ..config.redis import get_redis_client
from ..config.supabase import get_supabase_client
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI documentation
security = HTTPBearer()


class CurrentUser:
    """User information extracted from JWT token."""
    
    def __init__(
        self,
        user_id: str,
        email: str,
        is_active: bool = True,
        is_premium: bool = False,
        roles: Optional[list] = None,
        token_payload: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.email = email
        self.is_active = is_active
        self.is_premium = is_premium
        self.roles = roles or ["user"]
        self.token_payload = token_payload or {}
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.has_role("admin") or self.has_role("super_admin")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user info to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "is_active": self.is_active,
            "is_premium": self.is_premium,
            "roles": self.roles
        }


async def get_current_user(request: Request) -> CurrentUser:
    """
    Get current authenticated user from request state.
    This dependency assumes AuthenticationMiddleware has already validated the token.
    
    Args:
        request: FastAPI request object
        
    Returns:
        CurrentUser: Current user information
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    try:
        # Get user info from request state (set by AuthenticationMiddleware)
        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)
        is_active = getattr(request.state, "is_active", True)
        is_premium = getattr(request.state, "is_premium", False)
        user_roles = getattr(request.state, "user_roles", ["user"])
        token_payload = getattr(request.state, "token_payload", {})
        
        if not user_id:
            logger.warning("User ID not found in request state")
            raise AuthenticationError("User not authenticated")
        
        current_user = CurrentUser(
            user_id=user_id,
            email=user_email,
            is_active=is_active,
            is_premium=is_premium,
            roles=user_roles,
            token_payload=token_payload
        )
        
        logger.debug(f"Current user retrieved: {user_id}")
        return current_user
        
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        raise AuthenticationError("Invalid user session")


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Get current active user (not disabled/suspended).
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        CurrentUser: Active user information
        
    Raises:
        AuthorizationError: If user is not active
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.user_id}")
        raise AuthorizationError(
            "Your account is currently disabled. Please contact support."
        )
    
    return current_user


async def get_current_admin_user(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """
    Get current user with admin privileges.
    
    Args:
        current_user: Current active user
        
    Returns:
        CurrentUser: Admin user information
        
    Raises:
        AuthorizationError: If user is not an admin
    """
    if not current_user.is_admin():
        logger.warning(f"Non-admin user attempted admin access: {current_user.user_id}")
        raise AuthorizationError(
            "Admin privileges required for this action",
            required_permission="admin"
        )
    
    return current_user


async def get_current_premium_user(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """
    Get current user with premium subscription.
    
    Args:
        current_user: Current active user
        
    Returns:
        CurrentUser: Premium user information
        
    Raises:
        SubscriptionError: If user doesn't have premium subscription
    """
    if not current_user.is_premium:
        logger.info(f"Non-premium user attempted premium feature: {current_user.user_id}")
        raise SubscriptionError(
            "Premium subscription required for this feature",
            subscription_status="free"
        )
    
    return current_user


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with get_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> redis.Redis:
    """
    Dependency for Redis client.
    
    Returns:
        redis.Redis: Redis client instance
    """
    return get_redis_client()


async def get_supabase() -> Client:
    """
    Dependency for Supabase client.
    
    Returns:
        Client: Supabase client instance
    """
    return get_supabase_client()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify API key for external API access.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        dict: API key payload data
        
    Raises:
        AuthenticationError: If API key is invalid
    """
    try:
        security_manager = get_security_manager()
        api_key = credentials.credentials
        
        # Verify API key
        payload = security_manager.verify_api_key(api_key)
        
        logger.debug(f"API key verified for user: {payload.get('sub')}")
        return payload
        
    except Exception as e:
        logger.warning(f"API key verification failed: {e}")
        raise AuthenticationError("Invalid API key")


def require_role(required_role: str):
    """
    Dependency factory for role-based authorization.
    
    Args:
        required_role: Required role for access
        
    Returns:
        function: Dependency function
    """
    async def role_dependency(
        current_user: CurrentUser = Depends(get_current_active_user)
    ) -> CurrentUser:
        if not current_user.has_role(required_role):
            logger.warning(
                f"User {current_user.user_id} lacks required role: {required_role}"
            )
            raise AuthorizationError(
                f"Access denied. Required role: {required_role}",
                required_permission=required_role
            )
        return current_user
    
    return role_dependency


def require_any_role(required_roles: list):
    """
    Dependency factory for multiple role authorization.
    
    Args:
        required_roles: List of acceptable roles
        
    Returns:
        function: Dependency function
    """
    async def role_dependency(
        current_user: CurrentUser = Depends(get_current_active_user)
    ) -> CurrentUser:
        if not current_user.has_any_role(required_roles):
            logger.warning(
                f"User {current_user.user_id} lacks any required roles: {required_roles}"
            )
            raise AuthorizationError(
                f"Access denied. Required roles: {', '.join(required_roles)}",
                required_permission=f"any_of_{required_roles}"
            )
        return current_user
    
    return role_dependency


def require_premium_subscription(
    feature_name: Optional[str] = None
):
    """
    Dependency factory for premium feature access.
    
    Args:
        feature_name: Name of the premium feature
        
    Returns:
        function: Dependency function
    """
    async def premium_dependency(
        current_user: CurrentUser = Depends(get_current_active_user)
    ) -> CurrentUser:
        if not current_user.is_premium:
            logger.info(
                f"User {current_user.user_id} attempted premium feature: {feature_name}"
            )
            raise SubscriptionError(
                f"Premium subscription required for {feature_name or 'this feature'}",
                feature=feature_name,
                subscription_status="free"
            )
        return current_user
    
    return premium_dependency


def require_plant_ownership():
    """
    Dependency factory for plant ownership verification.
    This should be used with path parameters containing plant_id.
    
    Returns:
        function: Dependency function
    """
    async def ownership_dependency(
        plant_id: str,
        current_user: CurrentUser = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> CurrentUser:
        # Import here to avoid circular imports
        from ...modules.plant_management.infrastructure.database.models import Plant
        from sqlalchemy import select
        
        # Check if plant exists and belongs to user
        query = select(Plant).where(
            Plant.plant_id == plant_id,
            Plant.user_id == current_user.user_id,
            Plant.archived == False
        )
        result = await db.execute(query)
        plant = result.scalar_one_or_none()
        
        if not plant:
            logger.warning(
                f"User {current_user.user_id} attempted access to non-owned plant: {plant_id}"
            )
            raise NotFoundError(
                "Plant not found or access denied",
                resource_type="plant",
                resource_id=plant_id
            )
        
        return current_user
    
    return ownership_dependency


async def check_rate_limit(
    endpoint: str,
    limit: int = 100,
    window: str = "hour"
):
    """
    Dependency for endpoint-specific rate limiting.
    
    Args:
        endpoint: Endpoint identifier
        limit: Request limit
        window: Time window
        
    Returns:
        function: Dependency function
    """
    async def rate_limit_dependency(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user)
    ):
        # Rate limiting logic would be implemented here
        # This is a placeholder for the actual rate limiting
        logger.debug(f"Rate limit check for {endpoint}: {current_user.user_id}")
        return True
    
    return rate_limit_dependency


class PaginationParams:
    """Pagination parameters for list endpoints."""
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 20,
        max_limit: int = 100
    ):
        self.skip = max(0, skip)  # Ensure non-negative
        self.limit = min(max(1, limit), max_limit)  # Ensure within bounds
        
    def to_dict(self) -> Dict[str, int]:
        """Convert pagination params to dictionary."""
        return {
            "skip": self.skip,
            "limit": self.limit
        }


def get_pagination_params(
    skip: int = 0,
    limit: int = 20
) -> PaginationParams:
    """
    Dependency for pagination parameters.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        
    Returns:
        PaginationParams: Validated pagination parameters
    """
    return PaginationParams(skip=skip, limit=limit)


class SortParams:
    """Sorting parameters for list endpoints."""
    
    def __init__(
        self,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "asc"
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert sort params to dictionary."""
        return {
            "sort_by": self.sort_by,
            "sort_order": self.sort_order
        }


def get_sort_params(
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
) -> SortParams:
    """
    Dependency for sorting parameters.
    
    Args:
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        
    Returns:
        SortParams: Validated sorting parameters
    """
    return SortParams(sort_by=sort_by, sort_order=sort_order)


# Settings dependency
@lru_cache()
def get_app_settings():
    """
    Cached dependency for application settings.
    
    Returns:
        Settings: Application settings
    """
    return get_settings()


# Health check dependencies
async def get_system_health() -> Dict[str, Any]:
    """
    Dependency for system health information.
    
    Returns:
        dict: System health status
    """
    health_status = {
        "status": "healthy",
        "timestamp": logger.time(),
        "services": {}
    }
    
    try:
        # Check database connection
        async with get_async_session() as db:
            await db.execute("SELECT 1")
            health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    try:
        # Check Redis connection
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


# Request context dependencies
def get_request_id(request: Request) -> str:
    """
    Get request ID from request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        str: Request ID
    """
    return getattr(request.state, "request_id", "unknown")


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers first (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """
    Get user agent from request headers.
    
    Args:
        request: FastAPI request
        
    Returns:
        str: User agent string
    """
    return request.headers.get("User-Agent", "unknown")