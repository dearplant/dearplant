# 📄 File: app/shared/core/exceptions.py
# 🧭 Purpose (Layman Explanation): 
# This file defines all the special error types our Plant Care app uses to communicate
# what went wrong in a clear, organized way instead of generic error messages.
# 🧪 Purpose (Technical Summary): 
# Custom exception hierarchy providing specific error types with HTTP status codes,
# error details, and proper serialization for API responses and error handling.
# 🔗 Dependencies: 
# FastAPI HTTPException, typing, HTTP status constants
# 🔄 Connected Modules / Calls From: 
# All modules for error handling, middleware, API endpoints, domain services

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


# =============================================================================
# AUTHENTICATION & AUTHORIZATION EXCEPTIONS
# =============================================================================

class AuthenticationError(PlantCareException):
    """
    Exception raised for authentication failures.
    Used when user credentials are invalid or missing.
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ):
        if not details:
            details = {}
        if user_id:
            details["user_id"] = user_id
            
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
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        required_permission: Optional[str] = None,
        required_action: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if resource:
            details["resource"] = resource
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        if required_permission:
            details["required_permission"] = required_permission
        if required_action:
            details["required_action"] = required_action
        if user_id:
            details["user_id"] = user_id
        
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            error_code="AUTHORIZATION_ERROR"
        )


class AccountLockedException(PlantCareException):
    """
    Exception raised when user account is locked.
    Used for security lockouts, suspicious activity, etc.
    """
    
    def __init__(
        self,
        message: str = "Account is locked",
        user_id: Optional[str] = None,
        lock_reason: Optional[str] = None,
        locked_until: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if user_id:
            details["user_id"] = user_id
        if lock_reason:
            details["lock_reason"] = lock_reason
        if locked_until:
            details["locked_until"] = locked_until
        
        super().__init__(
            message=message,
            status_code=status.HTTP_423_LOCKED,
            details=details,
            error_code="ACCOUNT_LOCKED"
        )


# =============================================================================
# VALIDATION & DATA EXCEPTIONS
# =============================================================================

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
        constraint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if constraint:
            details["constraint"] = constraint
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            error_code="VALIDATION_ERROR"
        )


class NotFoundError(PlantCareException):
    """
    Exception raised when requested resource is not found.
    Used for missing entities, files, endpoints, etc.
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
            error_code="NOT_FOUND"
        )


class DuplicateResourceError(PlantCareException):
    """
    Exception raised when attempting to create duplicate resources.
    Used for unique constraint violations, duplicate entries, etc.
    """
    
    def __init__(
        self,
        message: str = "Resource already exists",
        resource_type: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if resource_type:
            details["resource_type"] = resource_type
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            error_code="DUPLICATE_RESOURCE"
        )


# =============================================================================
# BUSINESS LOGIC EXCEPTIONS
# =============================================================================

class BusinessRuleViolationError(PlantCareException):
    """
    Exception raised when business rules are violated.
    Used for domain-specific rule enforcement.
    """
    
    def __init__(
        self,
        message: str = "Business rule violation",
        rule: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if rule:
            details["rule"] = rule
        if context:
            details["context"] = context
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            error_code="BUSINESS_RULE_VIOLATION"
        )


class SubscriptionError(PlantCareException):
    """
    Exception raised for subscription-related failures.
    Used when premium features require active subscription.
    """
    
    def __init__(
        self,
        message: str = "Subscription required",
        feature: Optional[str] = None,
        subscription_status: Optional[str] = None,
        required_plan: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if feature:
            details["feature"] = feature
        if subscription_status:
            details["subscription_status"] = subscription_status
        if required_plan:
            details["required_plan"] = required_plan
        
        super().__init__(
            message=message,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details=details,
            error_code="SUBSCRIPTION_ERROR"
        )


# =============================================================================
# EXTERNAL SERVICE EXCEPTIONS
# =============================================================================

class ExternalServiceError(PlantCareException):
    """
    Exception raised when external service calls fail.
    Used for API integrations, third-party services, etc.
    """
    
    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        service_response: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if service:
            details["service"] = service
        if service_response:
            details["service_response"] = service_response
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
            error_code="EXTERNAL_SERVICE_ERROR"
        )


