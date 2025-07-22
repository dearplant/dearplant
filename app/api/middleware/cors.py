# 📄 File: app/api/middleware/cors.py
# 🧭 Purpose (Layman Explanation): 
# Manages cross-origin requests, allowing the plant care mobile app and web interfaces to safely communicate with the API from different domains
# 🧪 Purpose (Technical Summary): 
# Implements CORS (Cross-Origin Resource Sharing) middleware with configurable origins, methods, and headers for secure cross-domain API access
# 🔗 Dependencies: 
# FastAPI, starlette middleware, app.shared.core.config, typing
# 🔄 Connected Modules / Calls From: 
# app.main.py middleware registration, FastAPI application setup

import logging
from typing import List, Dict, Any, Optional, Union
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import Response as StarletteResponse

import os

logger = logging.getLogger(__name__)

class PlantCareCORSMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware for Plant Care Application with enhanced security and logging.
    Provides fine-grained control over cross-origin requests with environment-specific configurations.
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        allowed_origins: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        exposed_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        max_age: int = 600
    ):
        super().__init__(app)
        
        # Get environment from environment variable or default to development
        self.environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        # Default CORS configuration based on environment
        self.allowed_origins = allowed_origins or self._get_default_origins()
        self.allowed_methods = allowed_methods or [
            "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"
        ]
        self.allowed_headers = allowed_headers or [
            "Authorization",
            "Content-Type", 
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Mx-ReqToken",
            "Keep-Alive",
            "X-Requested-With",
            "If-Modified-Since",
            "X-API-Key",
            "X-Device-ID",
            "X-App-Version",
            "X-Platform"
        ]
        self.exposed_headers = exposed_headers or [
            "X-Total-Count",
            "X-Page-Count", 
            "X-Rate-Limit-Remaining",
            "X-Rate-Limit-Reset",
            "X-Request-ID"
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
        # Security settings
        self.strict_mode = self.environment == "production"
        self.log_cors_requests = self.environment in ["development", "staging"]
        
        logger.info(f"CORS Middleware initialized with {len(self.allowed_origins)} allowed origins")
        if self.log_cors_requests:
            logger.debug(f"Allowed origins: {self.allowed_origins}")
    
    def _get_default_origins(self) -> List[str]:
        """
        Get default allowed origins based on environment
        
        Returns:
            List of allowed origin URLs
        """
        if self.settings.environment == "production":
            return [
                "https://plantcare.app",
                "https://www.plantcare.app",
                "https://api.plantcare.app",
                "https://admin.plantcare.app",
                # Add your production mobile app schemes
                "plantcare://",
                "https://plantcare.vercel.app"
            ]
        elif self.environment == "staging":
            return [
                "https://staging.plantcare.app",
                "https://staging-admin.plantcare.app", 
                "http://localhost:3000",  # React/Next.js dev server
                "http://localhost:5173",  # Vite dev server
                "http://localhost:8080",  # Vue dev server
                "plantcare-staging://",
                "https://plantcare-staging.vercel.app"
            ]
        else:  # development
            return [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://localhost:5173",
                "http://localhost:8080",
                "http://localhost:8000",  # Self-reference for testing
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "plantcare-dev://",
                # Flutter web development
                "http://localhost:56000",
                "http://localhost:56001"
            ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process CORS for incoming requests
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            Response with appropriate CORS headers
        """
        origin = request.headers.get("Origin")
        method = request.method
        
        # Log CORS requests in development/staging
        if self.log_cors_requests and origin:
            logger.debug(f"CORS request: {method} {request.url.path} from {origin}")
        
        # Handle preflight OPTIONS requests
        if method == "OPTIONS":
            return self._handle_preflight(request, origin)
        
        # Process actual request
        response = await call_next(request)
        
        # Add CORS headers to response
        self._add_cors_headers(response, origin, request)
        
        return response
    
    def _handle_preflight(self, request: Request, origin: Optional[str]) -> StarletteResponse:
        """
        Handle CORS preflight OPTIONS requests
        
        Args:
            request: Preflight request
            origin: Request origin
            
        Returns:
            Preflight response with CORS headers
        """
        # Check if origin is allowed
        if not self._is_origin_allowed(origin):
            if self.strict_mode:
                logger.warning(f"CORS preflight rejected for origin: {origin}")
                return StarletteResponse(
                    status_code=403,
                    content="CORS origin not allowed"
                )
            else:
                # In development, log but allow
                logger.info(f"CORS allowing non-configured origin: {origin}")
        
        # Get requested method and headers
        requested_method = request.headers.get("Access-Control-Request-Method")
        requested_headers = request.headers.get("Access-Control-Request-Headers", "")
        
        # Validate requested method
        if requested_method and requested_method not in self.allowed_methods:
            logger.warning(f"CORS method not allowed: {requested_method}")
            return StarletteResponse(status_code=405)
        
        # Create preflight response
        response = StarletteResponse(status_code=200)
        
        # Add CORS headers
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not self.strict_mode:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        # Add exposed headers
        if self.exposed_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.exposed_headers)
        
        # Add custom headers for mobile apps
        response.headers["X-CORS-Preflight"] = "handled"
        response.headers["X-API-Version"] = "v1"
        
        logger.debug(f"CORS preflight handled for {origin}")
        return response
    
    def _add_cors_headers(self, response: Response, origin: Optional[str], request: Request) -> None:
        """
        Add CORS headers to actual response
        
        Args:
            response: Response to add headers to
            origin: Request origin
            request: Original request
        """
        # Add origin header
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not self.strict_mode and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not origin:
            # For same-origin requests or no origin header
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        # Add credentials header
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add exposed headers
        if self.exposed_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.exposed_headers)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        
        # Add API-specific headers
        response.headers["X-API-Version"] = "v1"
        response.headers["X-Powered-By"] = "PlantCare-API"
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """
        Check if origin is in allowed list
        
        Args:
            origin: Request origin
            
        Returns:
            True if origin is allowed
        """
        if not origin:
            return True  # No origin header (same-origin or mobile app)
        
        # Exact match
        if origin in self.allowed_origins:
            return True
        
        # Wildcard match for development
        if not self.strict_mode:
            # Allow localhost with any port in development
            if origin.startswith(("http://localhost:", "http://127.0.0.1:")):
                return True
            
            # Allow file:// protocol for mobile apps
            if origin.startswith("file://"):
                return True
        
        return False
    
    def add_allowed_origin(self, origin: str) -> None:
        """
        Dynamically add an allowed origin
        
        Args:
            origin: Origin URL to allow
        """
        if origin not in self.allowed_origins:
            self.allowed_origins.append(origin)
            logger.info(f"Added CORS origin: {origin}")
    
    def remove_allowed_origin(self, origin: str) -> None:
        """
        Dynamically remove an allowed origin
        
        Args:
            origin: Origin URL to remove
        """
        if origin in self.allowed_origins:
            self.allowed_origins.remove(origin)
            logger.info(f"Removed CORS origin: {origin}")
    
    def get_cors_info(self) -> Dict[str, Any]:
        """
        Get current CORS configuration info
        
        Returns:
            Dictionary with CORS configuration details
        """
        return {
            "allowed_origins": self.allowed_origins,
            "allowed_methods": self.allowed_methods,
            "allowed_headers": self.allowed_headers,
            "exposed_headers": self.exposed_headers,
            "allow_credentials": self.allow_credentials,
            "max_age": self.max_age,
            "strict_mode": self.strict_mode,
            "environment": self.environment
        }

# Convenience functions for FastAPI setup
def get_cors_middleware() -> PlantCareCORSMiddleware:
    """
    Get configured CORS middleware instance
    
    Returns:
        Configured CORS middleware
    """
    return PlantCareCORSMiddleware

def get_standard_cors_config() -> Dict[str, Any]:
    """
    Get standard CORS configuration for FastAPI CORSMiddleware
    
    Returns:
        CORS configuration dictionary
    """
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    if environment == "production":
        allowed_origins = [
            "https://plantcare.app",
            "https://www.plantcare.app",
            "https://admin.plantcare.app"
        ]
    elif environment == "staging":
        allowed_origins = [
            "https://staging.plantcare.app",
            "http://localhost:3000",
            "http://localhost:5173"
        ]
    else:  # development
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:3000"
        ]
    
    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-API-Key",
            "X-Device-ID",
            "X-App-Version"
        ],
        "expose_headers": [
            "X-Total-Count",
            "X-Rate-Limit-Remaining",
            "X-Request-ID"
        ]
    }