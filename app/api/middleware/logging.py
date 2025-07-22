# 📄 File: app/api/middleware/logging.py
# 🧭 Purpose (Layman Explanation): 
# This file keeps a detailed diary of every request made to our plant care app, recording what was asked for,
# how long it took to respond, and if there were any problems - like a security camera for our API.
# 🧪 Purpose (Technical Summary): 
# Request logging middleware that captures HTTP requests/responses with structured logging,
# performance metrics, security filtering, and correlation tracking for monitoring and debugging.
# 🔗 Dependencies: 
# FastAPI, logging, datetime, json, app.shared.utils.logging, uuid
# 🔄 Connected Modules / Calls From: 
# app.main.py (middleware registration), all API endpoints, monitoring systems

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urlparse, parse_qs

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import StreamingResponse

from app.shared.config.settings import get_settings
from . import should_exclude_path, get_middleware_config

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware for comprehensive API monitoring
    
    Features:
    - Structured JSON logging
    - Request/response timing
    - User context tracking
    - Security-aware data filtering
    - Performance metrics
    - Error correlation
    - Configurable log levels
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Sensitive headers that should not be logged
        self.sensitive_headers = {
            "authorization",
            "x-api-key", 
            "x-access-token",
            "cookie",
            "x-auth-token",
            "x-refresh-token",
            "x-session-id"
        }
        
        # Sensitive query parameters
        self.sensitive_params = {
            "password",
            "token", 
            "api_key",
            "secret",
            "auth",
            "session"
        }
        
        # Content types to log body for
        self.loggable_content_types = {
            "application/json",
            "application/x-www-form-urlencoded",
            "text/plain"
        }
        
        # Maximum body size to log (to prevent huge logs)
        self.max_body_size = 10000  # 10KB
        
        # Performance thresholds for warnings
        self.slow_request_threshold = 2.0  # 2 seconds
        self.very_slow_request_threshold = 5.0  # 5 seconds
        
        # Request ID header
        self.request_id_header = "X-Request-ID"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process and log HTTP requests/responses
        
        Args:
            request: HTTP request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response
        """
        # Skip logging for excluded paths
        if should_exclude_path("logging", request.url.path):
            return await call_next(request)
        
        # Generate request ID if not present
        request_id = self._get_or_create_request_id(request)
        
        # Start timing
        start_time = time.time()
        start_datetime = datetime.now()
        
        # Prepare request log data
        request_data = await self._prepare_request_log_data(request, request_id, start_datetime)
        
        # Log request
        self._log_request(request_data)
        
        # Process request and handle response
        try:
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Prepare response log data
            response_data = await self._prepare_response_log_data(
                request, response, request_id, processing_time, start_datetime
            )
            
            # Log response
            self._log_response(response_data)
            
            # Add request ID to response headers
            response.headers[self.request_id_header] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            processing_time = time.time() - start_time
            error_data = self._prepare_error_log_data(
                request, e, request_id, processing_time, start_datetime
            )
            self._log_error(error_data)
            
            # Re-raise exception
            raise
    
    def _get_or_create_request_id(self, request: Request) -> str:
        """
        Get existing request ID or create new one
        
        Args:
            request: HTTP request
            
        Returns:
            Request ID string
        """
        # Check if request ID already exists in state (from error handling middleware)
        if hasattr(request.state, "request_id"):
            return request.state.request_id
        
        # Check headers
        request_id = request.headers.get(self.request_id_header.lower())
        if request_id:
            request.state.request_id = request_id
            return request_id
        
        # Generate new request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        return request_id
    
    async def _prepare_request_log_data(
        self, request: Request, request_id: str, timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Prepare structured log data for request
        
        Args:
            request: HTTP request
            request_id: Request correlation ID
            timestamp: Request timestamp
            
        Returns:
            Request log data dictionary
        """
        # Basic request info
        log_data = {
            "event_type": "http_request",
            "request_id": request_id,
            "timestamp": timestamp.isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": self._filter_sensitive_params(dict(request.query_params)),
            "headers": self._filter_sensitive_headers(dict(request.headers)),
            "client": self._get_client_info(request),
            "user_agent": request.headers.get("user-agent", ""),
        }
        
        # Add user context if available
        if hasattr(request.state, "user") and request.state.user:
            log_data["user"] = {
                "id": request.state.user.get("id"),
                "email": request.state.user.get("email"),
                "role": request.state.user.get("role", "user"),
                "is_premium": getattr(request.state, "is_premium", False),
                "is_admin": getattr(request.state, "is_admin", False)
            }
        
        # Add request body if appropriate
        if self.settings.ENVIRONMENT == "development":
            body = await self._get_request_body(request)
            if body:
                log_data["body"] = body
        
        # Add content type
        content_type = request.headers.get("content-type", "")
        if content_type:
            log_data["content_type"] = content_type.split(";")[0]  # Remove charset
        
        return log_data
    
    async def _prepare_response_log_data(
        self,
        request: Request,
        response: Response,
        request_id: str,
        processing_time: float,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Prepare structured log data for response
        
        Args:
            request: HTTP request
            response: HTTP response
            request_id: Request correlation ID
            processing_time: Processing time in seconds
            start_time: Request start time
            
        Returns:
            Response log data dictionary
        """
        log_data = {
            "event_type": "http_response",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time_ms": round(processing_time * 1000, 2),
            "response_headers": self._filter_response_headers(dict(response.headers)),
        }
        
        # Add user context if available
        if hasattr(request.state, "user") and request.state.user:
            log_data["user_id"] = request.state.user.get("id")
        
        # Add performance classification
        if processing_time > self.very_slow_request_threshold:
            log_data["performance"] = "very_slow"
        elif processing_time > self.slow_request_threshold:
            log_data["performance"] = "slow"
        else:
            log_data["performance"] = "normal"
        
        # Add response body in development (for small responses)
        if (self.settings.ENVIRONMENT == "development" and 
            response.status_code >= 400 and
            not isinstance(response, StreamingResponse)):
            try:
                # Only for JSON responses and small bodies
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    # Note: This is a simplified approach
                    # In practice, you might need to handle response body differently
                    pass
            except Exception:
                pass
        
        return log_data
    
    def _prepare_error_log_data(
        self,
        request: Request,
        exception: Exception,
        request_id: str,
        processing_time: float,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Prepare structured log data for errors
        
        Args:
            request: HTTP request
            exception: Exception that occurred
            request_id: Request correlation ID
            processing_time: Processing time in seconds
            start_time: Request start time
            
        Returns:
            Error log data dictionary
        """
        log_data = {
            "event_type": "http_error",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "processing_time_ms": round(processing_time * 1000, 2),
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
        }
        
        # Add user context if available
        if hasattr(request.state, "user") and request.state.user:
            log_data["user_id"] = request.state.user.get("id")
        
        # Add status code if it's an HTTP exception
        if hasattr(exception, "status_code"):
            log_data["status_code"] = exception.status_code
        
        return log_data
    
    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out sensitive headers from logging
        
        Args:
            headers: Request headers
            
        Returns:
            Filtered headers dictionary
        """
        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in self.sensitive_headers:
                filtered[key] = "[REDACTED]"
            elif "password" in key_lower or "secret" in key_lower:
                filtered[key] = "[REDACTED]"
            else:
                filtered[key] = value
        
        return filtered
    
    def _filter_response_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter response headers for logging
        
        Args:
            headers: Response headers
            
        Returns:
            Filtered headers dictionary
        """
        # Include only important headers, exclude sensitive ones
        important_headers = {
            "content-type",
            "content-length", 
            "cache-control",
            "x-request-id",
            "x-response-time",
            "x-rate-limit-remaining",
            "x-api-version"
        }
        
        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in important_headers:
                filtered[key] = value
        
        return filtered
    
    def _filter_sensitive_params(self, params: Dict[str, str]) -> Dict[str, str]:
        """
        Filter sensitive query parameters
        
        Args:
            params: Query parameters
            
        Returns:
            Filtered parameters dictionary
        """
        filtered = {}
        for key, value in params.items():
            key_lower = key.lower()
            if key_lower in self.sensitive_params:
                filtered[key] = "[REDACTED]"
            else:
                filtered[key] = value
        
        return filtered
    
    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Get request body for logging (if appropriate)
        
        Args:
            request: HTTP request
            
        Returns:
            Request body data or None
        """
        try:
            content_type = request.headers.get("content-type", "")
            
            # Only log certain content types
            if not any(ct in content_type for ct in self.loggable_content_types):
                return None
            
            # Check content length
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_body_size:
                return {"message": f"Body too large ({content_length} bytes)"}
            
            # Get body
            body = await request.body()
            if not body:
                return None
            
            # Try to parse JSON
            if "application/json" in content_type:
                try:
                    body_data = json.loads(body.decode("utf-8"))
                    # Filter sensitive fields
                    return self._filter_sensitive_body_data(body_data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return {"raw": body.decode("utf-8", errors="replace")[:1000]}
            
            # For form data
            elif "application/x-www-form-urlencoded" in content_type:
                try:
                    body_str = body.decode("utf-8")
                    parsed = parse_qs(body_str)
                    return self._filter_sensitive_params(
                        {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                    )
                except UnicodeDecodeError:
                    return {"raw": "Binary data"}
            
            # For plain text
            elif "text/plain" in content_type:
                try:
                    return {"text": body.decode("utf-8")[:1000]}
                except UnicodeDecodeError:
                    return {"raw": "Binary data"}
            
            return None
            
        except Exception as e:
            logger.warning(f"Error reading request body for logging: {e}")
            return None
    
    def _filter_sensitive_body_data(self, data: Any) -> Any:
        """
        Recursively filter sensitive data from request body
        
        Args:
            data: Request body data
            
        Returns:
            Filtered data
        """
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in self.sensitive_params):
                    filtered[key] = "[REDACTED]"
                else:
                    filtered[key] = self._filter_sensitive_body_data(value)
            return filtered
        elif isinstance(data, list):
            return [self._filter_sensitive_body_data(item) for item in data]
        else:
            return data
    
    def _get_client_info(self, request: Request) -> Dict[str, Any]:
        """
        Get client information from request
        
        Args:
            request: HTTP request
            
        Returns:
            Client information dictionary
        """
        client_info = {}
        
        # Get IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_info["ip"] = forwarded_for.split(",")[0].strip()
        elif request.headers.get("x-real-ip"):
            client_info["ip"] = request.headers.get("x-real-ip")
        elif request.client:
            client_info["ip"] = request.client.host
        else:
            client_info["ip"] = "unknown"
        
        # Get port if available
        if request.client and request.client.port:
            client_info["port"] = request.client.port
        
        # Get forwarded protocol
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto:
            client_info["protocol"] = forwarded_proto
        
        return client_info
    
    def _log_request(self, log_data: Dict[str, Any]) -> None:
        """
        Log request data
        
        Args:
            log_data: Request log data
        """
        extra_data = {
            "request_id": log_data["request_id"],
            "user_id": log_data.get("user", {}).get("id"),
            "method": log_data["method"],
            "path": log_data["path"],
            "client_ip": log_data["client"].get("ip"),
        }
        
        logger.info(
            f"HTTP Request: {log_data['method']} {log_data['path']}",
            extra={
                "structured_data": log_data,
                **extra_data
            }
        )
    
    def _log_response(self, log_data: Dict[str, Any]) -> None:
        """
        Log response data
        
        Args:
            log_data: Response log data
        """
        extra_data = {
            "request_id": log_data["request_id"],
            "user_id": log_data.get("user_id"),
            "method": log_data["method"],
            "path": log_data["path"],
            "status_code": log_data["status_code"],
            "processing_time_ms": log_data["processing_time_ms"],
        }
        
        # Choose log level based on status code and performance
        if log_data["status_code"] >= 500:
            log_level = logging.ERROR
        elif log_data["status_code"] >= 400:
            log_level = logging.WARNING
        elif log_data.get("performance") == "very_slow":
            log_level = logging.WARNING
        elif log_data.get("performance") == "slow":
            log_level = logging.INFO
        else:
            log_level = logging.INFO
        
        logger.log(
            log_level,
            f"HTTP Response: {log_data['method']} {log_data['path']} -> {log_data['status_code']} ({log_data['processing_time_ms']}ms)",
            extra={
                "structured_data": log_data,
                **extra_data
            }
        )
    
    def _log_error(self, log_data: Dict[str, Any]) -> None:
        """
        Log error data
        
        Args:
            log_data: Error log data
        """
        extra_data = {
            "request_id": log_data["request_id"],
            "user_id": log_data.get("user_id"),
            "method": log_data["method"],
            "path": log_data["path"],
            "exception_type": log_data["exception_type"],
            "processing_time_ms": log_data["processing_time_ms"],
        }
        
        logger.error(
            f"HTTP Error: {log_data['method']} {log_data['path']} -> {log_data['exception_type']}: {log_data['exception_message']}",
            extra={
                "structured_data": log_data,
                **extra_data
            }
        )


# Utility functions for request logging
def get_request_id(request: Request) -> Optional[str]:
    """
    Get request ID from request state
    
    Args:
        request: HTTP request
        
    Returns:
        Request ID or None
    """
    return getattr(request.state, "request_id", None)


def log_custom_event(
    event_type: str,
    message: str,
    request: Optional[Request] = None,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log custom application event
    
    Args:
        event_type: Type of event
        message: Log message
        request: HTTP request (optional)
        data: Additional data (optional)
    """
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "message": message,
    }
    
    if data:
        log_data.update(data)
    
    extra_data = {}
    
    if request:
        request_id = get_request_id(request)
        if request_id:
            log_data["request_id"] = request_id
            extra_data["request_id"] = request_id
        
        if hasattr(request.state, "user") and request.state.user:
            log_data["user_id"] = request.state.user.get("id")
            extra_data["user_id"] = request.state.user.get("id")
    
    logger.info(
        message,
        extra={
            "structured_data": log_data,
            **extra_data
        }
    )


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "ms",
    request: Optional[Request] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log performance metric
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Metric unit
        request: HTTP request (optional)
        additional_data: Additional metric data (optional)
    """
    metric_data = {
        "event_type": "performance_metric",
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "timestamp": datetime.now().isoformat(),
    }
    
    if additional_data:
        metric_data.update(additional_data)
    
    log_custom_event("performance_metric", f"{metric_name}: {value}{unit}", request, metric_data)


# Context manager for timing operations
class LoggedOperation:
    """Context manager for logging operation timing"""
    
    def __init__(self, operation_name: str, request: Optional[Request] = None):
        self.operation_name = operation_name
        self.request = request
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.time() - self.start_time) * 1000  # Convert to ms
            
            if exc_type:
                log_custom_event(
                    "operation_error",
                    f"Operation '{self.operation_name}' failed after {duration:.2f}ms",
                    self.request,
                    {
                        "operation": self.operation_name,
                        "duration_ms": duration,
                        "exception_type": exc_type.__name__ if exc_type else None,
                        "exception_message": str(exc_val) if exc_val else None
                    }
                )
            else:
                log_performance_metric(
                    f"operation_{self.operation_name}",
                    duration,
                    "ms",
                    self.request,
                    {"operation": self.operation_name}
                )