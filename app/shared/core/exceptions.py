"""
Custom exception classes for Plant Care Application.
Provides specific exceptions for different error scenarios with proper HTTP status codes.
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status


class PlantCareException(Exception):
    """
    Base exception class for Plant Care Application.
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__.upper()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "status_code": self.status_code
            }
        }
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict()["error"]
        )


class AuthenticationError(PlantCareException):
    """
    Exception raised for authentication failures.
    Used when user credentials are invalid or missing.
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(PlantCareException):
    """
    Exception raised for authorization failures.
    Used when user lacks permission to access resources.
    """
    
    def __init__(
        self,
        message: str = "Access denied",
        resource: Optional[str] = None,
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if resource:
            details["resource"] = resource
        if required_permission:
            details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            error_code="AUTHORIZATION_ERROR"
        )


class ValidationError(PlantCareException):
    """
    Exception raised for data validation failures.
    Used when input data doesn't meet validation requirements.
    """
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_errors: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if validation_errors:
            details["validation_errors"] = validation_errors
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            error_code="VALIDATION_ERROR"
        )


class NotFoundError(PlantCareException):
    """
    Exception raised when requested resource is not found.
    Used for missing plants, users, or other entities.
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            error_code="NOT_FOUND_ERROR"
        )


class ConflictError(PlantCareException):
    """
    Exception raised for resource conflicts.
    Used when attempting to create duplicate resources or conflicting operations.
    """
    
    def __init__(
        self,
        message: str = "Resource conflict",
        resource_type: Optional[str] = None,
        conflict_field: Optional[str] = None,
        existing_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if resource_type:
            details["resource_type"] = resource_type
        if conflict_field:
            details["conflict_field"] = conflict_field
        if existing_value is not None:
            details["existing_value"] = str(existing_value)
        
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            error_code="CONFLICT_ERROR"
        )


