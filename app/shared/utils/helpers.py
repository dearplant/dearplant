# 📄 File: app/shared/utils/helpers.py

# 🧭 Purpose (Layman Explanation):
# This file contains helpful tools and shortcuts that make common programming tasks easier,
# like generating unique IDs, safely getting data from dictionaries, and splitting lists into smaller chunks.

# 🧪 Purpose (Technical Summary):
# General purpose utility functions for common operations including ID generation, data manipulation,
# safe operations, retry logic, and various helper functions used across the application.

# 🔗 Dependencies:
# - uuid: Unique identifier generation
# - secrets: Secure random generation
# - hashlib: Hashing functions
# - asyncio: Async utilities
# - typing: Type hints

# 🔄 Connected Modules / Calls From:
# Used by: All application modules for common operations, data manipulation, ID generation,
# Safe data access, retry logic, and general utility functions

import asyncio
import hashlib
import secrets
import string
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from uuid import uuid4, uuid5, NAMESPACE_DNS
import json
import re
from pathlib import Path

from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

# Type variables for generic functions
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class HelperError(Exception):
    """Exception for helper function errors."""
    pass


# ID and token generation functions
def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique identifier with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part
    
    Returns:
        Generated unique ID
    """
    random_part = secrets.token_urlsafe(length)[:length]
    if prefix:
        return f"{prefix}_{random_part}"
    return random_part


def generate_uuid(namespace: str = None, name: str = None) -> str:
    """
    Generate UUID with optional namespace and name.
    
    Args:
        namespace: Namespace for UUID5 generation
        name: Name for UUID5 generation
    
    Returns:
        Generated UUID string
    """
    if namespace and name:
        return str(uuid5(NAMESPACE_DNS, f"{namespace}:{name}"))
    return str(uuid4())


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure token.
    
    Args:
        length: Token length
    
    Returns:
        Secure token string
    """
    return secrets.token_urlsafe(length)


def generate_random_string(
    length: int = 10,
    include_digits: bool = True,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_symbols: bool = False,
    custom_chars: str = None
) -> str:
    """
    Generate random string with specified character sets.
    
    Args:
        length: String length
        include_digits: Include digits (0-9)
        include_uppercase: Include uppercase letters (A-Z)
        include_lowercase: Include lowercase letters (a-z)
        include_symbols: Include symbols (!@#$%^&*)
        custom_chars: Custom character set
    
    Returns:
        Random string
    """
    if custom_chars:
        chars = custom_chars
    else:
        chars = ""
        if include_lowercase:
            chars += string.ascii_lowercase
        if include_uppercase:
            chars += string.ascii_uppercase
        if include_digits:
            chars += string.digits
        if include_symbols:
            chars += "!@#$%^&*"
    
    if not chars:
        raise HelperError("No character set specified for random string generation")
    
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    Generate URL-friendly slug from text.
    
    Args:
        text: Text to convert to slug
        max_length: Maximum slug length
    
    Returns:
        URL-friendly slug
    """
    if not text:
        return ""
    
    # Convert to lowercase
    slug = text.lower()
    
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Truncate if necessary
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    
    return slug


def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """
    Generate hash of data using specified algorithm.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
    
    Returns:
        Hash string
    """
    if algorithm not in ['md5', 'sha1', 'sha256', 'sha512']:
        raise HelperError(f"Unsupported hash algorithm: {algorithm}")
    
    hash_func = getattr(hashlib, algorithm)
    return hash_func(data.encode('utf-8')).hexdigest()


# Safe data access functions
def safe_get(
    data: Union[Dict, List],
    key: Union[str, int, List],
    default: Any = None,
    raise_on_error: bool = False
) -> Any:
    """
    Safely get value from dictionary or list with support for nested keys.
    
    Args:
        data: Dictionary or list to get value from
        key: Key, index, or list of keys for nested access
        default: Default value if key not found
        raise_on_error: Whether to raise exception on error
    
    Returns:
        Value from data or default
    """
    try:
        if isinstance(key, list):
            # Handle nested key access
            current = data
            for k in key:
                if isinstance(current, dict):
                    current = current[k]
                elif isinstance(current, list):
                    current = current[int(k)]
                else:
                    if raise_on_error:
                        raise KeyError(f"Cannot access key {k} on {type(current)}")
                    return default
            return current
        else:
            # Single key access
            if isinstance(data, dict):
                return data.get(key, default)
            elif isinstance(data, list):
                try:
                    return data[int(key)]
                except (IndexError, ValueError):
                    if raise_on_error:
                        raise
                    return default
            else:
                if raise_on_error:
                    raise TypeError(f"Cannot access key {key} on {type(data)}")
                return default
                
    except Exception as e:
        if raise_on_error:
            raise
        logger.warning(f"Safe get failed for key {key}: {e}")
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Integer value or default
    """
    try:
        if isinstance(value, bool):
            return int(value)
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """
    Safely convert value to boolean.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Boolean value or default
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    if isinstance(value, (int, float)):
        return value != 0
    
    return default


def safe_json_loads(
    json_str: str,
    default: Any = None,
    raise_on_error: bool = False
) -> Any:
    """
    Safely parse JSON string.
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        raise_on_error: Whether to raise exception on error
    
    Returns:
        Parsed JSON data or default
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        if raise_on_error:
            raise
        logger.warning(f"JSON parsing failed: {e}")
        return default


