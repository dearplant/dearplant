# 📄 File: app/shared/utils/validators.py

# 🧭 Purpose (Layman Explanation):
# This file contains smart checkers that make sure the data entered into the app is correct and safe,
# like verifying email addresses are real, phone numbers are valid, and plant names make sense.

# 🧪 Purpose (Technical Summary):
# Comprehensive data validation functions for user input, API data, and internal data integrity
# with support for email, phone, UUID, plant data, and custom validation rules.

# 🔗 Dependencies:
# - re: Regular expression patterns for validation
# - uuid: UUID validation and parsing
# - email-validator: Email validation library
# - phonenumbers: Phone number validation

# 🔄 Connected Modules / Calls From:
# Used by: User registration, Plant data entry, API request validation, Database model validation,
# Form validation across all modules
# 📄 File: app/shared/utils/validators.py
# 🧭 Purpose (Layman Explanation): 
# This file contains validation functions that check if data is correct and safe before storing it in the database,
# like checking if email addresses are valid, passwords are strong enough, or plant names are appropriate.
# 🧪 Purpose (Technical Summary): 
# Implements common validation functions for data integrity, input sanitization, and business rule enforcement
# across all modules, providing reusable validation logic with comprehensive error handling.
# 🔗 Dependencies: 
# re, typing, datetime, uuid, email-validator, pydantic, PIL (for image validation)
# 🔄 Connected Modules / Calls From: 
# All domain models, API schemas, database repositories, file upload handlers, user input processing

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from email_validator import validate_email, EmailNotValidError
from pydantic import ValidationError
import mimetypes
from pathlib import Path
import json

# Password validation patterns
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_PATTERNS = {
    'uppercase': re.compile(r'[A-Z]'),
    'lowercase': re.compile(r'[a-z]'),
    'digit': re.compile(r'\d'),
    'special': re.compile(r'[!@#$%^&*(),.?":{}|<>]'),
    'no_spaces': re.compile(r'^\S+$')
}

# Text validation patterns
PLANT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\.\']{1,100}$')
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
SLUG_PATTERN = re.compile(r'^[a-z0-9\-]+$')
PHONE_PATTERN = re.compile(r'^\+?1?-?\.?\s?\(?([0-9]{3})\)?[-\.\s]?([0-9]{3})[-\.\s]?([0-9]{4})$')

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_DOCUMENT_TYPES = {'application/pdf', 'text/plain', 'application/json'}
DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js'}

# Plant care validation constants
CARE_FREQUENCIES = ['daily', 'weekly', 'bi-weekly', 'monthly', 'seasonal', 'yearly']
HEALTH_STATUSES = ['excellent', 'good', 'fair', 'poor', 'critical']
GROWTH_STAGES = ['seed', 'seedling', 'vegetative', 'flowering', 'fruiting', 'dormant']


class ValidationError(Exception):
    """Custom validation error with detailed information"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class ValidationResult:
    """Result object for validation operations"""
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)


# ==============================================================================
# EMAIL AND CONTACT VALIDATION
# ==============================================================================

def validate_email_address(email: str) -> ValidationResult:
    """
    Validate email address format and deliverability
    
    Args:
        email: Email address to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not email or not isinstance(email, str):
        result.add_error("Email address is required")
        return result
    
    email = email.strip().lower()
    
    # Basic format validation
    if len(email) > 254:
        result.add_error("Email address is too long (max 254 characters)")
    
    try:
        # Use email-validator for comprehensive validation
        valid_email = validate_email(email)
        # Update with normalized email
        email = valid_email.email
    except EmailNotValidError as e:
        result.add_error(f"Invalid email format: {str(e)}")
    
    return result


def validate_phone_number(phone: str, country_code: str = 'US') -> ValidationResult:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
        country_code: Country code for validation (default: US)
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not phone or not isinstance(phone, str):
        result.add_error("Phone number is required")
        return result
    
    phone = phone.strip()
    
    # Remove common formatting characters
    cleaned_phone = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    # Basic length validation
    if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
        result.add_error("Phone number must be between 10-15 digits")
    
    # Pattern validation (US format for now)
    if not PHONE_PATTERN.match(phone):
        result.add_error("Invalid phone number format")
    
    return result


# ==============================================================================
# PASSWORD AND SECURITY VALIDATION
# ==============================================================================

