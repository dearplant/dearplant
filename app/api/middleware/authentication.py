# 📄 File: app/api/middleware/authentication.py
# 🧭 Purpose (Layman Explanation): 
# This file acts like a security guard that checks if users have valid ID cards (tokens) before letting them
# access protected parts of our plant care app, like personal plant collections or premium features.
# 🧪 Purpose (Technical Summary): 
# Authentication middleware that validates JWT tokens, injects user context into requests,
# handles token refresh, and enforces authentication requirements for protected endpoints.
# 🔗 Dependencies: 
# FastAPI, python-jose, app.shared.core.security, app.shared.config.settings, supabase
# 🔄 Connected Modules / Calls From: 
# app.main.py (middleware registration), all protected API endpoints, user management module

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from jose import jwt, JWTError
import asyncio

from app.shared.config.settings import get_settings
from app.shared.core.security import verify_token, decode_token, TokenData
from app.shared.core.exceptions import AuthenticationError, AuthorizationError
from . import should_exclude_path, get_error_message

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token validation
    
    This middleware:
    - Validates JWT tokens from Authorization header or cookies
    - Injects authenticated user context into request state
    - Handles token refresh for near-expired tokens
    - Enforces authentication requirements for protected routes
    - Supports multiple authentication methods (Bearer token, cookies)
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Paths that don't require authentication
        self.public_paths = [
            "/health",
            "/health/live", 
            "/health/ready",
            "/health/startup",
            "/health/detailed",
            "/metrics",
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/",
            "/favicon.ico",
            "/api/v1/",
            "/api/v1/status",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/plants/library",  # Public plant library
            "/api/v1/content/public",  # Public content
        ]
        
        # Paths that require admin authentication
        self.admin_paths = [
            "/api/v1/admin",
        ]
        
        # Token refresh threshold (refresh if expires within this time)
        self.refresh_threshold = timedelta(minutes=15)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process authentication for incoming requests
        
        Args:
            request: HTTP request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response
        """
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Extract and validate token
        auth_result = await self._authenticate_request(request)
        
        if auth_result["authenticated"]:
            # Add user context to request state
            request.state.user = auth_result["user"]
            request.state.token_data = auth_result["token_data"]
            request.state.is_admin = auth_result.get("is_admin", False)
            request.state.is_premium = auth_result.get("is_premium", False)
            
            # Check admin access for admin paths
            if self._is_admin_path(request.url.path) and not auth_result.get("is_admin", False):
                return self._create_authorization_error("Admin access required")
            
            # Process request
            response = await call_next(request)
            
            # Add token refresh header if needed
            if auth_result.get("needs_refresh", False):
                response.headers["X-Token-Refresh-Suggested"] = "true"
            
            # Add user context headers
            response.headers["X-User-ID"] = str(auth_result["user"]["id"])
            if auth_result.get("is_premium"):
                response.headers["X-User-Type"] = "premium"
            if auth_result.get("is_admin"):
                response.headers["X-User-Type"] = "admin"
                
            return response
        
        else:
            # Authentication failed
            return self._create_authentication_error(
                auth_result.get("error", "Authentication required")
            )
    
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """
        Authenticate request and extract user information
        
        Args:
            request: HTTP request
            
        Returns:
            Authentication result dictionary
        """
        result = {
            "authenticated": False,
            "user": None,
            "token_data": None,
            "is_admin": False,
            "is_premium": False,
            "needs_refresh": False,
            "error": None
        }
        
        try:
            # Extract token from request
            token = self._extract_token(request)
            
            if not token:
                result["error"] = "No authentication token provided"
                return result
            
            # Verify and decode token
            token_data = await self._verify_token(token)
            
            if not token_data:
                result["error"] = "Invalid or expired token"
                return result
            
            # Get user information
            user_info = await self._get_user_info(token_data)
            
            if not user_info:
                result["error"] = "User not found or inactive"
                return result
            
            # Check if token needs refresh
            needs_refresh = self._check_token_refresh_needed(token_data)
            
            # Update result
            result.update({
                "authenticated": True,
                "user": user_info,
                "token_data": token_data,
                "is_admin": user_info.get("role") == "admin",
                "is_premium": user_info.get("subscription_status") == "premium",
                "needs_refresh": needs_refresh
            })
            
            return result
            
        except AuthenticationError as e:
            result["error"] = str(e)
            return result
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            result["error"] = "Authentication service unavailable"
            return result
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request headers or cookies
        
        Args:
            request: HTTP request
            
        Returns:
            JWT token string or None
        """
        # Try Authorization header first (Bearer token)
        authorization = request.headers.get("Authorization")
        if authorization:
            try:
                scheme, token = authorization.split()
                if scheme.lower() == "bearer":
                    return token
            except ValueError:
                pass
        
        # Try X-Access-Token header
        access_token = request.headers.get("X-Access-Token")
        if access_token:
            return access_token
        
        # Try cookies
        token_cookie = request.cookies.get("access_token")
        if token_cookie:
            return token_cookie
        
        return None
    
    async def _verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify JWT token and extract token data
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object or None if invalid
        """
        try:
            # Use shared security module to verify token
            token_data = await verify_token(token)
            return token_data
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    async def _get_user_info(self, token_data: TokenData) -> Optional[Dict[str, Any]]:
        """
        Get user information from token data
        
        Args:
            token_data: Validated token data
            
        Returns:
            User information dictionary or None
        """
        try:
            # In a real implementation, this would fetch from database
            # For now, we'll extract from token data
            user_info = {
                "id": token_data.user_id,
                "email": token_data.email,
                "role": getattr(token_data, "role", "user"),
                "subscription_status": getattr(token_data, "subscription_status", "free"),
                "is_active": getattr(token_data, "is_active", True),
                "permissions": getattr(token_data, "permissions", [])
            }
            
            # Check if user is active
            if not user_info["is_active"]:
                return None
            
            return user_info
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def _check_token_refresh_needed(self, token_data: TokenData) -> bool:
        """
        Check if token needs to be refreshed soon
        
        Args:
            token_data: Token data with expiration info
            
        Returns:
            True if token should be refreshed
        """
        try:
            if not hasattr(token_data, "exp") or not token_data.exp:
                return False
            
            # Convert expiration to datetime
            if isinstance(token_data.exp, int):
                exp_datetime = datetime.fromtimestamp(token_data.exp)
            else:
                exp_datetime = token_data.exp
            
            # Check if expires within refresh threshold
            time_until_expiry = exp_datetime - datetime.now()
            return time_until_expiry <= self.refresh_threshold
            
        except Exception as e:
            logger.warning(f"Error checking token refresh: {e}")
            return False
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if path is public (doesn't require authentication)
        
        Args:
            path: Request path
            
        Returns:
            True if path is public
        """
        # Check exact matches
        if path in self.public_paths:
            return True
        
        # Check prefix matches
        for public_path in self.public_paths:
            if path.startswith(public_path + "/"):
                return True
        
        # Check using middleware config
        return should_exclude_path("authentication", path)
    
    def _is_admin_path(self, path: str) -> bool:
        """
        Check if path requires admin authentication
        
        Args:
            path: Request path
            
        Returns:
            True if path requires admin access
        """
        for admin_path in self.admin_paths:
            if path.startswith(admin_path):
                return True
        return False
    
    def _create_authentication_error(self, message: str) -> JSONResponse:
        """
        Create authentication error response
        
        Args:
            message: Error message
            
        Returns:
            JSON error response
        """
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "AUTHENTICATION_REQUIRED",
                    "message": message,
                    "details": {
                        "auth_methods": ["Bearer token", "X-Access-Token header", "access_token cookie"]
                    },
                    "timestamp": datetime.now().isoformat()
                }
            },
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Auth-Required": "true"
            }
        )
    
    def _create_authorization_error(self, message: str) -> JSONResponse:
        """
        Create authorization error response
        
        Args:
            message: Error message
            
        Returns:
            JSON error response
        """
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": message,
                    "details": {},
                    "timestamp": datetime.now().isoformat()
                }
            },
            headers={
                "X-Auth-Required": "true"
            }
        )