def safe_json_dumps(
    data: Any,
    default: str = "{}",
    raise_on_error: bool = False,
    **kwargs
) -> str:
    """
    Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        default: Default value if serialization fails
        raise_on_error: Whether to raise exception on error
        **kwargs: Additional arguments for json.dumps
    
    Returns:
        JSON string or default
    """
    try:
        return json.dumps(data, default=str, **kwargs)
    except (TypeError, ValueError) as e:
        if raise_on_error:
            raise
        logger.warning(f"JSON serialization failed: {e}")
        return default


# List and data manipulation functions
def chunk_list(data: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split list into chunks of specified size.
    
    Args:
        data: List to split
        chunk_size: Size of each chunk
    
    Returns:
        List of chunks
    """
    if chunk_size <= 0:
        raise HelperError("Chunk size must be positive")
    
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def flatten_list(nested_list: List[Union[T, List[T]]]) -> List[T]:
    """
    Flatten nested list structure.
    
    Args:
        nested_list: Nested list to flatten
    
    Returns:
        Flattened list
    """
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def deduplicate_list(
    data: List[T],
    key: Callable[[T], Any] = None,
    preserve_order: bool = True
) -> List[T]:
    """
    Remove duplicates from list.
    
    Args:
        data: List to deduplicate
        key: Function to extract comparison key
        preserve_order: Whether to preserve original order
    
    Returns:
        Deduplicated list
    """
    if not data:
        return []
    
    if key is None:
        if preserve_order:
            seen = set()
            result = []
            for item in data:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        else:
            return list(set(data))
    else:
        seen_keys = set()
        result = []
        for item in data:
            item_key = key(item)
            if item_key not in seen_keys:
                seen_keys.add(item_key)
                result.append(item)
        return result


def group_by(data: List[T], key: Callable[[T], K]) -> Dict[K, List[T]]:
    """
    Group list items by key function.
    
    Args:
        data: List to group
        key: Function to extract grouping key
    
    Returns:
        Dictionary with grouped items
    """
    groups = {}
    for item in data:
        group_key = key(item)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    return groups


def sort_by_multiple(
    data: List[T],
    keys: List[Union[str, Callable[[T], Any]]],
    reverse: Union[bool, List[bool]] = False
) -> List[T]:
    """
    Sort list by multiple keys.
    
    Args:
        data: List to sort
        keys: List of key functions or attribute names
        reverse: Reverse sort order (bool or list of bools)
    
    Returns:
        Sorted list
    """
    if not keys:
        return data[:]
    
    # Normalize reverse parameter
    if isinstance(reverse, bool):
        reverse_list = [reverse] * len(keys)
    else:
        reverse_list = list(reverse)
        while len(reverse_list) < len(keys):
            reverse_list.append(False)
    
    # Sort by keys in reverse order (last key first)
    sorted_data = data[:]
    for i in reversed(range(len(keys))):
        key_func = keys[i]
        
        # Convert string to attribute getter
        if isinstance(key_func, str):
            attr_name = key_func
            key_func = lambda x, attr=attr_name: getattr(x, attr, None)
        
        sorted_data.sort(key=key_func, reverse=reverse_list[i])
    
    return sorted_data


def filter_dict(
    data: Dict[K, V],
    condition: Callable[[K, V], bool],
    keys_only: bool = False,
    values_only: bool = False
) -> Union[Dict[K, V], List[K], List[V]]:
    """
    Filter dictionary by condition.
    
    Args:
        data: Dictionary to filter
        condition: Function that takes (key, value) and returns bool
        keys_only: Return only filtered keys
        values_only: Return only filtered values
    
    Returns:
        Filtered dictionary, keys, or values
    """
    filtered_items = {k: v for k, v in data.items() if condition(k, v)}
    
    if keys_only:
        return list(filtered_items.keys())
    elif values_only:
        return list(filtered_items.values())
    else:
        return filtered_items


def merge_dicts(*dicts: Dict[K, V], deep: bool = False) -> Dict[K, V]:
    """
    Merge multiple dictionaries.
    
    Args:
        *dicts: Dictionaries to merge
        deep: Whether to perform deep merge for nested dicts
    
    Returns:
        Merged dictionary
    """
    if not dicts:
        return {}
    
    result = {}
    
    for d in dicts:
        if not isinstance(d, dict):
            continue
            
        for key, value in d.items():
            if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value, deep=True)
            else:
                result[key] = value
    
    return result


def invert_dict(data: Dict[K, V]) -> Dict[V, K]:
    """
    Invert dictionary (swap keys and values).
    
    Args:
        data: Dictionary to invert
    
    Returns:
        Inverted dictionary
    """
    return {v: k for k, v in data.items()}


# String manipulation functions
def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase to snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()


def snake_to_camel(snake_str: str, first_upper: bool = False) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    if first_upper:
        return ''.join(word.capitalize() for word in components)
    else:
        return components[0] + ''.join(word.capitalize() for word in components[1:])


def title_case(text: str) -> str:
    """Convert text to title case with proper handling of articles."""
    articles = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 
                'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet'}
    
    words = text.lower().split()
    if not words:
        return text
    
    # Always capitalize first word
    words[0] = words[0].capitalize()
    
    # Capitalize other words unless they're articles
    for i in range(1, len(words)):
        if words[i] not in articles:
            words[i] = words[i].capitalize()
    
    return ' '.join(words)


def clean_whitespace(text: str) -> str:
    """Clean excessive whitespace from text."""
    if not text:
        return text
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    return text.strip()


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text."""
    number_pattern = r'-?\d+\.?\d*'
    matches = re.findall(number_pattern, text)
    return [float(match) for match in matches if match]


def mask_sensitive_data(
    text: str,
    patterns: Dict[str, str] = None,
    mask_char: str = '*'
) -> str:
    """
    Mask sensitive data in text.
    
    Args:
        text: Text to mask
        patterns: Dict of pattern_name -> regex_pattern
        mask_char: Character to use for masking
    
    Returns:
        Text with sensitive data masked
    """
    if not text:
        return text
    
    default_patterns = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
    }
    
    patterns = patterns or default_patterns
    masked_text = text
    
    for pattern_name, pattern in patterns.items():
        def mask_match(match):
            matched_text = match.group(0)
            if pattern_name == 'email':
                # Keep first char of username and domain
                parts = matched_text.split('@')
                if len(parts) == 2:
                    username = parts[0]
                    domain = parts[1]
                    masked_username = username[0] + mask_char * (len(username) - 1)
                    domain_parts = domain.split('.')
                    if len(domain_parts) >= 2:
                        masked_domain = domain_parts[0][0] + mask_char * (len(domain_parts[0]) - 1)
                        masked_domain += '.' + '.'.join(domain_parts[1:])
                    else:
                        masked_domain = domain
                    return f"{masked_username}@{masked_domain}"
            
            # Default masking: keep first and last char
            if len(matched_text) <= 2:
                return mask_char * len(matched_text)
            else:
                return matched_text[0] + mask_char * (len(matched_text) - 2) + matched_text[-1]
        
        masked_text = re.sub(pattern, mask_match, masked_text)
    
    return masked_text