def validate_password(password: str, username: str = None) -> ValidationResult:
    """
    Validate password strength and security requirements
    
    Args:
        password: Password to validate
        username: Username to check against (optional)
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not password or not isinstance(password, str):
        result.add_error("Password is required")
        return result
    
    # Length validation
    if len(password) < PASSWORD_MIN_LENGTH:
        result.add_error(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    
    if len(password) > PASSWORD_MAX_LENGTH:
        result.add_error(f"Password must be no more than {PASSWORD_MAX_LENGTH} characters long")
    
    # Pattern validations
    if not PASSWORD_PATTERNS['uppercase'].search(password):
        result.add_error("Password must contain at least one uppercase letter")
    
    if not PASSWORD_PATTERNS['lowercase'].search(password):
        result.add_error("Password must contain at least one lowercase letter")
    
    if not PASSWORD_PATTERNS['digit'].search(password):
        result.add_error("Password must contain at least one digit")
    
    if not PASSWORD_PATTERNS['special'].search(password):
        result.add_error("Password must contain at least one special character")
    
    if not PASSWORD_PATTERNS['no_spaces'].match(password):
        result.add_error("Password cannot contain spaces")
    
    # Username similarity check
    if username and username.lower() in password.lower():
        result.add_error("Password cannot contain username")
    
    # Common password check (basic patterns)
    common_patterns = ['password', '123456', 'qwerty', 'admin', 'login']
    if any(pattern in password.lower() for pattern in common_patterns):
        result.add_warning("Password contains common patterns that may be weak")
    
    return result


def validate_api_key(api_key: str) -> ValidationResult:
    """
    Validate API key format and structure
    
    Args:
        api_key: API key to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not api_key or not isinstance(api_key, str):
        result.add_error("API key is required")
        return result
    
    api_key = api_key.strip()
    
    # Length validation (typical API keys are 32-128 characters)
    if len(api_key) < 16 or len(api_key) > 256:
        result.add_error("API key must be between 16-256 characters")
    
    # Character validation (alphanumeric and common symbols)
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', api_key):
        result.add_error("API key contains invalid characters")
    
    return result


# ==============================================================================
# TEXT AND NAME VALIDATION
# ==============================================================================

def validate_plant_name(name: str) -> ValidationResult:
    """
    Validate plant name format and content
    
    Args:
        name: Plant name to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not name or not isinstance(name, str):
        result.add_error("Plant name is required")
        return result
    
    name = name.strip()
    
    # Length validation
    if len(name) < 1 or len(name) > 100:
        result.add_error("Plant name must be between 1-100 characters")
    
    # Pattern validation
    if not PLANT_NAME_PATTERN.match(name):
        result.add_error("Plant name contains invalid characters (only letters, numbers, spaces, hyphens, dots, and apostrophes allowed)")
    
    # Content validation
    if name.lower() in ['test', 'temp', 'delete', 'admin']:
        result.add_warning("Plant name appears to be a placeholder or system name")
    
    return result


def validate_username(username: str) -> ValidationResult:
    """
    Validate username format and availability
    
    Args:
        username: Username to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not username or not isinstance(username, str):
        result.add_error("Username is required")
        return result
    
    username = username.strip().lower()
    
    # Length validation
    if len(username) < 3 or len(username) > 30:
        result.add_error("Username must be between 3-30 characters")
    
    # Pattern validation
    if not USERNAME_PATTERN.match(username):
        result.add_error("Username can only contain letters, numbers, and underscores")
    
    # Reserved usernames
    reserved_names = ['admin', 'root', 'system', 'api', 'www', 'mail', 'ftp']
    if username in reserved_names:
        result.add_error("Username is reserved and cannot be used")
    
    return result


def validate_text_content(content: str, min_length: int = 1, max_length: int = 5000, 
                         allow_html: bool = False) -> ValidationResult:
    """
    Validate text content for length and safety
    
    Args:
        content: Text content to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        allow_html: Whether HTML tags are allowed
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not content or not isinstance(content, str):
        if min_length > 0:
            result.add_error("Content is required")
        return result
    
    content = content.strip()
    
    # Length validation
    if len(content) < min_length:
        result.add_error(f"Content must be at least {min_length} characters long")
    
    if len(content) > max_length:
        result.add_error(f"Content must be no more than {max_length} characters long")
    
    # HTML validation
    if not allow_html and ('<' in content and '>' in content):
        result.add_error("HTML tags are not allowed in this content")
    
    # Basic security check for script injection
    dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']
    if any(pattern in content.lower() for pattern in dangerous_patterns):
        result.add_error("Content contains potentially dangerous code")
    
    return result


# ==============================================================================
# NUMERIC AND DATE VALIDATION
# ==============================================================================

def validate_uuid(uuid_string: str) -> ValidationResult:
    """
    Validate UUID format
    
    Args:
        uuid_string: UUID string to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not uuid_string or not isinstance(uuid_string, str):
        result.add_error("UUID is required")
        return result
    
    try:
        uuid.UUID(uuid_string)
    except ValueError:
        result.add_error("Invalid UUID format")
    
    return result


