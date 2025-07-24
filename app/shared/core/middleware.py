"""
Custom middleware for Plant Care Application.
Provides authentication, rate limiting, logging, CORS, and security headers.
"""

import time
import logging
import json
import uuid
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from .security import get_security_manager
from .exceptions import AuthenticationError, RateLimitError
from .rate_limiter import get_rate_limiter
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token validation.
    Automatically validates tokens for protected endpoints.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_manager = get_security_manager()
        self.settings = get_settings()
        
        # Endpoints that don't require authentication
        self.public_endpoints = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/plant-library/search",  # Public plant search
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process authentication for incoming requests."""
        
        # Skip authentication for public endpoints
        if request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization: str = request.headers.get("Authorization")
        
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "MISSING_TOKEN",
                        "message": "Authorization header required",
                        "details": {"header": "Authorization: Bearer <token>"}
                    }
                }
            )
        
        try:
            # Validate Bearer token format
            if not authorization.startswith("Bearer "):
                raise AuthenticationError("Invalid authorization header format")
            
            token = authorization.split(" ")[1]
            
            # Verify token
            payload = self.security_manager.verify_token(token)
            
            # Add user info to request state
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.is_active = payload.get("active", True)
            request.state.is_premium = payload.get("premium", False)
            request.state.user_roles = payload.get("roles", ["user"])
            request.state.token_payload = payload
            
            logger.debug(f"User authenticated: {request.state.user_id}")
            
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "Invalid or expired token",
                        "details": {"hint": "Please login again"}
                    }
                }
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with user-specific and global limits.
    Prevents abuse and ensures fair usage across users.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limiter = get_rate_limiter()
        self.settings = get_settings()
        
        # Endpoints exempt from rate limiting
        self.exempt_endpoints = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to incoming requests."""
        
        # Skip rate limiting for exempt endpoints
        if request.url.path in self.exempt_endpoints:
            return await call_next(request)
        
        # Get identifier for rate limiting
        user_id = getattr(request.state, "user_id", None)
        client_ip = request.client.host if request.client else "unknown"
        
        # Use user_id for authenticated requests, IP for anonymous
        identifier = user_id if user_id else f"ip_{client_ip}"
        
        # Determine rate limit based on endpoint and user status
        is_premium = getattr(request.state, "is_premium", False)
        endpoint_path = request.url.path
        method = request.method
        
        # Define rate limits
        if endpoint_path.startswith("/api/v1/ai/"):
            # AI endpoints have stricter limits
            limit = 100 if is_premium else 20
            window = "hour"
        elif endpoint_path.startswith("/api/v1/external-api/"):
            # External API calls are limited
            limit = 200 if is_premium else 50
            window = "hour"
        elif method in ["POST", "PUT", "DELETE"]:
            # Write operations
            limit = 1000 if is_premium else 200
            window = "hour"
        else:
            # Read operations
            limit = 2000 if is_premium else 500
            window = "hour"
        
        try:
            # Check rate limit
            allowed = await self.rate_limiter.is_allowed(
                identifier=identifier,
                limit=limit,
                window=window,
                endpoint=endpoint_path
            )
            
            if not allowed:
                # Get remaining time until reset
                reset_time = await self.rate_limiter.get_reset_time(identifier, window)
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded: {limit} requests per {window}",
                            "details": {
                                "limit": limit,
                                "window": window,
                                "reset_time": reset_time,
                                "upgrade_hint": "Consider upgrading to premium for higher limits" if not is_premium else None
                            }
                        }
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time)
                    }
                )
            
            # Record the request
            remaining = await self.rate_limiter.record_request(identifier, limit, window)
            
            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting on error
            return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/response logging middleware with structured logging.
    Logs all API requests with timing, status, and user context.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log incoming requests and responses."""
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Capture request start time
        start_time = time.time()
        
        # Extract request information
        method = request.method
        url = str(request.url)
        path = request.url.path
        query_params = dict(request.query_params)
        headers = dict(request.headers)
        
        # Get user information if available
        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)
        client_ip = request.client.host if request.client else "unknown"
        
        # Remove sensitive headers from logging
        safe_headers = {
            k: v for k, v in headers.items() 
            if k.lower() not in ["authorization", "cookie", "x-api-key"]
        }
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "url": url,
                "query_params": query_params,
                "headers": safe_headers,
                "user_id": user_id,
                "user_email": user_email,
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Process request and capture response
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": round(process_time, 4),
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for enhanced security.
    Adds various security headers to all responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to responses."""
        
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Enforce HTTPS (if in production)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if self.settings.environment == "production" else None,
            
            # Content Security Policy
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            
            # Server identification
            "Server": f"PlantCareAPI/{self.settings.APP_VERSION}",
        }
        
        # Add headers to response
        for header, value in security_headers.items():
            if value:  # Only add headers with values
                response.headers[header] = value
        
        return response


class CORSCustomMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware with environment-specific origins.
    Handles CORS headers for cross-origin requests.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Define allowed origins based on environment
        if self.settings.environment == "development":
            self.allowed_origins = [
                "http://localhost:3000",  # React dev server
                "http://localhost:3001",  # Alternative React port
                "http://127.0.0.1:3000",
                "http://localhost:8080",  # Vue/Angular dev server
            ]
        elif self.settings.environment == "staging":
            self.allowed_origins = [
                "https://staging.plantcare.app",
                "https://staging-admin.plantcare.app"
            ]
        else:  # production
            self.allowed_origins = [
                "https://plantcare.app",
                "https://www.plantcare.app", 
                "https://admin.plantcare.app"
            ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS headers for cross-origin requests."""
        
        origin = request.headers.get("origin")
        
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = Response()
            
            if origin and origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With, X-Request-ID"
                response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
            
            return response
        
        # Process normal requests
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Process-Time, X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    Catches unhandled exceptions and converts them to proper HTTP responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle unhandled exceptions globally."""
        
        try:
            return await call_next(request)
            
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
            
        except Exception as e:
            # Log unexpected errors
            request_id = getattr(request.state, "request_id", "unknown")
            user_id = getattr(request.state, "user_id", "anonymous")
            
            logger.error(
                "Unhandled exception",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            # Return generic error response
            error_response = {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id
                }
            }
            
            # Include error details in development
            if self.settings.environment == "development":
                error_response["error"]["details"] = {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response
            )