# Retry and timing utilities
def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Backoff multiplier
        exceptions: Exceptions to catch and retry
        on_retry: Callback function called on each retry
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        break
                    
                    delay = backoff_factor * (2 ** attempt)
                    
                    if on_retry:
                        on_retry(attempt + 1, delay, e)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        break
                    
                    delay = backoff_factor * (2 ** attempt)
                    
                    if on_retry:
                        on_retry(attempt + 1, delay, e)
                    
                    time.sleep(delay)
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def timeout_after(seconds: float):
    """
    Decorator to add timeout to async functions.
    
    Args:
        seconds: Timeout in seconds
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        return wrapper
    return decorator


def rate_limit(calls_per_second: float = 1.0):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls_per_second: Maximum calls per second
    
    Returns:
        Decorated function
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            sleep_time = min_interval - elapsed
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            
            last_called[0] = time.time()
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            sleep_time = min_interval - elapsed
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# File and path utilities
def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def safe_filename(filename: str, replacement: str = "_") -> str:
    """
    Make filename safe for filesystem.
    
    Args:
        filename: Original filename
        replacement: Character to replace unsafe characters
    
    Returns:
        Safe filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = r'[<>:"/\\|?*]'
    safe_name = re.sub(unsafe_chars, replacement, filename)
    
    # Remove leading/trailing dots and spaces
    safe_name = safe_name.strip('. ')
    
    # Limit length
    if len(safe_name) > 255:
        name, ext = safe_name.rsplit('.', 1) if '.' in safe_name else (safe_name, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        safe_name = name[:max_name_length] + ('.' + ext if ext else '')
    
    return safe_name or "unnamed"


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix.lower()


def get_file_size_human(file_path: Union[str, Path]) -> str:
    """Get human-readable file size."""
    try:
        size = Path(file_path).stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except (OSError, AttributeError):
        return "Unknown"


# Math and calculation utilities
def clamp(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))


