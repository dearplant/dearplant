# 📄 File: app/shared/utils/formatters.py

# 🧭 Purpose (Layman Explanation):
# This file provides smart formatting tools that make data look nice and consistent,
# like turning numbers into currency, dates into readable text, and file sizes into "5 MB" format.

# 🧪 Purpose (Technical Summary):
# Data formatting utilities for consistent presentation of dates, numbers, currencies,
# file sizes, durations, and plant-specific data across the application.

# 🔗 Dependencies:
# - datetime: Date and time formatting
# - decimal: Precise decimal formatting
# - babel: Internationalization and localization (optional)
# - re: Regular expression utilities

# 🔄 Connected Modules / Calls From:
# Used by: API responses, UI templates, Reports, Email templates, Notifications,
# Any module requiring consistent data presentation

import re
import math
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union
from enum import Enum

try:
    from babel.dates import format_datetime as babel_format_datetime
    from babel.numbers import format_currency as babel_format_currency
    from babel import Locale
    HAS_BABEL = True
except ImportError:
    HAS_BABEL = False

from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class DateFormat(Enum):
    """Standard date format types."""
    SHORT = "short"          # 01/15/24
    MEDIUM = "medium"        # Jan 15, 2024
    LONG = "long"           # January 15, 2024
    FULL = "full"           # Monday, January 15, 2024
    ISO = "iso"             # 2024-01-15
    RELATIVE = "relative"    # 2 days ago


class NumberFormat(Enum):
    """Standard number format types."""
    DECIMAL = "decimal"      # 1,234.56
    PERCENT = "percent"      # 12.34%
    CURRENCY = "currency"    # $1,234.56
    SCIENTIFIC = "scientific" # 1.23E+3
    COMPACT = "compact"      # 1.2K


class FileSize(Enum):
    """File size units."""
    BYTES = "bytes"
    KB = "kb"
    MB = "mb" 
    GB = "gb"
    TB = "tb"


# Global formatting configuration
DEFAULT_LOCALE = "en_US"
DEFAULT_CURRENCY = "USD"
DEFAULT_TIMEZONE = "UTC"

# Formatting cache for performance
_format_cache = {}


class FormattingError(Exception):
    """Exception for formatting errors."""
    pass


def set_default_locale(locale: str):
    """Set the default locale for formatting."""
    global DEFAULT_LOCALE
    DEFAULT_LOCALE = locale
    _format_cache.clear()  # Clear cache when locale changes


def set_default_currency(currency: str):
    """Set the default currency for formatting."""
    global DEFAULT_CURRENCY
    DEFAULT_CURRENCY = currency


