# 📄 File: app/api/middleware/__init__.py
# 🧭 Purpose (Layman Explanation): 
# This file organizes all the middleware components that act like security guards and helpers for our API,
# checking things like user permissions, request limits, and logging what happens.
# 🧪 Purpose (Technical Summary): 
# Package initialization for API middleware components, providing centralized imports and configuration
# for authentication, rate limiting, logging, and error handling middleware.
# 🔗 Dependencies: 
# FastAPI middleware components, app.shared.core
# 🔄 Connected Modules / Calls From: 
# app.main.py, FastAPI application setup, middleware registration

"""
Plant Care Application API Middleware Package

This package contains all middleware components that process HTTP requests
and responses before they reach the API endpoints. Middleware provides
cross-cutting concerns like authentication, rate limiting, logging, and
error handling.

Middleware Components:
    - AuthenticationMiddleware: JWT token validation and user authentication
    - RateLimitingMiddleware: Request rate limiting per user and endpoint
    - RequestLoggingMiddleware: HTTP request and response logging
    - ErrorHandlingMiddleware: Centralized error handling and formatting
    - LocalizationMiddleware: Multi-language support and localization

Middleware Stack Order (applied in reverse order):
    1. ErrorHandlingMiddleware (outermost - catches all errors)
    2. RequestLoggingMiddleware (logs all requests/responses)
    3. RateLimitingMiddleware (enforces rate limits)
    4. AuthenticationMiddleware (validates authentication)
    5. LocalizationMiddleware (handles language preferences)
    6. Application Routes (innermost)

Usage:
    from app.api.middleware import (
        AuthenticationMiddleware,
        RateLimitingMiddleware,
        RequestLoggingMiddleware,
        ErrorHandlingMiddleware
    )
    
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitingMiddleware)
    app.add_middleware(AuthenticationMiddleware)
"""

from typing import Dict, Any, List, Optional

# Middleware package metadata
__version__ = "1.0.0"
__author__ = "Plant Care Team"
__description__ = "API Middleware Components for Plant Care Application"

# Middleware configuration constants
MIDDLEWARE_CONFIG = {
    "authentication": {
        "enabled": True,
        "jwt_algorithm": "HS256",
        "token_expiry_hours": 24,
        "refresh_token_expiry_days": 30,
        "exclude_paths": [
            "/health",
            "/health/live", 
            "/health/ready",
            "/health/startup",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/",
            "/"
        ]
    },
    "rate_limiting": {
        "enabled": True,
        "default_limit": "100/minute",
        "premium_limit": "500/minute", 
        "admin_limit": "1000/minute",
        "burst_limit": 10,
        "endpoint_specific_limits": {
            "/api/v1/auth/login": "5/minute",
            "/api/v1/auth/register": "3/minute",
            "/api/v1/plants/identify": "10/minute",
            "/api/v1/ai/chat": "30/minute"
        },
        "exclude_paths": [
            "/health",
            "/health/live",
            "/health/ready", 
            "/health/startup",
            "/metrics"
        ]
    },
    "logging": {
        "enabled": True,
        "log_requests": True,
        "log_responses": True,
        "log_request_body": False,  # Security: don't log sensitive data
        "log_response_body": False,
        "exclude_paths": [
            "/health",
            "/health/live",
            "/health/ready",
            "/health/startup"
        ],
        "sensitive_headers": [
            "authorization",
            "x-api-key",
            "cookie",
            "x-access-token"
        ]
    },
    "error_handling": {
        "enabled": True,
        "include_traceback": False,  # Only in development
        "log_errors": True,
        "custom_error_responses": True,
        "rate_limit_errors": True
    },
    "localization": {
        "enabled": True,
        "default_locale": "en",
        "supported_locales": ["en", "es", "fr", "de", "hi", "zh"],
        "detect_from_header": True,
        "detect_from_query": True,
        "query_param": "lang"
    }
}

# HTTP status codes for middleware responses
HTTP_STATUS_CODES = {
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "RATE_LIMITED": 429,
    "INTERNAL_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503
}

# Common HTTP headers used by middleware
COMMON_HEADERS = {
    "REQUEST_ID": "X-Request-ID",
    "RATE_LIMIT_REMAINING": "X-Rate-Limit-Remaining",
    "RATE_LIMIT_RESET": "X-Rate-Limit-Reset",
    "API_VERSION": "X-API-Version",
    "RESPONSE_TIME": "X-Response-Time",
    "CONTENT_LANGUAGE": "Content-Language",
    "USER_ID": "X-User-ID",
    "CORRELATION_ID": "X-Correlation-ID"
}