def normalize(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> float:
    """Normalize value to 0-1 range."""
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def lerp(start: float, end: float, factor: float) -> float:
    """Linear interpolation between start and end."""
    return start + factor * (end - start)


def round_to_nearest(value: float, nearest: float) -> float:
    """Round value to nearest multiple."""
    return round(value / nearest) * nearest


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between old and new values."""
    if old_value == 0:
        return float('inf') if new_value > 0 else float('-inf') if new_value < 0 else 0
    return ((new_value - old_value) / old_value) * 100


# Date and time utilities
def days_between(date1: datetime, date2: datetime) -> int:
    """Calculate days between two dates."""
    return abs((date2.date() - date1.date()).days)


def add_business_days(start_date: datetime, business_days: int) -> datetime:
    """Add business days to date (excluding weekends)."""
    current_date = start_date
    days_added = 0
    
    while days_added < business_days:
        current_date += timedelta(days=1)
        # Monday is 0, Sunday is 6
        if current_date.weekday() < 5:  # Monday to Friday
            days_added += 1
    
    return current_date


def is_business_day(date: datetime) -> bool:
    """Check if date is a business day (Monday-Friday)."""
    return date.weekday() < 5


def get_age_from_date(birth_date: datetime) -> Dict[str, int]:
    """Calculate age from birth date."""
    today = datetime.now()
    age = today - birth_date
    
    years = age.days // 365
    months = (age.days % 365) // 30
    days = (age.days % 365) % 30
    
    return {
        'years': years,
        'months': months,
        'days': days,
        'total_days': age.days
    }


# Validation and checking utilities
def is_valid_email_domain(domain: str) -> bool:
    """Check if domain could be valid for email."""
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(domain_pattern, domain)) and len(domain) <= 253


def is_valid_url(url: str) -> bool:
    """Check if URL format is valid."""
    url_pattern = r'^https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    return bool(re.match(url_pattern, url))


def is_valid_ipv4(ip: str) -> bool:
    """Check if string is valid IPv4 address."""
    try:
        parts = ip.split('.')
        return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, AttributeError):
        return False


def is_empty_or_whitespace(value: Any) -> bool:
    """Check if value is None, empty, or only whitespace."""
    if value is None:
        return True
    if isinstance(value, str):
        return len(value.strip()) == 0
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


# Performance and monitoring utilities
class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, description: str = "Operation"):
        self.description = description
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.debug(f"{self.description} took {duration:.3f} seconds")
        
    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


def measure_memory():
    """Measure current memory usage (if psutil available)."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms,  # Virtual Memory Size
            'percent': process.memory_percent()
        }
    except ImportError:
        return None


