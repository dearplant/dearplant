# 📄 File: app/shared/utils/__init__.py

# 🧭 Purpose (Layman Explanation):
# This file sets up a collection of helpful tools and utilities that other parts of the app
# can use for common tasks like logging, data validation, and formatting.

# 🧪 Purpose (Technical Summary):
# Initializes the utilities package with common helper functions, validators, formatters,
# and logging utilities used across the Plant Care application.

# 🔗 Dependencies:
# - logging: Structured logging utilities
# - validators: Data validation functions
# - formatters: Data formatting utilities
# - helpers: General purpose helper functions

# 🔄 Connected Modules / Calls From:
# Used by: All application modules for logging, validation, formatting, and utility functions
# Core utilities for consistent data handling and application monitoring

"""
Shared Utilities Package

This package provides common utilities and helper functions used throughout
the Plant Care Application including:

- Structured logging with JSON formatting
- Data validation functions
- Data formatting utilities
- General helper functions
- Error handling utilities
- Performance utilities
"""

from typing import Any, Dict, List, Optional
import logging

# Version information
__version__ = "1.0.0"
__author__ = "Plant Care App Team"

# Package-level constants
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Common data types used across utilities
UtilResult = Dict[str, Any]
ValidationResult = Dict[str, Any]
FormatResult = Any

# Utility categories
UTILITY_CATEGORIES = {
    'logging': 'Structured logging and monitoring',
    'validation': 'Data validation and integrity checking',
    'formatting': 'Data formatting and transformation',
    'helpers': 'General purpose helper functions',
    'performance': 'Performance monitoring and optimization'
}

# Error codes for utility operations
UTILITY_ERROR_CODES = {
    'VALIDATION_ERROR': 'UTIL_VAL_001',
    'FORMATTING_ERROR': 'UTIL_FMT_002',
    'LOGGING_ERROR': 'UTIL_LOG_003',
    'HELPER_ERROR': 'UTIL_HLP_004',
    'PERFORMANCE_ERROR': 'UTIL_PRF_005'
}


class UtilityError(Exception):
    """Base exception for utility operations."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ValidationError(UtilityError):
    """Exception for validation errors."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, UTILITY_ERROR_CODES['VALIDATION_ERROR'])
        self.field = field
        self.value = value


class FormattingError(UtilityError):
    """Exception for formatting errors."""
    
    def __init__(self, message: str, input_data: Any = None):
        super().__init__(message, UTILITY_ERROR_CODES['FORMATTING_ERROR'])
        self.input_data = input_data


def get_utility_info() -> Dict[str, Any]:
    """Get information about available utilities."""
    return {
        'version': __version__,
        'categories': UTILITY_CATEGORIES,
        'error_codes': UTILITY_ERROR_CODES,
        'available_modules': [
            'logging',
            'validators', 
            'formatters',
            'helpers'
        ]
    }


def initialize_utilities() -> bool:
    """Initialize all utility modules."""
    try:
        # This will be called during application startup
        # to initialize logging and other utilities
        
        # Initialize logging first as other utilities may need it
        from .logging import setup_logging
        setup_logging()
        
        # Additional utility initialization can be added here
        
        return True
        
    except Exception as e:
        print(f"Failed to initialize utilities: {e}")
        return False


# Re-export commonly used utilities for convenience
try:
    from .logging import get_logger, setup_logging
    from .validators import validate_email, validate_phone, validate_uuid
    from .formatters import format_datetime, format_currency, format_file_size
    from .helpers import generate_id, safe_get, chunk_list
    
    __all__ = [
        # Classes
        'UtilityError',
        'ValidationError', 
        'FormattingError',
        
        # Functions
        'get_utility_info',
        'initialize_utilities',
        
        # Re-exported utilities
        'get_logger',
        'setup_logging',
        'validate_email',
        'validate_phone', 
        'validate_uuid',
        'format_datetime',
        'format_currency',
        'format_file_size',
        'generate_id',
        'safe_get',
        'chunk_list'
    ]
    
except ImportError:
    # Utilities not yet implemented, only export base functionality
    __all__ = [
        'UtilityError',
        'ValidationError',
        'FormattingError', 
        'get_utility_info',
        'initialize_utilities'
    ]