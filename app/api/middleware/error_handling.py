# 📄 File: app/api/middleware/error_handling.py
# 🧭 Purpose (Layman Explanation): 
# This file catches any errors that happen in our app and turns them into friendly, consistent error messages
# that users can understand, like translating technical problems into helpful responses.
# 🧪 Purpose (Technical Summary): 
# Global error handling middleware that catches all exceptions, formats consistent error responses,
# logs errors appropriately, and provides request correlation for debugging and monitoring.
# 🔗 Dependencies: 
# FastAPI, starlette, app.shared.core.exceptions, logging, traceback, uuid
# 🔄 Connected Modules / Calls From: 
# app.main.py (middleware registration), all API endpoints, other middleware components

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncio

from app.shared.config.settings import get_settings
from app.shared.core.exceptions import (
    PlantCareException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ExternalAPIError as ExternalServiceError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware for the Plant Care API
    
    This middleware catches all unhandled exceptions and converts them
    into consistent, well-formatted JSON error responses. It also handles
    request correlation, error logging, and provides appropriate HTTP
    status codes for different error types.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Error type to HTTP status code mapping
        self.error_status_map = {
            ValidationError: 400,
            AuthenticationError: 401,
            AuthorizationError: 403,
            NotFoundError: 404,
            RateLimitError: 429,
            ExternalServiceError: 503,
            DatabaseError: 503,
            HTTPException: None,  # Use exception's status_code
            ValueError: 400,
            TypeError: 400,
            KeyError: 400,
            AttributeError: 500,
            ConnectionError: 503,
            TimeoutError: 504,
        }
        
        # Error messages for common exceptions
        self.error_messages = {
            ValidationError: "Request validation failed",
            AuthenticationError: "Authentication required",
            AuthorizationError: "Insufficient permissions",
            NotFoundError: "Resource not found",
            RateLimitError: "Rate limit exceeded",
            ExternalServiceError: "External service unavailable",
            DatabaseError: "Database service unavailable",
            ValueError: "Invalid request data",
            TypeError: "Invalid data type in request",
            KeyError: "Missing required field",
            AttributeError: "Internal server error",
            ConnectionError: "Service connection failed",
            TimeoutError: "Request timeout",
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and handle any exceptions that occur
        
        Args:
            request: HTTP request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response
        """
        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to request headers for downstream processing
        request.headers.__dict__["_list"].append(
            (b"x-request-id", request_id.encode())
        )
        
        start_time = datetime.now()
        
        try:
            # Process request through the rest of the middleware stack
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Add response time header
            processing_time = (datetime.now() - start_time).total_seconds()
            response.headers["X-Response-Time"] = f"{processing_time:.3f}s"
            
            return response
            
        except Exception as exc:
            # Handle the exception and return error response
            return await self._handle_exception(request, exc, request_id, start_time)
    
    async def _handle_exception(
        self, 
        request: Request, 
        exc: Exception, 
        request_id: str,
        start_time: datetime
    ) -> JSONResponse:
        """
        Handle exception and create appropriate error response
        
        Args:
            request: HTTP request
            exc: Exception that occurred
            request_id: Request correlation ID
            start_time: Request start time
            
        Returns:
            JSON error response
        """
        # Determine HTTP status code
        status_code = self._get_status_code(exc)
        
        # Get error details
        error_code, error_message, error_details = self._get_error_info(exc)
        
        # Log the error
        await self._log_error(request, exc, request_id, status_code)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Build error response
        error_response = {
            "error": {
                "code": error_code,
                "message": error_message,
                "details": error_details,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "path": str(request.url.path),
                "method": request.method
            }
        }
        
        # Add debug information in development
        if self.settings.DEBUG and self.settings.ENVIRONMENT != "production":
            error_response["error"]["debug"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc().split('\n')
            }
        
        # Create JSON response
        response = JSONResponse(
            status_code=status_code,
            content=error_response
        )
        
        # Add correlation headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{processing_time:.3f}s"
        response.headers["X-Error-Code"] = error_code
        
        return response
    
    def _get_status_code(self, exc: Exception) -> int:
        """
        Determine appropriate HTTP status code for exception
        
        Args:
            exc: Exception instance
            
        Returns:
            HTTP status code
        """
        # Check if it's an HTTPException with its own status code
        if isinstance(exc, HTTPException):
            return exc.status_code
        
        # Check custom PlantCare exceptions
        if isinstance(exc, PlantCareException):
            return exc.status_code
        
        # Check mapped exception types
        for exc_type, status_code in self.error_status_map.items():
            if isinstance(exc, exc_type):
                return status_code or 500
        
        # Default to 500 for unknown exceptions
        return 500
    
    def _get_error_info(self, exc: Exception) -> tuple[str, str, Dict[str, Any]]:
        """
        Extract error information from exception
        
        Args:
            exc: Exception instance
            
        Returns:
            Tuple of (error_code, error_message, error_details)
        """
        error_details = {}
        
        # Handle PlantCare custom exceptions
        if isinstance(exc, PlantCareException):
            return (
                exc.error_code,
                exc.message,
                exc.details or {}
            )
        
        # Handle FastAPI HTTPException
        if isinstance(exc, HTTPException):
            error_code = f"HTTP_{exc.status_code}"
            error_message = exc.detail
            if hasattr(exc, 'headers') and exc.headers:
                error_details["headers"] = exc.headers
            return error_code, error_message, error_details
        
        # Handle validation errors
        if hasattr(exc, 'errors') and callable(exc.errors):
            # Pydantic validation error
            error_code = "VALIDATION_ERROR"
            error_message = "Request validation failed"
            error_details = {"validation_errors": exc.errors()}
            return error_code, error_message, error_details
        
        # Handle common exception types
        exc_type = type(exc)
        if exc_type in self.error_messages:
            error_code = exc_type.__name__.upper()
            error_message = self.error_messages[exc_type]
        else:
            error_code = "INTERNAL_SERVER_ERROR"
            error_message = "An internal server error occurred"
        
        # Add exception message if available and safe to expose
        if str(exc) and not self._is_sensitive_error(exc):
            error_details["exception_message"] = str(exc)
        
        return error_code, error_message, error_details
    
    def _is_sensitive_error(self, exc: Exception) -> bool:
        """
        Check if error contains sensitive information that shouldn't be exposed
        
        Args:
            exc: Exception instance
            
        Returns:
            True if error is sensitive
        """
        sensitive_keywords = [
            "password", "token", "secret", "key", "auth",
            "database", "connection", "sql", "query"
        ]
        
        error_message = str(exc).lower()
        return any(keyword in error_message for keyword in sensitive_keywords)
    
    async def _log_error(
        self, 
        request: Request, 
        exc: Exception, 
        request_id: str,
        status_code: int
    ) -> None:
        """
        Log error with appropriate level and context
        
        Args:
            request: HTTP request
            exc: Exception that occurred
            request_id: Request correlation ID
            status_code: HTTP status code
        """
        # Prepare log context
        log_context = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "query_params": str(request.query_params) if request.query_params else None,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": self._get_client_ip(request),
            "status_code": status_code,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
        
        # Add user context if available
        if hasattr(request.state, "user") and request.state.user:
            log_context["user_id"] = getattr(request.state.user, "id", None)
        
        # Determine log level based on status code and exception type
        if status_code >= 500:
            # Server errors - log as error with full traceback
            logger.error(
                f"Server error in {request.method} {request.url.path}",
                extra=log_context,
                exc_info=True
            )
        elif status_code == 429:
            # Rate limit - log as warning
            logger.warning(
                f"Rate limit exceeded for {request.method} {request.url.path}",
                extra=log_context
            )
        elif status_code >= 400:
            # Client errors - log as info (not our fault)
            logger.info(
                f"Client error in {request.method} {request.url.path}",
                extra=log_context
            )
        else:
            # Unexpected case - log as warning
            logger.warning(
                f"Unexpected error handling for {request.method} {request.url.path}",
                extra=log_context
            )
        
        # Additional logging for specific exception types
        if isinstance(exc, (ConnectionError, TimeoutError, DatabaseError)):
            logger.error(
                f"Infrastructure error: {type(exc).__name__}",
                extra={**log_context, "infrastructure_error": True}
            )
        
        if isinstance(exc, ExternalServiceError):
            logger.warning(
                f"External service error: {exc.service_name if hasattr(exc, 'service_name') else 'unknown'}",
                extra={**log_context, "external_service_error": True}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request headers
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return "unknown"


# Utility functions for error handling
def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a standardized error response
    
    Args:
        error_code: Error code identifier
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        request_id: Request correlation ID
        
    Returns:
        JSON error response
    """
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if request_id:
        error_response["error"]["request_id"] = request_id
    
    response = JSONResponse(
        status_code=status_code,
        content=error_response
    )
    
    if request_id:
        response.headers["X-Request-ID"] = request_id
    
    response.headers["X-Error-Code"] = error_code
    
    return response


def handle_validation_error(exc, request_id: Optional[str] = None) -> JSONResponse:
    """
    Handle Pydantic validation errors
    
    Args:
        exc: Pydantic validation exception
        request_id: Request correlation ID
        
    Returns:
        JSON error response
    """
    error_details = {}
    
    if hasattr(exc, 'errors') and callable(exc.errors):
        # Format validation errors
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "validation_error"),
                "input": error.get("input")
            })
        error_details["validation_errors"] = validation_errors
    
    return create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details=error_details,
        request_id=request_id
    )


def handle_rate_limit_error(
    limit: str, 
    reset_time: Optional[datetime] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Handle rate limit exceeded errors
    
    Args:
        limit: Rate limit that was exceeded
        reset_time: When the rate limit resets
        request_id: Request correlation ID
        
    Returns:
        JSON error response with rate limit headers
    """
    error_details = {"rate_limit": limit}
    
    if reset_time:
        error_details["reset_time"] = reset_time.isoformat()
    
    response = create_error_response(
        error_code="RATE_LIMIT_EXCEEDED",
        message=f"Rate limit of {limit} exceeded. Please try again later.",
        status_code=429,
        details=error_details,
        request_id=request_id
    )
    
    # Add rate limit headers
    response.headers["X-Rate-Limit-Limit"] = limit
    response.headers["Retry-After"] = "60"  # Default retry after 60 seconds
    
    if reset_time:
        response.headers["X-Rate-Limit-Reset"] = str(int(reset_time.timestamp()))
    
    return response


# Exception handler decorators
def handle_exceptions(func):
    """
    Decorator to wrap async functions with exception handling
    
    Usage:
        @handle_exceptions
        async def my_endpoint():
            # endpoint logic
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
            raise
    
    return wrapper