# Date and time formatting functions
def format_datetime(
    dt: Union[datetime, date, str],
    format_type: Union[DateFormat, str] = DateFormat.MEDIUM,
    locale: str = None,
    timezone: str = None,
    include_time: bool = None
) -> str:
    """
    Format datetime with various options.
    
    Args:
        dt: Datetime object, date object, or ISO string
        format_type: Format type (short, medium, long, full, iso, relative)
        locale: Locale for formatting (e.g., 'en_US', 'es_ES')
        timezone: Timezone for conversion
        include_time: Whether to include time component
    
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return ""
    
    # Convert string to datetime if needed
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d')
            except ValueError:
                raise FormattingError(f"Unable to parse datetime string: {dt}")
    
    # Convert date to datetime if needed
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    locale = locale or DEFAULT_LOCALE
    format_type = DateFormat(format_type) if isinstance(format_type, str) else format_type
    
    # Handle relative formatting
    if format_type == DateFormat.RELATIVE:
        return format_relative_time(dt)
    
    # Handle ISO formatting
    if format_type == DateFormat.ISO:
        if isinstance(dt, datetime):
            return dt.isoformat()
        else:
            return dt.strftime('%Y-%m-%d')
    
    # Use Babel for internationalized formatting if available
    if HAS_BABEL:
        try:
            babel_locale = Locale.parse(locale)
            
            if format_type == DateFormat.SHORT:
                pattern = 'short'
            elif format_type == DateFormat.MEDIUM:
                pattern = 'medium'
            elif format_type == DateFormat.LONG:
                pattern = 'long'
            elif format_type == DateFormat.FULL:
                pattern = 'full'
            else:
                pattern = 'medium'
            
            if include_time is None:
                include_time = isinstance(dt, datetime) and dt.time() != datetime.min.time()
            
            if include_time:
                return babel_format_datetime(dt, format=pattern, locale=babel_locale)
            else:
                from babel.dates import format_date
                return format_date(dt.date() if isinstance(dt, datetime) else dt, 
                                 format=pattern, locale=babel_locale)
                
        except Exception as e:
            logger.warning(f"Babel formatting failed, using fallback: {e}")
    
    # Fallback formatting
    format_patterns = {
        DateFormat.SHORT: '%m/%d/%y',
        DateFormat.MEDIUM: '%b %d, %Y',
        DateFormat.LONG: '%B %d, %Y',
        DateFormat.FULL: '%A, %B %d, %Y'
    }
    
    pattern = format_patterns.get(format_type, '%b %d, %Y')
    
    if include_time or (include_time is None and isinstance(dt, datetime) and dt.time() != datetime.min.time()):
        pattern += ' %I:%M %p'
    
    return dt.strftime(pattern)


def format_relative_time(dt: datetime, reference: datetime = None) -> str:
    """
    Format datetime as relative time (e.g., '2 hours ago', 'in 3 days').
    
    Args:
        dt: Datetime to format
        reference: Reference datetime (defaults to now)
    
    Returns:
        Relative time string
    """
    if reference is None:
        reference = datetime.now(dt.tzinfo if dt.tzinfo else None)
    
    delta = reference - dt
    total_seconds = abs(delta.total_seconds())
    
    # Determine if past or future
    is_past = delta.total_seconds() > 0
    prefix = "" if is_past else "in "
    suffix = " ago" if is_past else ""
    
    # Calculate time units
    units = [
        (31536000, "year"),    # 365 days
        (2592000, "month"),    # 30 days  
        (604800, "week"),      # 7 days
        (86400, "day"),        # 24 hours
        (3600, "hour"),        # 60 minutes
        (60, "minute"),        # 60 seconds
        (1, "second")
    ]
    
    for seconds_in_unit, unit_name in units:
        if total_seconds >= seconds_in_unit:
            count = int(total_seconds // seconds_in_unit)
            unit_str = unit_name if count == 1 else f"{unit_name}s"
            return f"{prefix}{count} {unit_str}{suffix}"
    
    return "just now"


def format_duration(
    seconds: Union[int, float],
    precision: int = 2,
    short_format: bool = False
) -> str:
    """
    Format duration in seconds to human-readable format.
    
    Args:
        seconds: Duration in seconds
        precision: Number of units to show
        short_format: Use short format (1h 30m vs 1 hour 30 minutes)
    
    Returns:
        Formatted duration string
    """
    if seconds < 0:
        return f"-{format_duration(abs(seconds), precision, short_format)}"
    
    units = [
        (86400, "day", "d"),
        (3600, "hour", "h"),
        (60, "minute", "m"),
        (1, "second", "s")
    ]
    
    result_parts = []
    remaining = seconds
    
    for unit_seconds, long_name, short_name in units:
        if remaining >= unit_seconds:
            count = int(remaining // unit_seconds)
            remaining = remaining % unit_seconds
            
            if short_format:
                result_parts.append(f"{count}{short_name}")
            else:
                unit_str = long_name if count == 1 else f"{long_name}s"
                result_parts.append(f"{count} {unit_str}")
            
            if len(result_parts) >= precision:
                break
    
    if not result_parts:
        return "0 seconds" if not short_format else "0s"
    
    return " ".join(result_parts)


# Number formatting functions
def format_number(
    value: Union[int, float, Decimal, str],
    format_type: Union[NumberFormat, str] = NumberFormat.DECIMAL,
    precision: int = None,
    locale: str = None,
    currency: str = None
) -> str:
    """
    Format numbers with various options.
    
    Args:
        value: Number to format
        format_type: Format type (decimal, percent, currency, etc.)
        precision: Number of decimal places
        locale: Locale for formatting
        currency: Currency code for currency formatting
    
    Returns:
        Formatted number string
    """
    if value is None:
        return ""
    
    # Convert to Decimal for precise arithmetic
    try:
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
    except Exception:
        raise FormattingError(f"Unable to convert value to number: {value}")
    
    locale = locale or DEFAULT_LOCALE
    currency = currency or DEFAULT_CURRENCY
    format_type = NumberFormat(format_type) if isinstance(format_type, str) else format_type
    
    # Handle different format types
    if format_type == NumberFormat.PERCENT:
        percent_value = decimal_value * 100
        if precision is None:
            precision = 1
        formatted = f"{percent_value:.{precision}f}%"
        
    elif format_type == NumberFormat.CURRENCY:
        if HAS_BABEL:
            try:
                babel_locale = Locale.parse(locale)
                return babel_format_currency(
                    float(decimal_value), 
                    currency, 
                    locale=babel_locale
                )
            except Exception as e:
                logger.warning(f"Babel currency formatting failed: {e}")
        
        # Fallback currency formatting
        if precision is None:
            precision = 2
        symbol = get_currency_symbol(currency)
        formatted = f"{symbol}{decimal_value:,.{precision}f}"
        
    elif format_type == NumberFormat.SCIENTIFIC:
        if precision is None:
            precision = 2
        formatted = f"{float(decimal_value):.{precision}e}"
        
    elif format_type == NumberFormat.COMPACT:
        formatted = format_compact_number(decimal_value, precision)
        
    else:  # DECIMAL
        if precision is None:
            # Auto-determine precision
            if decimal_value == decimal_value.to_integral_value():
                precision = 0
            else:
                precision = 2
        
        formatted = f"{decimal_value:,.{precision}f}"
    
    return formatted


def format_compact_number(value: Union[int, float, Decimal], precision: int = 1) -> str:
    """
    Format large numbers in compact format (1.2K, 3.4M, etc.).
    
    Args:
        value: Number to format
        precision: Decimal precision
    
    Returns:
        Compact formatted number
    """
    if isinstance(value, str):
        value = float(value)
    
    abs_value = abs(float(value))
    
    if abs_value < 1000:
        return str(int(value)) if value == int(value) else f"{value:.{precision}f}"
    
    units = [
        (1e12, 'T'),  # Trillion
        (1e9, 'B'),   # Billion
        (1e6, 'M'),   # Million
        (1e3, 'K')    # Thousand
    ]
    
    for threshold, suffix in units:
        if abs_value >= threshold:
            compact_value = value / threshold
            if compact_value == int(compact_value):
                return f"{int(compact_value)}{suffix}"
            else:
                return f"{compact_value:.{precision}f}{suffix}"
    
    return str(value)


def format_currency(
    amount: Union[int, float, Decimal, str],
    currency: str = None,
    locale: str = None,
    precision: int = 2
) -> str:
    """
    Format currency amount.
    
    Args:
        amount: Amount to format
        currency: Currency code
        locale: Locale for formatting
        precision: Decimal precision
    
    Returns:
        Formatted currency string
    """
    return format_number(amount, NumberFormat.CURRENCY, precision, locale, currency)


def format_percentage(
    value: Union[int, float, Decimal, str],
    precision: int = 1,
    multiply_by_100: bool = True
) -> str:
    """
    Format percentage value.
    
    Args:
        value: Value to format (0.15 becomes 15% if multiply_by_100=True)
        precision: Decimal precision
        multiply_by_100: Whether to multiply by 100
    
    Returns:
        Formatted percentage string
    """
    if isinstance(value, str):
        value = float(value)
    
    if multiply_by_100:
        percentage = value * 100
    else:
        percentage = value
    
    return f"{percentage:.{precision}f}%"


# File size formatting
def format_file_size(
    size_bytes: int,
    binary: bool = True,
    precision: int = 1
) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        binary: Use binary (1024) or decimal (1000) units
        precision: Decimal precision
    
    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 B"
    
    if size_bytes < 0:
        return f"-{format_file_size(abs(size_bytes), binary, precision)}"
    
    base = 1024 if binary else 1000
    
    if binary:
        units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
    else:
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    # Calculate the appropriate unit
    unit_index = min(int(math.log(size_bytes) / math.log(base)), len(units) - 1)
    
    if unit_index == 0:
        return f"{size_bytes} B"
    
    size_in_unit = size_bytes / (base ** unit_index)
    
    if size_in_unit == int(size_in_unit):
        return f"{int(size_in_unit)} {units[unit_index]}"
    else:
        return f"{size_in_unit:.{precision}f} {units[unit_index]}"


# Plant-specific formatting functions
def format_plant_measurement(
    value: Union[int, float, str],
    unit: str = "cm",
    precision: int = 1
) -> str:
    """
    Format plant measurements (height, width, etc.).
    
    Args:
        value: Measurement value
        unit: Unit of measurement (cm, inches, ft)
        precision: Decimal precision
    
    Returns:
        Formatted measurement string
    """
    if value is None or value == "":
        return "Not measured"
    
    try:
        numeric_value = float(value)
        
        if numeric_value == 0:
            return f"0 {unit}"
        
        if numeric_value == int(numeric_value):
            return f"{int(numeric_value)} {unit}"
        else:
            return f"{numeric_value:.{precision}f} {unit}"
            
    except (ValueError, TypeError):
        return str(value)


def format_care_frequency(frequency: str, next_date: date = None) -> str:
    """
    Format care frequency with next due date.
    
    Args:
        frequency: Care frequency (daily, weekly, etc.)
        next_date: Next care due date
    
    Returns:
        Formatted care frequency string
    """
    frequency_display = {
        'daily': 'Daily',
        'every_other_day': 'Every other day',
        'weekly': 'Weekly',
        'bi_weekly': 'Bi-weekly',
        'monthly': 'Monthly',
        'seasonal': 'Seasonally',
        'as_needed': 'As needed'
    }
    
    formatted_freq = frequency_display.get(frequency, frequency.replace('_', ' ').title())
    
    if next_date and frequency != 'as_needed':
        next_date_str = format_datetime(next_date, DateFormat.MEDIUM)
        return f"{formatted_freq} (Next: {next_date_str})"
    
    return formatted_freq


def format_plant_health_score(score: Union[int, float], max_score: int = 10) -> str:
    """
    Format plant health score with status.
    
    Args:
        score: Health score
        max_score: Maximum possible score
    
    Returns:
        Formatted health score with status
    """
    if score is None:
        return "Not assessed"
    
    try:
        numeric_score = float(score)
        percentage = (numeric_score / max_score) * 100
        
        if percentage >= 80:
            status = "Excellent"
            emoji = "🌟"
        elif percentage >= 60:
            status = "Good"
            emoji = "😊"
        elif percentage >= 40:
            status = "Fair"
            emoji = "😐"
        elif percentage >= 20:
            status = "Poor"
            emoji = "😟"
        else:
            status = "Critical"
            emoji = "🚨"
        
        return f"{numeric_score:.1f}/{max_score} {emoji} {status}"
        
    except (ValueError, TypeError):
        return str(score)


def format_growth_progress(
    current_height: float,
    previous_height: float = None,
    target_height: float = None,
    unit: str = "cm"
) -> Dict[str, str]:
    """
    Format growth progress information.
    
    Args:
        current_height: Current plant height
        previous_height: Previous measurement
        target_height: Target/expected height
        unit: Unit of measurement
    
    Returns:
        Dict with formatted growth information
    """
    result = {
        'current': format_plant_measurement(current_height, unit),
        'growth': None,
        'progress': None
    }
    
    if previous_height is not None:
        growth = current_height - previous_height
        if growth > 0:
            result['growth'] = f"+{format_plant_measurement(growth, unit)} growth"
        elif growth < 0:
            result['growth'] = f"{format_plant_measurement(growth, unit)} decline"
        else:
            result['growth'] = "No change"
    
    if target_height is not None and current_height > 0:
        progress_percent = (current_height / target_height) * 100
        result['progress'] = f"{progress_percent:.1f}% to target"
    
    return result


def format_watering_schedule(
    last_watered: datetime = None,
    next_due: datetime = None,
    frequency_days: int = None
) -> Dict[str, str]:
    """
    Format watering schedule information.
    
    Args:
        last_watered: Last watering date
        next_due: Next watering due date
        frequency_days: Watering frequency in days
    
    Returns:
        Dict with formatted watering information
    """
    result = {}
    
    if last_watered:
        result['last_watered'] = format_relative_time(last_watered)
    
    if next_due:
        now = datetime.now(next_due.tzinfo if next_due.tzinfo else None)
        if next_due <= now:
            result['next_due'] = "Due now"
            result['status'] = "overdue"
        else:
            result['next_due'] = f"Due {format_relative_time(next_due, now)}"
            result['status'] = "scheduled"
    
    if frequency_days:
        if frequency_days == 1:
            result['frequency'] = "Daily"
        elif frequency_days == 7:
            result['frequency'] = "Weekly"
        elif frequency_days == 14:
            result['frequency'] = "Bi-weekly"
        elif frequency_days == 30:
            result['frequency'] = "Monthly"
        else:
            result['frequency'] = f"Every {frequency_days} days"
    
    return result


# Address and location formatting
def format_address(
    address_components: Dict[str, str],
    format_style: str = "full"
) -> str:
    """
    Format address from components.
    
    Args:
        address_components: Dict with address parts
        format_style: Format style (full, short, city_state)
    
    Returns:
        Formatted address string
    """
    if not address_components:
        return ""
    
    if format_style == "city_state":
        city = address_components.get('city', '')
        state = address_components.get('state', '')
        return f"{city}, {state}" if city and state else city or state
    
    elif format_style == "short":
        parts = [
            address_components.get('city', ''),
            address_components.get('state', ''),
            address_components.get('country', '')
        ]
        return ", ".join(filter(None, parts))
    
    else:  # full
        parts = [
            address_components.get('street_address', ''),
            address_components.get('city', ''),
            address_components.get('state', ''),
            address_components.get('postal_code', ''),
            address_components.get('country', '')
        ]
        return ", ".join(filter(None, parts))


def format_coordinates(
    latitude: float,
    longitude: float,
    precision: int = 6,
    format_style: str = "decimal"
) -> str:
    """
    Format geographic coordinates.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
        precision: Decimal precision
        format_style: Format style (decimal, dms)
    
    Returns:
        Formatted coordinates string
    """
    if format_style == "dms":
        # Convert to degrees, minutes, seconds
        def to_dms(coord: float, is_latitude: bool = True) -> str:
            abs_coord = abs(coord)
            degrees = int(abs_coord)
            minutes = int((abs_coord - degrees) * 60)
            seconds = ((abs_coord - degrees) * 60 - minutes) * 60
            
            if is_latitude:
                direction = 'N' if coord >= 0 else 'S'
            else:
                direction = 'E' if coord >= 0 else 'W'
            
            return f"{degrees}°{minutes}'{seconds:.1f}\"{direction}"
        
        lat_dms = to_dms(latitude, True)
        lon_dms = to_dms(longitude, False)
        return f"{lat_dms}, {lon_dms}"
    
    else:  # decimal
        return f"{latitude:.{precision}f}, {longitude:.{precision}f}"


# JSON and data structure formatting
def format_json(
    data: Any,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False
) -> str:
    """
    Format data as pretty JSON.
    
    Args:
        data: Data to format
        indent: Indentation spaces
        sort_keys: Whether to sort dictionary keys
        ensure_ascii: Whether to escape non-ASCII characters
    
    Returns:
        Formatted JSON string
    """
    import json
    
    try:
        return json.dumps(
            data,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            default=str  # Handle datetime and other non-serializable objects
        )
    except Exception as e:
        raise FormattingError(f"JSON formatting failed: {e}")


def format_table_data(
    data: List[Dict[str, Any]],
    headers: List[str] = None,
    max_width: int = 20
) -> str:
    """
    Format data as ASCII table.
    
    Args:
        data: List of dictionaries to format
        headers: Column headers (uses dict keys if not provided)
        max_width: Maximum column width
    
    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display"
    
    # Get headers from first row if not provided
    if headers is None:
        headers = list(data[0].keys())
    
    # Calculate column widths
    widths = {}
    for header in headers:
        widths[header] = min(max_width, max(
            len(str(header)),
            max(len(str(row.get(header, ''))) for row in data)
        ))
    
    # Format header row
    header_row = " | ".join(
        str(header).ljust(widths[header]) for header in headers
    )
    separator = "-" * len(header_row)
    
    # Format data rows
    data_rows = []
    for row in data:
        formatted_row = " | ".join(
            str(row.get(header, '')).ljust(widths[header])[:widths[header]]
            for header in headers
        )
        data_rows.append(formatted_row)
    
    return "\n".join([header_row, separator] + data_rows)