class RateLimitError(PlantCareException):
    """
    Exception raised when rate limits are exceeded.
    Used for API rate limiting and request throttling.
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[str] = None,
        reset_time: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        if reset_time:
            details["reset_time"] = reset_time
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            error_code="RATE_LIMIT_ERROR"
        )


class ExternalAPIError(PlantCareException):
    """
    Exception raised for external API failures.
    Used when third-party services (PlantNet, Weather APIs) fail.
    """
    
    def __init__(
        self,
        message: str = "External API error",
        api_name: Optional[str] = None,
        api_status_code: Optional[int] = None,
        api_response: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if api_name:
            details["api_name"] = api_name
        if api_status_code:
            details["api_status_code"] = api_status_code
        if api_response:
            details["api_response"] = api_response
        
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
            error_code="EXTERNAL_API_ERROR"
        )


class DatabaseError(PlantCareException):
    """
    Exception raised for database operation failures.
    Used for connection issues, query failures, and constraint violations.
    """
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        constraint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        if constraint:
            details["constraint"] = constraint
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="DATABASE_ERROR"
        )


class CircuitBreakerError(PlantCareException):
    """
    Exception raised when circuit breaker is open.
    Used to prevent cascading failures in external service calls.
    """
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service_name: Optional[str] = None,
        failure_count: Optional[int] = None,
        reset_time: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if service_name:
            details["service_name"] = service_name
        if failure_count:
            details["failure_count"] = failure_count
        if reset_time:
            details["reset_time"] = reset_time
        
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            error_code="CIRCUIT_BREAKER_ERROR"
        )


class SubscriptionError(PlantCareException):
    """
    Exception raised for subscription-related issues.
    Used when premium features are accessed without subscription.
    """
    
    def __init__(
        self,
        message: str = "Premium subscription required",
        feature: Optional[str] = None,
        subscription_status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if feature:
            details["feature"] = feature
        if subscription_status:
            details["subscription_status"] = subscription_status
        
        super().__init__(
            message=message,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details=details,
            error_code="SUBSCRIPTION_ERROR"
        )


class FileUploadError(PlantCareException):
    """
    Exception raised for file upload failures.
    Used when file processing or storage operations fail.
    """
    
    def __init__(
        self,
        message: str = "File upload failed",
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        allowed_types: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if filename:
            details["filename"] = filename
        if file_size:
            details["file_size"] = file_size
        if allowed_types:
            details["allowed_types"] = allowed_types
        
        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
            error_code="FILE_UPLOAD_ERROR"
        )


class CacheError(PlantCareException):
    """
    Exception raised for caching system failures.
    Used when Redis or other caching operations fail.
    """
    
    def __init__(
        self,
        message: str = "Cache operation failed",
        operation: Optional[str] = None,
        cache_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if operation:
            details["operation"] = operation
        if cache_key:
            details["cache_key"] = cache_key
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="CACHE_ERROR"
        )


# Plant-specific exceptions
class PlantNotFoundError(NotFoundError):
    """Exception for when a plant is not found."""
    
    def __init__(self, plant_id: str):
        super().__init__(
            message=f"Plant with ID {plant_id} not found",
            resource_type="plant",
            resource_id=plant_id
        )


class UserNotFoundError(NotFoundError):
    """Exception for when a user is not found."""
    
    def __init__(self, user_id: str):
        super().__init__(
            message=f"User with ID {user_id} not found",
            resource_type="user",
            resource_id=user_id
        )


class InvalidCredentialsError(AuthenticationError):
    """Exception for invalid login credentials."""
    
    def __init__(self):
        super().__init__(
            message="Invalid email or password",
            details={"hint": "Please check your credentials and try again"}
        )


class InsufficientPermissionsError(AuthorizationError):
    """Exception for insufficient user permissions."""
    
    def __init__(self, required_role: str):
        super().__init__(
            message=f"This action requires {required_role} privileges",
            required_permission=required_role
        )


class PlantLimitExceededError(SubscriptionError):
    """Exception when free tier plant limit is exceeded."""
    
    def __init__(self, current_count: int, limit: int):
        super().__init__(
            message=f"Plant limit exceeded. You have {current_count} plants (limit: {limit})",
            feature="unlimited_plants",
            details={
                "current_count": current_count,
                "limit": limit,
                "upgrade_required": True
            }
        )


class APIQuotaExceededError(RateLimitError):
    """Exception when external API quota is exceeded."""
    
    def __init__(self, api_name: str, quota_type: str = "daily"):
        super().__init__(
            message=f"{api_name} API {quota_type} quota exceeded",
            details={
                "api_name": api_name,
                "quota_type": quota_type,
                "suggestion": "Try again tomorrow or upgrade to premium"
            }
        )


def handle_database_error(error: Exception) -> DatabaseError:
    """
    Convert database-specific errors to DatabaseError.
    
    Args:
        error: Original database exception
        
    Returns:
        DatabaseError: Standardized database error
    """
    error_msg = str(error)
    
    # Handle common database errors
    if "unique constraint" in error_msg.lower():
        return DatabaseError(
            message="Duplicate entry detected",
            operation="insert",
            constraint="unique"
        )
    elif "foreign key constraint" in error_msg.lower():
        return DatabaseError(
            message="Referenced record not found",
            operation="insert/update",
            constraint="foreign_key"
        )
    elif "connection" in error_msg.lower():
        return DatabaseError(
            message="Database connection failed",
            operation="connection"
        )
    else:
        return DatabaseError(
            message=f"Database operation failed: {error_msg}",
            operation="unknown"
        )


# Additional exceptions for API authentication and timeout
class APIAuthenticationError(AuthenticationError):
    """Exception raised when an external API request is not properly authenticated."""

    def __init__(self, api_name: str):
        super().__init__(
            message=f"Authentication failed for {api_name} API",
            details={"api_name": api_name}
        )


class APITimeoutError(ExternalAPIError):
    """Exception raised when an external API call times out."""

    def __init__(self, api_name: str, timeout_seconds: int = 10):
        super().__init__(
            message=f"{api_name} API request timed out after {timeout_seconds} seconds",
            api_name=api_name,
            details={
                "api_name": api_name,
                "timeout_seconds": timeout_seconds,
                "suggestion": "Retry after some time or check network"
            }
        )