# Environment and configuration utilities
def get_env_bool(env_var: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    import os
    value = os.getenv(env_var, '').lower()
    return value in ('true', '1', 'yes', 'on', 'enabled')


def get_env_int(env_var: str, default: int = 0) -> int:
    """Get integer value from environment variable."""
    import os
    try:
        return int(os.getenv(env_var, str(default)))
    except ValueError:
        return default


def get_env_list(env_var: str, separator: str = ',', default: List[str] = None) -> List[str]:
    """Get list value from environment variable."""
    import os
    value = os.getenv(env_var, '')
    if not value:
        return default or []
    return [item.strip() for item in value.split(separator) if item.strip()]


# Caching utilities
class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if key in self.cache:
            value, expires_at = self.cache[key]
            if time.time() < expires_at:
                return value
            else:
                del self.cache[key]
        return default
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        self.cache[key] = (value, expires_at)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expires_at) in self.cache.items()
            if current_time >= expires_at
        ]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)


# Data transformation utilities
def pivot_data(
    data: List[Dict[str, Any]],
    index_col: str,
    value_col: str,
    agg_func: str = 'sum'
) -> Dict[str, Any]:
    """
    Pivot data similar to pandas pivot table.
    
    Args:
        data: List of dictionaries
        index_col: Column to use as index
        value_col: Column to aggregate
        agg_func: Aggregation function (sum, count, avg, min, max)
    
    Returns:
        Pivoted data dictionary
    """
    pivoted = {}
    
    for row in data:
        index_val = row.get(index_col)
        value = row.get(value_col, 0)
        
        if index_val not in pivoted:
            pivoted[index_val] = []
        
        try:
            pivoted[index_val].append(float(value))
        except (ValueError, TypeError):
            pivoted[index_val].append(0)
    
    # Apply aggregation
    result = {}
    for key, values in pivoted.items():
        if agg_func == 'sum':
            result[key] = sum(values)
        elif agg_func == 'count':
            result[key] = len(values)
        elif agg_func == 'avg':
            result[key] = sum(values) / len(values) if values else 0
        elif agg_func == 'min':
            result[key] = min(values) if values else 0
        elif agg_func == 'max':
            result[key] = max(values) if values else 0
        else:
            result[key] = values
    
    return result