class RateLimitError(PlantCareException):
    """
    Exception raised when rate limits are exceeded.
    Used for API throttling and abuse prevention.
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            error_code="RATE_LIMIT_EXCEEDED"
        )


# =============================================================================
# DATABASE & INFRASTRUCTURE EXCEPTIONS
# =============================================================================

class DatabaseError(PlantCareException):
    """
    Exception raised for database operation failures.
    Used for connection issues, query failures, etc.
    """
    
    def __init__(
        self,
        message: str = "Database error",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="DATABASE_ERROR"
        )


class CacheError(PlantCareException):
    """
    Exception raised for cache operation failures.
    Used for Redis connection issues, cache misses, etc.
    """
    
    def __init__(
        self,
        message: str = "Cache error",
        operation: Optional[str] = None,
        key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if operation:
            details["operation"] = operation
        if key:
            details["key"] = key
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="CACHE_ERROR"
        )


class FileStorageError(PlantCareException):
    """
    Exception raised for file storage operation failures.
    Used for upload/download errors, storage quota issues, etc.
    """
    
    def __init__(
        self,
        message: str = "File storage error",
        operation: Optional[str] = None,
        filename: Optional[str] = None,
        storage_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if operation:
            details["operation"] = operation
        if filename:
            details["filename"] = filename
        if storage_path:
            details["storage_path"] = storage_path
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="FILE_STORAGE_ERROR"
        )


# =============================================================================
# PLANT CARE SPECIFIC EXCEPTIONS
# =============================================================================

class PlantNotFoundError(NotFoundError):
    """
    Exception raised when plant is not found.
    Specialized NotFoundError for plant resources.
    """
    
    def __init__(
        self,
        plant_id: str,
        user_id: Optional[str] = None,
        message: Optional[str] = None
    ):
        if not message:
            message = f"Plant not found: {plant_id}"
        
        details = {"plant_id": plant_id}
        if user_id:
            details["user_id"] = user_id
        
        super().__init__(
            message=message,
            resource_type="plant",
            resource_id=plant_id,
            details=details
        )


class CareScheduleError(BusinessRuleViolationError):
    """
    Exception raised for care schedule violations.
    Used when care schedules conflict or are invalid.
    """
    
    def __init__(
        self,
        message: str = "Care schedule error",
        plant_id: Optional[str] = None,
        schedule_id: Optional[str] = None,
        conflict: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if plant_id:
            details["plant_id"] = plant_id
        if schedule_id:
            details["schedule_id"] = schedule_id
        if conflict:
            details["conflict"] = conflict
        
        super().__init__(
            message=message,
            rule="care_schedule_validation",
            context=details,
            details=details
        )


class PlantIdentificationError(ExternalServiceError):
    """
    Exception raised when plant identification fails.
    Used for AI service failures, invalid images, etc.
    """
    
    def __init__(
        self,
        message: str = "Plant identification failed",
        image_url: Optional[str] = None,
        provider: Optional[str] = None,
        confidence: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if image_url:
            details["image_url"] = image_url
        if provider:
            details["provider"] = provider
        if confidence:
            details["confidence"] = confidence
        
        super().__init__(
            message=message,
            service="plant_identification",
            details=details
        )


# =============================================================================
# EXCEPTION UTILITIES
# =============================================================================

def create_http_exception(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Utility function to create HTTPException with consistent format.
    
    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Optional error code
        details: Optional error details
        
    Returns:
        HTTPException: Formatted HTTP exception
    """
    error_response = {
        "code": error_code or f"HTTP_{status_code}",
        "message": message,
        "details": details or {}
    }
    
    return HTTPException(
        status_code=status_code,
        detail=error_response
    )


def exception_to_dict(exception: Exception) -> Dict[str, Any]:
    """
    Convert any exception to dictionary format.
    
    Args:
        exception: Exception to convert
        
    Returns:
        Dict: Exception data as dictionary
    """
    if isinstance(exception, PlantCareException):
        return exception.to_dict()
    
    return {
        "error": {
            "code": exception.__class__.__name__.upper(),
            "message": str(exception),
            "details": {},
            "status_code": 500
        }
    }


def is_client_error(exception: Exception) -> bool:
    """
    Check if exception represents a client error (4xx).
    
    Args:
        exception: Exception to check
        
    Returns:
        bool: True if client error, False otherwise
    """
    if isinstance(exception, PlantCareException):
        return 400 <= exception.status_code < 500
    
    if isinstance(exception, HTTPException):
        return 400 <= exception.status_code < 500
    
    return False