# Utility functions
def get_currency_symbol(currency_code: str) -> str:
    """Get currency symbol for currency code."""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'INR': '₹',
        'CAD': 'C',
        'AUD': 'A',
        'CNY': '¥',
        'KRW': '₩',
        'BRL': 'R'
    }
    return symbols.get(currency_code.upper(), currency_code)


def truncate_text(
    text: str,
    max_length: int,
    suffix: str = "..."
) -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
    
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    if len(suffix) >= max_length:
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def format_list(
    items: List[Any],
    conjunction: str = "and",
    max_items: int = None,
    formatter: callable = None
) -> str:
    """
    Format list of items into readable string.
    
    Args:
        items: List of items to format
        conjunction: Conjunction word (and, or)
        max_items: Maximum items to show before truncating
        formatter: Function to format individual items
    
    Returns:
        Formatted list string
    """
    if not items:
        return ""
    
    # Apply formatter if provided
    if formatter:
        formatted_items = [formatter(item) for item in items]
    else:
        formatted_items = [str(item) for item in items]
    
    # Truncate if necessary
    if max_items and len(formatted_items) > max_items:
        shown_items = formatted_items[:max_items]
        remaining = len(formatted_items) - max_items
        shown_items.append(f"{remaining} more")
        formatted_items = shown_items
    
    if len(formatted_items) == 1:
        return formatted_items[0]
    elif len(formatted_items) == 2:
        return f"{formatted_items[0]} {conjunction} {formatted_items[1]}"
    else:
        return f"{', '.join(formatted_items[:-1])} {conjunction} {formatted_items[-1]}"