def transpose_dict_list(data: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Transpose list of dictionaries to dictionary of lists.
    
    Args:
        data: List of dictionaries
    
    Returns:
        Dictionary with lists of values
    """
    if not data:
        return {}
    
    result = {}
    for row in data:
        for key, value in row.items():
            if key not in result:
                result[key] = []
            result[key].append(value)
    
    return result


def dict_list_to_csv_string(data: List[Dict[str, Any]]) -> str:
    """
    Convert list of dictionaries to CSV string.
    
    Args:
        data: List of dictionaries
    
    Returns:
        CSV formatted string
    """
    if not data:
        return ""
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()


# Async utilities
async def gather_with_concurrency(
    coroutines: List[Callable],
    max_concurrency: int = 10
) -> List[Any]:
    """
    Run coroutines with limited concurrency.
    
    Args:
        coroutines: List of coroutines to run
        max_concurrency: Maximum concurrent operations
    
    Returns:
        List of results
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def run_with_semaphore(coro):
        async with semaphore:
            return await coro
    
    tasks = [run_with_semaphore(coro) for coro in coroutines]
    return await asyncio.gather(*tasks)


async def run_with_timeout_and_retry(
    coro: Callable,
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_factor: float = 1.0
) -> Any:
    """
    Run coroutine with timeout and retry logic.
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        max_retries: Maximum number of retries
        backoff_factor: Backoff multiplier for retries
    
    Returns:
        Result of coroutine
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                break
    
    raise last_exception


# Network utilities
def get_client_ip(request_headers: Dict[str, str]) -> str:
    """
    Extract client IP from request headers.
    
    Args:
        request_headers: HTTP request headers
    
    Returns:
        Client IP address
    """
    # Check common proxy headers
    ip_headers = [
        'X-Forwarded-For',
        'X-Real-IP',
        'X-Client-IP',
        'CF-Connecting-IP',  # Cloudflare
        'X-Forwarded'
    ]
    
    for header in ip_headers:
        ip = request_headers.get(header)
        if ip:
            # X-Forwarded-For can contain multiple IPs
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            
            # Validate IP format
            if is_valid_ipv4(ip):
                return ip
    
    return "unknown"


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """
    Parse user agent string to extract browser and OS info.
    
    Args:
        user_agent: User agent string
    
    Returns:
        Dictionary with parsed information
    """
    if not user_agent:
        return {"browser": "unknown", "os": "unknown", "device": "unknown"}
    
    ua_lower = user_agent.lower()
    
    # Browser detection
    browser = "unknown"
    if "chrome" in ua_lower:
        browser = "chrome"
    elif "firefox" in ua_lower:
        browser = "firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "safari"
    elif "edge" in ua_lower:
        browser = "edge"
    elif "opera" in ua_lower:
        browser = "opera"
    
    # OS detection
    os = "unknown"
    if "windows" in ua_lower:
        os = "windows"
    elif "mac" in ua_lower:
        os = "macos"
    elif "linux" in ua_lower:
        os = "linux"
    elif "android" in ua_lower:
        os = "android"
    elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
        os = "ios"
    
    # Device detection
    device = "desktop"
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device = "tablet"
    
    return {
        "browser": browser,
        "os": os,
        "device": device,
        "raw": user_agent
    }


# Color utilities
def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_color_palette(base_color: str, count: int = 5) -> List[str]:
    """
    Generate color palette based on base color.
    
    Args:
        base_color: Base hex color
        count: Number of colors to generate
    
    Returns:
        List of hex colors
    """
    r, g, b = hex_to_rgb(base_color)
    palette = []
    
    for i in range(count):
        # Adjust brightness
        factor = 0.3 + (0.7 * i / (count - 1)) if count > 1 else 1.0
        
        new_r = int(r * factor)
        new_g = int(g * factor)
        new_b = int(b * factor)
        
        # Clamp values
        new_r = clamp(new_r, 0, 255)
        new_g = clamp(new_g, 0, 255)
        new_b = clamp(new_b, 0, 255)
        
        palette.append(rgb_to_hex(new_r, new_g, new_b))
    
    return palette


# Export all helper functions
__all__ = [
    'HelperError',
    'generate_id',
    'generate_uuid',
    'generate_secure_token',
    'generate_random_string',
    'generate_slug',
    'generate_hash',
    'safe_get',
    'safe_int',
    'safe_float',
    'safe_bool',
    'safe_json_loads',
    'safe_json_dumps',
    'chunk_list',
    'flatten_list',
    'deduplicate_list',
    'group_by',
    'sort_by_multiple',
    'filter_dict',
    'merge_dicts',
    'invert_dict',
    'camel_to_snake',
    'snake_to_camel',
    'title_case',
    'clean_whitespace',
    'extract_numbers',
    'mask_sensitive_data',
    'retry_with_backoff',
    'timeout_after',
    'rate_limit',
    'ensure_directory',
    'safe_filename',
    'get_file_extension',
    'get_file_size_human',
    'clamp',
    'normalize',
    'lerp',
    'round_to_nearest',
    'calculate_percentage_change',
    'days_between',
    'add_business_days',
    'is_business_day',
    'get_age_from_date',
    'is_valid_email_domain',
    'is_valid_url',
    'is_valid_ipv4',
    'is_empty_or_whitespace',
    'Timer',
    'measure_memory',
    'get_env_bool',
    'get_env_int',
    'get_env_list',
    'SimpleCache',
    'pivot_data',
    'transpose_dict_list',
    'dict_list_to_csv_string',
    'gather_with_concurrency',
    'run_with_timeout_and_retry',
    'get_client_ip',
    'parse_user_agent',
    'hex_to_rgb',
    'rgb_to_hex',
    'generate_color_palette'
]