# 📄 File: app/shared/utils/logging.py

# 🧭 Purpose (Layman Explanation):
# This file sets up a smart logging system that records what happens in the app in a structured way,
# making it easy to monitor, debug, and understand how the plant care app is performing.

# 🧪 Purpose (Technical Summary):
# Implements structured logging with JSON formatting, contextual information, performance tracking,
# and integration with monitoring systems for comprehensive application observability.

# 🔗 Dependencies:
# - python-json-logger: JSON log formatting
# - logging: Python standard logging
# - contextvars: Request context tracking
# - datetime: Timestamp handling

# 🔄 Connected Modules / Calls From:
# Used by: All application modules for consistent logging, error tracking, performance monitoring,
# API request logging, database operation logging, external API call logging

import json
import logging
import logging.config
import os
import sys
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

from app.shared.config.settings import get_settings

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')

# Global logging configuration
_logging_configured = False
_loggers_cache = {}


class ContextualFormatter(logging.Formatter):
    """
    Custom formatter that adds contextual information to log records.
    
    Adds request ID, user ID, correlation ID, and other contextual data
    to every log message for better traceability.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        self.service_name = 'plant-care-api'
        
    def format(self, record):
        # Add contextual information
        record.request_id = request_id_var.get('')
        record.user_id = user_id_var.get('')
        record.correlation_id = correlation_id_var.get('')
        record.hostname = self.hostname
        record.service = self.service_name
        record.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Add extra fields from record
        if hasattr(record, 'extra_fields') and record.extra_fields:
            for key, value in record.extra_fields.items():
                setattr(record, key, value)
        
        return super().format(record)


class JSONFormatter(ContextualFormatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs in JSON format with consistent structure for
    log aggregation and analysis tools.
    """
    
    def __init__(self):
        super().__init__()
        
    def format(self, record):
        # Create base log structure
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'service': self.service_name,
            'hostname': self.hostname
        }
        
        # Add contextual information
        if request_id_var.get():
            log_entry['request_id'] = request_id_var.get()
        if user_id_var.get():
            log_entry['user_id'] = user_id_var.get()
        if correlation_id_var.get():
            log_entry['correlation_id'] = correlation_id_var.get()
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_fields') and record.extra_fields:
            log_entry['extra'] = record.extra_fields
        
        # Add performance data if present
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'path'):
            log_entry['path'] = record.path
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class PerformanceLogger:
    """
    Logger for tracking performance metrics and timing information.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str = None,
        extra: Dict = None
    ):
        """Log HTTP request performance."""
        extra_fields = {
            'event_type': 'http_request',
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': duration_ms,
            **(extra or {})
        }
        
        if user_id:
            extra_fields['user_id'] = user_id
            
        self.logger.info(
            f"HTTP {method} {path} - {status_code} - {duration_ms:.2f}ms",
            extra={'extra_fields': extra_fields}
        )
    
    def log_database_query(
        self,
        query_type: str,
        table: str,
        duration_ms: float,
        rows_affected: int = None,
        extra: Dict = None
    ):
        """Log database query performance."""
        extra_fields = {
            'event_type': 'database_query',
            'query_type': query_type,
            'table': table,
            'duration_ms': duration_ms,
            **(extra or {})
        }
        
        if rows_affected is not None:
            extra_fields['rows_affected'] = rows_affected
            
        self.logger.info(
            f"DB {query_type} on {table} - {duration_ms:.2f}ms",
            extra={'extra_fields': extra_fields}
        )
    
    def log_external_api_call(
        self,
        api_name: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        success: bool,
        extra: Dict = None
    ):
        """Log external API call performance."""
        extra_fields = {
            'event_type': 'external_api_call',
            'api_name': api_name,
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'success': success,
            **(extra or {})
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"API {api_name} {method} {endpoint} - {status_code} - {duration_ms:.2f}ms",
            extra={'extra_fields': extra_fields}
        )
    
    def log_cache_operation(
        self,
        operation: str,
        cache_type: str,
        key: str,
        hit: bool = None,
        duration_ms: float = None,
        extra: Dict = None
    ):
        """Log cache operation performance."""
        extra_fields = {
            'event_type': 'cache_operation',
            'operation': operation,
            'cache_type': cache_type,
            'cache_key': key,
            **(extra or {})
        }
        
        if hit is not None:
            extra_fields['cache_hit'] = hit
        if duration_ms is not None:
            extra_fields['duration_ms'] = duration_ms
            
        self.logger.debug(
            f"Cache {operation} {cache_type} - {key}",
            extra={'extra_fields': extra_fields}
        )


class SecurityLogger:
    """
    Logger for security-related events and audit trails.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def log_authentication(
        self,
        user_id: str,
        event_type: str,
        success: bool,
        ip_address: str = None,
        user_agent: str = None,
        extra: Dict = None
    ):
        """Log authentication events."""
        extra_fields = {
            'event_type': 'authentication',
            'auth_event': event_type,
            'user_id': user_id,
            'success': success,
            **(extra or {})
        }
        
        if ip_address:
            extra_fields['ip_address'] = ip_address
        if user_agent:
            extra_fields['user_agent'] = user_agent
            
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"Auth {event_type} for user {user_id} - {'success' if success else 'failed'}",
            extra={'extra_fields': extra_fields}
        )
    
    def log_authorization(
        self,
        user_id: str,
        resource: str,
        action: str,
        granted: bool,
        reason: str = None,
        extra: Dict = None
    ):
        """Log authorization events."""
        extra_fields = {
            'event_type': 'authorization',
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'granted': granted,
            **(extra or {})
        }
        
        if reason:
            extra_fields['reason'] = reason
            
        level = logging.INFO if granted else logging.WARNING
        self.logger.log(
            level,
            f"Authorization {action} on {resource} for user {user_id} - "
            f"{'granted' if granted else 'denied'}",
            extra={'extra_fields': extra_fields}
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: str = None,
        ip_address: str = None,
        extra: Dict = None
    ):
        """Log general security events."""
        extra_fields = {
            'event_type': 'security_event',
            'security_event_type': event_type,
            'severity': severity,
            'description': description,
            **(extra or {})
        }
        
        if user_id:
            extra_fields['user_id'] = user_id
        if ip_address:
            extra_fields['ip_address'] = ip_address
            
        # Map severity to log level
        level_map = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }
        level = level_map.get(severity.lower(), logging.WARNING)
        
        self.logger.log(
            level,
            f"Security event {event_type}: {description}",
            extra={'extra_fields': extra_fields}
        )