def format_key_value_pairs(
    data: Dict[str, Any],
    separator: str = ": ",
    line_separator: str = "\n",
    key_formatter: callable = None,
    value_formatter: callable = None
) -> str:
    """
    Format dictionary as key-value pairs.
    
    Args:
        data: Dictionary to format
        separator: Separator between key and value
        line_separator: Separator between pairs
        key_formatter: Function to format keys
        value_formatter: Function to format values
    
    Returns:
        Formatted key-value string
    """
    if not data:
        return ""
    
    formatted_pairs = []
    
    for key, value in data.items():
        # Format key
        if key_formatter:
            formatted_key = key_formatter(key)
        else:
            formatted_key = str(key).replace('_', ' ').title()
        
        # Format value
        if value_formatter:
            formatted_value = value_formatter(value)
        else:
            formatted_value = str(value)
        
        formatted_pairs.append(f"{formatted_key}{separator}{formatted_value}")
    
    return line_separator.join(formatted_pairs)


# Template formatting functions
def format_notification_message(
    template: str,
    variables: Dict[str, Any],
    formatters: Dict[str, callable] = None
) -> str:
    """
    Format notification message template with variables.
    
    Args:
        template: Message template with {variable} placeholders
        variables: Variables to substitute
        formatters: Custom formatters for specific variables
    
    Returns:
        Formatted message
    """
    formatted_vars = {}
    formatters = formatters or {}
    
    for key, value in variables.items():
        if key in formatters:
            formatted_vars[key] = formatters[key](value)
        elif isinstance(value, datetime):
            formatted_vars[key] = format_datetime(value, DateFormat.MEDIUM)
        elif isinstance(value, (int, float)):
            formatted_vars[key] = format_number(value)
        else:
            formatted_vars[key] = str(value)
    
    try:
        return template.format(**formatted_vars)
    except KeyError as e:
        raise FormattingError(f"Missing template variable: {e}")
    except Exception as e:
        raise FormattingError(f"Template formatting failed: {e}")