def is_server_error(exception: Exception) -> bool:
    """
    Check if exception represents a server error (5xx).
    
    Args:
        exception: Exception to check
        
    Returns:
        bool: True if server error, False otherwise
    """
    if isinstance(exception, PlantCareException):
        return 500 <= exception.status_code < 600
    
    if isinstance(exception, HTTPException):
        return 500 <= exception.status_code < 600
    
    return True  # Default to server error for unknown exceptions

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

class APIAuthenticationError(AuthenticationError):
    """Exception raised when an external API request is not properly authenticated."""

    def __init__(self, api_name: str):
        super().__init__(
            message=f"Authentication failed for {api_name} API",
            details={"api_name": api_name}
        )

class FileTooLargeError(PlantCareException):
    """
    Exception raised when uploaded file exceeds allowed size.
    """
    def __init__(
        self,
        message: str = "Uploaded file is too large",
        max_size_mb: Optional[float] = None,
        actual_size_mb: Optional[float] = None,
        filename: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}

        if max_size_mb is not None:
            details["max_size_mb"] = max_size_mb
        if actual_size_mb is not None:
            details["actual_size_mb"] = actual_size_mb
        if filename:
            details["filename"] = filename

        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
            error_code="FILE_TOO_LARGE"
        )


class FileProcessingError(PlantCareException):
    """
    Exception raised when file processing (e.g., parsing, reading) fails.
    """
    def __init__(
        self,
        message: str = "Failed to process the uploaded file",
        filename: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}

        if filename:
            details["filename"] = filename
        if operation:
            details["operation"] = operation

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            error_code="FILE_PROCESSING_ERROR"
        )


class InvalidFileTypeError(PlantCareException):
    """
    Exception raised when the uploaded file type is not supported.
    """
    def __init__(
        self,
        message: str = "Invalid or unsupported file type",
        filename: Optional[str] = None,
        expected_types: Optional[list] = None,
        actual_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}

        if filename:
            details["filename"] = filename
        if expected_types:
            details["expected_types"] = expected_types
        if actual_type:
            details["actual_type"] = actual_type

        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            error_code="INVALID_FILE_TYPE"
        )


class FileIntegrityError(PlantCareException):
    """
    Exception raised when uploaded file fails integrity checks (e.g., corruption).
    """
    def __init__(
        self,
        message: str = "Uploaded file is corrupted or incomplete",
        filename: Optional[str] = None,
        checksum: Optional[str] = None,
        expected_checksum: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}

        if filename:
            details["filename"] = filename
        if checksum:
            details["checksum"] = checksum
        if expected_checksum:
            details["expected_checksum"] = expected_checksum

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            error_code="FILE_INTEGRITY_ERROR"
        )


# =============================================================================
# STORAGE QUOTA EXCEPTION
# =============================================================================

class StorageQuotaExceededError(PlantCareException):
    """
    Exception raised when a user exceeds their allocated storage quota.
    """
    def __init__(
        self,
        message: str = "Storage quota exceeded",
        user_id: Optional[str] = None,
        max_quota_mb: Optional[float] = None,
        current_usage_mb: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}

        if user_id:
            details["user_id"] = user_id
        if max_quota_mb is not None:
            details["max_quota_mb"] = max_quota_mb
        if current_usage_mb is not None:
            details["current_usage_mb"] = current_usage_mb

        super().__init__(
            message=message,
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            details=details,
            error_code="STORAGE_QUOTA_EXCEEDED"
        )
class RepositoryError(PlantCareException):
    """
    Exception raised for repository/database operation failures.
    Used when database operations fail at the repository layer.
    """
    
    def __init__(
        self,
        message: str = "Repository operation failed",
        operation: Optional[str] = None,
        entity: Optional[str] = None,
        constraint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}
        
        if operation:
            details["operation"] = operation
        if entity:
            details["entity"] = entity
        if constraint:
            details["constraint"] = constraint
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="REPOSITORY_ERROR"
        )

class TransactionError(PlantCareException):
    """
    Exception raised when a database transaction fails.
    Used to wrap commit/rollback errors in DB sessions.
    """
    
    def __init__(
        self,
        message: str = "Database transaction failed",
        operation: Optional[str] = None,
        entity: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if not details:
            details = {}

        if operation:
            details["operation"] = operation
        if entity:
            details["entity"] = entity

        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            error_code="TRANSACTION_ERROR"
        )