# Utility functions for authentication
def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from request state
    
    Args:
        request: HTTP request
        
    Returns:
        User information or None if not authenticated
    """
    return getattr(request.state, "user", None)


def get_current_user_id(request: Request) -> Optional[str]:
    """
    Get current user ID from request state
    
    Args:
        request: HTTP request
        
    Returns:
        User ID or None if not authenticated
    """
    user = get_current_user(request)
    return user["id"] if user else None


def is_authenticated(request: Request) -> bool:
    """
    Check if request is authenticated
    
    Args:
        request: HTTP request
        
    Returns:
        True if authenticated
    """
    return get_current_user(request) is not None


def is_admin(request: Request) -> bool:
    """
    Check if current user is admin
    
    Args:
        request: HTTP request
        
    Returns:
        True if user is admin
    """
    return getattr(request.state, "is_admin", False)


def is_premium(request: Request) -> bool:
    """
    Check if current user has premium subscription
    
    Args:
        request: HTTP request
        
    Returns:
        True if user has premium subscription
    """
    return getattr(request.state, "is_premium", False)


def has_permission(request: Request, permission: str) -> bool:
    """
    Check if current user has specific permission
    
    Args:
        request: HTTP request
        permission: Permission to check
        
    Returns:
        True if user has permission
    """
    user = get_current_user(request)
    if not user:
        return False
    
    user_permissions = user.get("permissions", [])
    return permission in user_permissions or is_admin(request)


def require_authentication(func):
    """
    Decorator to require authentication for endpoint functions
    
    Usage:
        @require_authentication
        async def protected_endpoint(request: Request):
            # This will only execute if user is authenticated
    """
    async def wrapper(request: Request, *args, **kwargs):
        if not is_authenticated(request):
            raise AuthenticationError("Authentication required")
        return await func(request, *args, **kwargs)
    
    return wrapper


def require_admin(func):
    """
    Decorator to require admin role for endpoint functions
    
    Usage:
        @require_admin
        async def admin_endpoint(request: Request):
            # This will only execute if user is admin
    """
    async def wrapper(request: Request, *args, **kwargs):
        if not is_authenticated(request):
            raise AuthenticationError("Authentication required")
        if not is_admin(request):
            raise AuthorizationError("Admin access required")
        return await func(request, *args, **kwargs)
    
    return wrapper


def require_premium(func):
    """
    Decorator to require premium subscription for endpoint functions
    
    Usage:
        @require_premium
        async def premium_endpoint(request: Request):
            # This will only execute if user has premium subscription
    """
    async def wrapper(request: Request, *args, **kwargs):
        if not is_authenticated(request):
            raise AuthenticationError("Authentication required")
        if not is_premium(request):
            raise AuthorizationError("Premium subscription required")
        return await func(request, *args, **kwargs)
    
    return wrapper


def require_permission(permission: str):
    """
    Decorator to require specific permission for endpoint functions
    
    Args:
        permission: Required permission
        
    Usage:
        @require_permission("plants:manage")
        async def manage_plants_endpoint(request: Request):
            # This will only execute if user has plants:manage permission
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            if not is_authenticated(request):
                raise AuthenticationError("Authentication required")
            if not has_permission(request, permission):
                raise AuthorizationError(f"Permission required: {permission}")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# FastAPI dependency functions
async def get_current_user_dependency(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user
    
    Usage:
        @app.get("/profile")
        async def get_profile(user: dict = Depends(get_current_user_dependency)):
            return user
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_admin_user_dependency(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to get current admin user
    
    Usage:
        @app.get("/admin/stats")
        async def admin_stats(admin_user: dict = Depends(get_admin_user_dependency)):
            return stats
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_premium_user_dependency(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to get current premium user
    
    Usage:
        @app.get("/premium/features")
        async def premium_features(premium_user: dict = Depends(get_premium_user_dependency)):
            return features
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not is_premium(request):
        raise HTTPException(status_code=403, detail="Premium subscription required")
    return user