def format_api_response(
    data: Any,
    format_type: str = "json",
    include_metadata: bool = True
) -> Union[str, Dict[str, Any]]:
    """
    Format data for API response.
    
    Args:
        data: Data to format
        format_type: Response format (json, xml, csv)
        include_metadata: Whether to include response metadata
    
    Returns:
        Formatted response data
    """
    if format_type == "json":
        response = {
            "data": data,
            "success": True
        }
        
        if include_metadata:
            response["metadata"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "format": "json",
                "count": len(data) if isinstance(data, (list, dict)) else 1
            }
        
        return response
    
    elif format_type == "csv" and isinstance(data, list):
        import csv
        import io
        
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    else:
        return str(data)


# Export all formatting functions
__all__ = [
    'DateFormat',
    'NumberFormat', 
    'FileSize',
    'FormattingError',
    'set_default_locale',
    'set_default_currency',
    'format_datetime',
    'format_relative_time',
    'format_duration',
    'format_number',
    'format_compact_number',
    'format_currency',
    'format_percentage',
    'format_file_size',
    'format_plant_measurement',
    'format_care_frequency',
    'format_plant_health_score',
    'format_growth_progress',
    'format_watering_schedule',
    'format_address',
    'format_coordinates',
    'format_json',
    'format_table_data',
    'get_currency_symbol',
    'truncate_text',
    'format_list',
    'format_key_value_pairs',
    'format_notification_message',
    'format_api_response'
]