class StructuredLogger:
    """
    Enhanced logger with structured logging capabilities.
    
    Provides methods for logging different types of events with
    consistent structure and contextual information.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.performance = PerformanceLogger(self.logger)
        self.security = SecurityLogger(self.logger)
        
    def debug(self, message: str, extra: Dict = None, **kwargs):
        """Log debug message with extra fields."""
        self._log(logging.DEBUG, message, extra, **kwargs)
    
    def info(self, message: str, extra: Dict = None, **kwargs):
        """Log info message with extra fields."""
        self._log(logging.INFO, message, extra, **kwargs)
    
    def warning(self, message: str, extra: Dict = None, **kwargs):
        """Log warning message with extra fields."""
        self._log(logging.WARNING, message, extra, **kwargs)
    
    def error(self, message: str, extra: Dict = None, exc_info: bool = False, **kwargs):
        """Log error message with extra fields."""
        self._log(logging.ERROR, message, extra, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, extra: Dict = None, exc_info: bool = False, **kwargs):
        """Log critical message with extra fields."""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info, **kwargs)
    
    def _log(self, level: int, message: str, extra: Dict = None, **kwargs):
        """Internal log method with extra fields handling."""
        extra_fields = extra or {}
        
        # Add any additional kwargs as extra fields
        for key, value in kwargs.items():
            if key not in ['exc_info', 'stack_info', 'stacklevel']:
                extra_fields[key] = value
        
        # Remove extra fields from kwargs to avoid conflict
        clean_kwargs = {k: v for k, v in kwargs.items() 
                       if k in ['exc_info', 'stack_info', 'stacklevel']}
        
        if extra_fields:
            clean_kwargs['extra'] = {'extra_fields': extra_fields}
        
        self.logger.log(level, message, **clean_kwargs)
    
    def log_user_action(
        self,
        action: str,
        user_id: str,
        resource: str = None,
        result: str = 'success',
        extra: Dict = None
    ):
        """Log user action for audit trail."""
        extra_fields = {
            'event_type': 'user_action',
            'action': action,
            'user_id': user_id,
            'result': result,
            **(extra or {})
        }
        
        if resource:
            extra_fields['resource'] = resource
            
        self.info(
            f"User {user_id} performed {action}" + 
            (f" on {resource}" if resource else ""),
            extra=extra_fields
        )
    
    def log_business_event(
        self,
        event_type: str,
        description: str,
        entity_id: str = None,
        entity_type: str = None,
        extra: Dict = None
    ):
        """Log business events for analytics."""
        extra_fields = {
            'event_type': 'business_event',
            'business_event_type': event_type,
            'description': description,
            **(extra or {})
        }
        
        if entity_id:
            extra_fields['entity_id'] = entity_id
        if entity_type:
            extra_fields['entity_type'] = entity_type
            
        self.info(description, extra=extra_fields)


def setup_logging(
    log_level: str = None,
    log_format: str = 'json',
    log_file: str = None,
    enable_console: bool = True
) -> logging.Logger:  # <- updated return type
    """
    Setup application logging configuration.
    ...
    """
    global _logging_configured

    if _logging_configured:
        return logging.getLogger("startup")  # or any default named logger

    try:
        settings = get_settings()
        log_level = log_level or settings.LOG_LEVEL
        log_format = log_format or getattr(settings, 'LOG_FORMAT', 'json')
        log_file = log_file or getattr(settings, 'LOG_FILE', None)
    except Exception:
        log_level = log_level or 'INFO'
        log_format = log_format or 'json'

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    if log_format.lower() == 'json' and HAS_JSON_LOGGER:
        formatter = JSONFormatter()
    else:
        formatter = ContextualFormatter('%(timestamp)s - %(name)s - %(levelname)s - %(message)s')

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    _logging_configured = True
    return logging.getLogger("startup")  # ✅ Add this


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        StructuredLogger instance
    """
    if name in _loggers_cache:
        return _loggers_cache[name]
    
    logger = StructuredLogger(name)
    _loggers_cache[name] = logger
    
    return logger