# Error message templates
ERROR_MESSAGES = {
    "AUTHENTICATION_REQUIRED": "Authentication required. Please provide a valid access token.",
    "AUTHENTICATION_INVALID": "Invalid or expired access token. Please login again.",
    "PERMISSION_DENIED": "Insufficient permissions to access this resource.",
    "RATE_LIMIT_EXCEEDED": "Rate limit exceeded. Please try again later.",
    "VALIDATION_ERROR": "Request validation failed. Please check your input data.",
    "INTERNAL_ERROR": "An internal server error occurred. Please try again later.",
    "SERVICE_UNAVAILABLE": "Service temporarily unavailable. Please try again later."
}

# Middleware execution order (lower numbers execute first)
MIDDLEWARE_ORDER = {
    "error_handling": 1,
    "request_logging": 2, 
    "rate_limiting": 3,
    "authentication": 4,
    "localization": 5
}

def get_middleware_config(middleware_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific middleware
    
    Args:
        middleware_name: Name of the middleware
        
    Returns:
        Middleware configuration dictionary
    """
    return MIDDLEWARE_CONFIG.get(middleware_name, {})

def is_middleware_enabled(middleware_name: str) -> bool:
    """
    Check if a middleware is enabled
    
    Args:
        middleware_name: Name of the middleware
        
    Returns:
        True if middleware is enabled, False otherwise
    """
    config = get_middleware_config(middleware_name)
    return config.get("enabled", False)

def should_exclude_path(middleware_name: str, path: str) -> bool:
    """
    Check if a path should be excluded from middleware processing
    
    Args:
        middleware_name: Name of the middleware
        path: Request path to check
        
    Returns:
        True if path should be excluded, False otherwise
    """
    config = get_middleware_config(middleware_name)
    exclude_paths = config.get("exclude_paths", [])
    
    # Check for exact matches and prefix matches
    for exclude_path in exclude_paths:
        if path == exclude_path or path.startswith(exclude_path + "/"):
            return True
    
    return False

def get_error_message(error_code: str) -> str:
    """
    Get error message for a given error code
    
    Args:
        error_code: Error code identifier
        
    Returns:
        Error message string
    """
    return ERROR_MESSAGES.get(error_code, "An unknown error occurred.")

def get_middleware_order() -> Dict[str, int]:
    """
    Get middleware execution order configuration
    
    Returns:
        Dictionary mapping middleware names to execution order
    """
    return MIDDLEWARE_ORDER.copy()

# Import middleware classes when needed (commented out until implemented)
# These imports will be uncommented as middleware components are implemented

# from .authentication import AuthenticationMiddleware
# from .rate_limiting import RateLimitingMiddleware  
# from .logging import RequestLoggingMiddleware
# from .error_handling import ErrorHandlingMiddleware
# from .localization import LocalizationMiddleware

# List of middleware classes (will be populated as components are implemented)
AVAILABLE_MIDDLEWARE = [
    # "AuthenticationMiddleware",
    # "RateLimitingMiddleware", 
    # "RequestLoggingMiddleware",
    # "ErrorHandlingMiddleware",
    # "LocalizationMiddleware"
]

def get_available_middleware() -> List[str]:
    """
    Get list of available middleware components
    
    Returns:
        List of available middleware class names
    """
    return AVAILABLE_MIDDLEWARE.copy()

def validate_middleware_config() -> Dict[str, Any]:
    """
    Validate middleware configuration
    
    Returns:
        Validation results with any configuration issues
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Validate that enabled middleware have required configuration
    for middleware_name, config in MIDDLEWARE_CONFIG.items():
        if config.get("enabled", False):
            # Check for required configuration keys
            if middleware_name == "authentication":
                required_keys = ["jwt_algorithm", "exclude_paths"]
                for key in required_keys:
                    if key not in config:
                        validation_results["errors"].append(
                            f"Authentication middleware missing required config: {key}"
                        )
                        validation_results["valid"] = False
            
            elif middleware_name == "rate_limiting":
                required_keys = ["default_limit", "exclude_paths"]
                for key in required_keys:
                    if key not in config:
                        validation_results["errors"].append(
                            f"Rate limiting middleware missing required config: {key}"
                        )
                        validation_results["valid"] = False
    
    # Check for middleware order conflicts
    order_values = list(MIDDLEWARE_ORDER.values())
    if len(order_values) != len(set(order_values)):
        validation_results["warnings"].append(
            "Duplicate middleware order values detected"
        )
    
    return validation_results

# Export commonly used items
__all__ = [
    "MIDDLEWARE_CONFIG",
    "HTTP_STATUS_CODES", 
    "COMMON_HEADERS",
    "ERROR_MESSAGES",
    "MIDDLEWARE_ORDER",
    "get_middleware_config",
    "is_middleware_enabled", 
    "should_exclude_path",
    "get_error_message",
    "get_middleware_order",
    "get_available_middleware",
    "validate_middleware_config"
]