def validate_decimal(value: Union[str, int, float, Decimal], min_value: Decimal = None, 
                    max_value: Decimal = None, decimal_places: int = 2) -> ValidationResult:
    """
    Validate decimal/numeric values
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        decimal_places: Maximum decimal places allowed
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if value is None:
        result.add_error("Numeric value is required")
        return result
    
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        result.add_error("Invalid numeric format")
        return result
    
    # Range validation
    if min_value is not None and decimal_value < min_value:
        result.add_error(f"Value must be at least {min_value}")
    
    if max_value is not None and decimal_value > max_value:
        result.add_error(f"Value must be no more than {max_value}")
    
    # Decimal places validation
    if decimal_places is not None:
        scale = decimal_value.as_tuple().exponent
        if scale < -decimal_places:
            result.add_error(f"Value cannot have more than {decimal_places} decimal places")
    
    return result


def validate_date(date_value: Union[str, datetime, date], 
                 min_date: date = None, max_date: date = None,
                 future_allowed: bool = True) -> ValidationResult:
    """
    Validate date values and ranges
    
    Args:
        date_value: Date to validate
        min_date: Minimum allowed date
        max_date: Maximum allowed date
        future_allowed: Whether future dates are allowed
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if date_value is None:
        result.add_error("Date is required")
        return result
    
    # Convert string to date if needed
    if isinstance(date_value, str):
        try:
            if 'T' in date_value:  # ISO format with time
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
            else:
                date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            result.add_error("Invalid date format (use YYYY-MM-DD)")
            return result
    elif isinstance(date_value, datetime):
        date_value = date_value.date()
    
    # Range validation
    if min_date and date_value < min_date:
        result.add_error(f"Date must be on or after {min_date}")
    
    if max_date and date_value > max_date:
        result.add_error(f"Date must be on or before {max_date}")
    
    # Future date validation
    if not future_allowed and date_value > date.today():
        result.add_error("Future dates are not allowed")
    
    return result


# ==============================================================================
# FILE AND UPLOAD VALIDATION
# ==============================================================================

def validate_file_upload(filename: str, file_size: int, content_type: str = None,
                         allowed_types: List[str] = None) -> ValidationResult:
    """
    Validate file upload parameters
    
    Args:
        filename: Original filename
        file_size: File size in bytes
        content_type: MIME content type
        allowed_types: List of allowed MIME types
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not filename or not isinstance(filename, str):
        result.add_error("Filename is required")
        return result
    
    # File size validation
    if file_size <= 0:
        result.add_error("File is empty")
    elif file_size > MAX_FILE_SIZE:
        result.add_error(f"File size exceeds maximum allowed size ({MAX_FILE_SIZE // (1024*1024)}MB)")
    
    # Filename validation
    if len(filename) > 255:
        result.add_error("Filename is too long (max 255 characters)")
    
    # Extension validation
    file_path = Path(filename)
    extension = file_path.suffix.lower()
    
    if extension in DANGEROUS_EXTENSIONS:
        result.add_error(f"File type '{extension}' is not allowed for security reasons")
    
    # MIME type validation
    if content_type:
        if allowed_types and content_type not in allowed_types:
            result.add_error(f"File type '{content_type}' is not allowed")
        
        # Check if MIME type matches extension
        expected_type, _ = mimetypes.guess_type(filename)
        if expected_type and expected_type != content_type:
            result.add_warning(f"File extension doesn't match content type")
    
    return result


def validate_image_file(filename: str, file_size: int, content_type: str = None) -> ValidationResult:
    """
    Validate image file specifically
    
    Args:
        filename: Image filename
        file_size: File size in bytes
        content_type: MIME content type
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = validate_file_upload(filename, file_size, content_type, list(ALLOWED_IMAGE_TYPES))
    
    # Additional image-specific validations
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        result.add_error("Only JPEG, PNG, WebP, and GIF images are allowed")
    
    # File extension check
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    extension = Path(filename).suffix.lower()
    if extension not in allowed_extensions:
        result.add_error(f"Image file extension '{extension}' is not allowed")
    
    return result


# ==============================================================================
# PLANT CARE SPECIFIC VALIDATION
# ==============================================================================

def validate_care_frequency(frequency: str) -> ValidationResult:
    """
    Validate plant care frequency values
    
    Args:
        frequency: Care frequency to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not frequency or not isinstance(frequency, str):
        result.add_error("Care frequency is required")
        return result
    
    frequency = frequency.lower().strip()
    
    if frequency not in CARE_FREQUENCIES:
        result.add_error(f"Invalid care frequency. Must be one of: {', '.join(CARE_FREQUENCIES)}")
    
    return result


def validate_health_status(status: str) -> ValidationResult:
    """
    Validate plant health status values
    
    Args:
        status: Health status to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not status or not isinstance(status, str):
        result.add_error("Health status is required")
        return result
    
    status = status.lower().strip()
    
    if status not in HEALTH_STATUSES:
        result.add_error(f"Invalid health status. Must be one of: {', '.join(HEALTH_STATUSES)}")
    
    return result