@contextmanager
def log_context(
    request_id: str = None,
    user_id: str = None, 
    correlation_id: str = None
):
    """
    Context manager for adding contextual information to logs.
    
    Args:
        request_id: Request identifier
        user_id: User identifier
        correlation_id: Correlation identifier for distributed tracing
    """
    # Generate request ID if not provided
    if request_id is None:
        request_id = str(uuid4())
    
    # Set context variables
    request_token = request_id_var.set(request_id)
    user_token = user_id_var.set(user_id or '')
    correlation_token = correlation_id_var.set(correlation_id or '')
    
    try:
        yield {
            'request_id': request_id,
            'user_id': user_id,
            'correlation_id': correlation_id
        }
    finally:
        # Reset context variables
        request_id_var.reset(request_token)
        user_id_var.reset(user_token)
        correlation_id_var.reset(correlation_token)


def log_function_call(func_name: str = None):
    """
    Decorator for logging function calls with timing.
    
    Args:
        func_name: Custom function name for logging
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            name = func_name or func.__name__
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"Function {name} completed successfully",
                    extra={
                        'function': name,
                        'duration_ms': duration,
                        'event_type': 'function_call'
                    }
                )
                
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                
                logger.error(
                    f"Function {name} failed: {e}",
                    extra={
                        'function': name,
                        'duration_ms': duration,
                        'event_type': 'function_call',
                        'error': str(e)
                    },
                    exc_info=True
                )
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            name = func_name or func.__name__
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"Function {name} completed successfully",
                    extra={
                        'function': name,
                        'duration_ms': duration,
                        'event_type': 'function_call'
                    }
                )
                
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                
                logger.error(
                    f"Function {name} failed: {e}",
                    extra={
                        'function': name,
                        'duration_ms': duration,
                        'event_type': 'function_call',
                        'error': str(e)
                    },
                    exc_info=True
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience functions for common logging patterns
def log_startup_event(service_name: str, version: str, extra: Dict = None):
    """Log application startup event."""
    logger = get_logger('startup')
    logger.info(
        f"Service {service_name} starting up",
        extra={
            'event_type': 'service_startup',
            'service_name': service_name,
            'version': version,
            **(extra or {})
        }
    )


def log_shutdown_event(service_name: str, extra: Dict = None):
    """Log application shutdown event."""
    logger = get_logger('shutdown')
    logger.info(
        f"Service {service_name} shutting down",
        extra={
            'event_type': 'service_shutdown',
            'service_name': service_name,
            **(extra or {})
        }
    )


def log_health_check(component: str, status: str, extra: Dict = None):
    """Log health check results."""
    logger = get_logger('health')
    level = logging.INFO if status == 'healthy' else logging.WARNING
    
    logger.log(
        level,
        f"Health check for {component}: {status}",
        extra={
            'event_type': 'health_check',
            'component': component,
            'status': status,
            **(extra or {})
        }
    )


# Import asyncio here to avoid circular imports
import asyncio