def validate_growth_stage(stage: str) -> ValidationResult:
    """
    Validate plant growth stage values
    
    Args:
        stage: Growth stage to validate
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if not stage or not isinstance(stage, str):
        result.add_error("Growth stage is required")
        return result
    
    stage = stage.lower().strip()
    
    if stage not in GROWTH_STAGES:
        result.add_error(f"Invalid growth stage. Must be one of: {', '.join(GROWTH_STAGES)}")
    
    return result


def validate_plant_measurement(measurement: Union[str, int, float], 
                              measurement_type: str) -> ValidationResult:
    """
    Validate plant measurement values (height, width, etc.)
    
    Args:
        measurement: Measurement value
        measurement_type: Type of measurement (height, width, etc.)
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if measurement is None:
        # Measurements are optional
        return result
    
    try:
        value = float(measurement)
    except (ValueError, TypeError):
        result.add_error(f"Invalid {measurement_type} measurement format")
        return result
    
    # Reasonable range validation
    if value < 0:
        result.add_error(f"{measurement_type} cannot be negative")
    elif value > 10000:  # 10 meters in cm
        result.add_error(f"{measurement_type} value seems unreasonably large")
    
    return result


# ==============================================================================
# JSON AND DATA STRUCTURE VALIDATION
# ==============================================================================

def validate_json_structure(json_data: Union[str, dict], required_keys: List[str] = None,
                           max_depth: int = 10) -> ValidationResult:
    """
    Validate JSON data structure and format
    
    Args:
        json_data: JSON data to validate (string or dict)
        required_keys: List of required top-level keys
        max_depth: Maximum allowed nesting depth
        
    Returns:
        ValidationResult with validation status and errors
    """
    result = ValidationResult(True)
    
    if json_data is None:
        result.add_error("JSON data is required")
        return result
    
    # Parse JSON if string
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON format: {str(e)}")
            return result
    else:
        data = json_data
    
    # Check if it's a dictionary
    if not isinstance(data, dict):
        result.add_error("JSON data must be an object/dictionary")
        return result
    
    # Required keys validation
    if required_keys:
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            result.add_error(f"Missing required keys: {', '.join(missing_keys)}")
    
    # Depth validation (recursive function)
    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            return False
        if isinstance(obj, dict):
            return all(check_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            return all(check_depth(item, current_depth + 1) for item in obj)
        return True
    
    if not check_depth(data):
        result.add_error(f"JSON structure exceeds maximum depth of {max_depth}")
    
    return result


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed_file"
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[^\w\-_\.\s]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('._')
    
    # Ensure filename length
    if len(filename) > 100:
        name, ext = Path(filename).stem[:95], Path(filename).suffix
        filename = f"{name}{ext}"
    
    return filename or "unnamed_file"


def validate_bulk_data(data_list: List[Dict[str, Any]], 
                      validation_func, max_items: int = 1000) -> ValidationResult:
    """
    Validate a list of data items using a validation function
    
    Args:
        data_list: List of data items to validate
        validation_func: Function to validate each item
        max_items: Maximum number of items allowed
        
    Returns:
        ValidationResult with aggregated validation status
    """
    result = ValidationResult(True)
    
    if not isinstance(data_list, list):
        result.add_error("Data must be a list")
        return result
    
    if len(data_list) > max_items:
        result.add_error(f"Too many items (max {max_items} allowed)")
        return result
    
    # Validate each item
    for i, item in enumerate(data_list):
        try:
            item_result = validation_func(item)
            if not item_result.is_valid:
                for error in item_result.errors:
                    result.add_error(f"Item {i + 1}: {error}")
        except Exception as e:
            result.add_error(f"Item {i + 1}: Validation error - {str(e)}")
    
    return result


def create_validation_summary(results: List[ValidationResult]) -> Dict[str, Any]:
    """
    Create a summary of multiple validation results
    
    Args:
        results: List of ValidationResult objects
        
    Returns:
        Dictionary with validation summary
    """
    total_results = len(results)
    valid_results = sum(1 for r in results if r.is_valid)
    
    all_errors = []
    all_warnings = []
    
    for result in results:
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
    
    return {
        'total_validations': total_results,
        'valid_count': valid_results,
        'invalid_count': total_results - valid_results,
        'success_rate': valid_results / total_results if total_results > 0 else 0,
        'total_errors': len(all_errors),
        'total_warnings': len(all_warnings),
        'errors': all_errors,
        'warnings': all_warnings,
        'is_all_valid': valid_results == total_results
    }