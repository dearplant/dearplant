# 📄 File: app/shared/infrastructure/external_apis/__init__.py

# 🧭 Purpose (Layman Explanation):
# This file sets up the foundation for communicating with external services like plant identification APIs,
# weather services, and AI chatbots in a reliable and organized way.

# 🧪 Purpose (Technical Summary):
# Initializes external API infrastructure including client management, rotation strategies,
# circuit breakers, and rate limiting for all third-party service integrations.

# 🔗 Dependencies:
# - api_client: Generic HTTP client with retry logic
# - api_rotation: API rotation and failover management
# - circuit_breaker: Circuit breaker for API resilience

# 🔄 Connected Modules / Calls From:
# Used by: Plant identification, Weather services, AI chat, Content moderation,
# Payment processing, Analytics services, Translation services

"""
External APIs Infrastructure Module

This module provides a robust foundation for integrating with third-party APIs
including plant identification services, weather APIs, AI services, and more.

Key Features:
- API rotation and failover
- Circuit breaker pattern for resilience
- Rate limiting and quota management
- Centralized error handling
- Request/response caching
- Performance monitoring
"""

from typing import Dict, Any, Optional
import logging

from app.shared.utils.logging import get_logger

logger = get_logger(__name__)

# API Categories for organization
API_CATEGORIES = {
    'plant_identification': [
        'plantnet', 'trefle', 'plant_id', 'kindwise'
    ],
    'weather': [
        'openweathermap', 'tomorrow_io', 'weatherstack', 'visual_crossing'
    ],
    'ai_services': [
        'openai', 'gemini', 'claude', 'perspective'
    ],
    'translation': [
        'google_translate', 'deepl', 'azure_translate'
    ],
    'payment': [
        'razorpay', 'stripe'
    ],
    'communication': [
        'fcm', 'sendgrid', 'telegram'
    ],
    'analytics': [
        'mixpanel', 'google_analytics'
    ]
}

# API Priority Configuration
API_PRIORITIES = {
    'plant_identification': {
        'plantnet': 1,
        'trefle': 2,
        'plant_id': 3,
        'kindwise': 4
    },
    'weather': {
        'openweathermap': 1,
        'tomorrow_io': 2,
        'weatherstack': 3,
        'visual_crossing': 4
    },
    'ai_services': {
        'openai': 1,
        'gemini': 2,
        'claude': 3
    }
}

# Default API Limits
DEFAULT_API_LIMITS = {
    'requests_per_minute': 60,
    'requests_per_hour': 1000,
    'requests_per_day': 10000,
    'concurrent_requests': 5,
    'timeout_seconds': 30,
    'retry_attempts': 3
}

# Circuit Breaker Configuration
CIRCUIT_BREAKER_CONFIG = {
    'failure_threshold': 5,
    'recovery_timeout': 60,
    'expected_exception': Exception
}


class ExternalAPIError(Exception):
    """Base exception for external API errors."""
    pass


class APIRateLimitError(ExternalAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class APICircuitBreakerError(ExternalAPIError):
    """Raised when circuit breaker is open."""
    pass


class APIRotationError(ExternalAPIError):
    """Raised when all APIs in rotation have failed."""
    pass


def get_api_config(api_name: str) -> Dict[str, Any]:
    """Get configuration for specific API."""
    configs = {
        # Plant identification APIs
        'plantnet': {
            'base_url': 'https://my-api.plantnet.org/v1',
            'rate_limits': {
                'free': {'daily': 50, 'hourly': 10},
                'premium': {'daily': 500, 'hourly': 100}
            },
            'priority': 1,
            'timeout': 30
        },
        'trefle': {
            'base_url': 'https://trefle.io/api/v1',
            'rate_limits': {
                'free': {'daily': 120, 'hourly': 20},
                'premium': {'daily': 1200, 'hourly': 200}
            },
            'priority': 2,
            'timeout': 25
        },
        'plant_id': {
            'base_url': 'https://api.plant.id/v2',
            'rate_limits': {
                'free': {'daily': 100, 'hourly': 20},
                'premium': {'daily': 1000, 'hourly': 200}
            },
            'priority': 3,
            'timeout': 35
        },
        'kindwise': {
            'base_url': 'https://plant.id/api/v1',
            'rate_limits': {
                'free': {'daily': 50, 'hourly': 10},
                'premium': {'daily': 500, 'hourly': 100}
            },
            'priority': 4,
            'timeout': 30
        },
        
        # Weather APIs
        'openweathermap': {
            'base_url': 'https://api.openweathermap.org/data/2.5',
            'rate_limits': {
                'free': {'daily': 1000, 'minute': 60},
                'premium': {'daily': 10000, 'minute': 600}
            },
            'priority': 1,
            'timeout': 20
        },
        'tomorrow_io': {
            'base_url': 'https://api.tomorrow.io/v4',
            'rate_limits': {
                'free': {'daily': 100, 'hour': 25},
                'premium': {'daily': 1000, 'hour': 250}
            },
            'priority': 2,
            'timeout': 25
        },
        'weatherstack': {
            'base_url': 'https://api.weatherstack.com/current',
            'rate_limits': {
                'free': {'monthly': 1000, 'hour': 100},
                'premium': {'monthly': 10000, 'hour': 1000}
            },
            'priority': 3,
            'timeout': 20
        },
        'visual_crossing': {
            'base_url': 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services',
            'rate_limits': {
                'free': {'daily': 1000, 'hour': 100},
                'premium': {'daily': 10000, 'hour': 1000}
            },
            'priority': 4,
            'timeout': 25
        },
        
        # AI Services
        'openai': {
            'base_url': 'https://api.openai.com/v1',
            'rate_limits': {
                'premium': {'minute': 3500, 'hour': 90000}
            },
            'priority': 1,
            'timeout': 60
        },
        'gemini': {
            'base_url': 'https://generativelanguage.googleapis.com/v1',
            'rate_limits': {
                'free': {'minute': 15, 'hour': 1500},
                'premium': {'minute': 1000, 'hour': 32000}
            },
            'priority': 2,
            'timeout': 45
        },
        'claude': {
            'base_url': 'https://api.anthropic.com/v1',
            'rate_limits': {
                'premium': {'minute': 1000, 'hour': 40000}
            },
            'priority': 3,
            'timeout': 60
        }
    }
    
    return configs.get(api_name, {})


def get_category_apis(category: str) -> list:
    """Get list of APIs for a specific category."""
    return API_CATEGORIES.get(category, [])


def get_api_priority(category: str, api_name: str) -> int:
    """Get priority for API within its category."""
    category_priorities = API_PRIORITIES.get(category, {})
    return category_priorities.get(api_name, 999)  # Default low priority


# Global registry for API clients
_api_clients_registry = {}
_api_rotation_managers = {}
_circuit_breakers = {}


def register_api_client(api_name: str, client_instance):
    """Register an API client instance."""
    _api_clients_registry[api_name] = client_instance
    logger.info(f"Registered API client: {api_name}")


def get_api_client(api_name: str):
    """Get registered API client instance."""
    return _api_clients_registry.get(api_name)


def register_rotation_manager(category: str, manager_instance):
    """Register API rotation manager for category."""
    _api_rotation_managers[category] = manager_instance
    logger.info(f"Registered rotation manager for category: {category}")


def get_rotation_manager(category: str):
    """Get rotation manager for category."""
    return _api_rotation_managers.get(category)


def register_circuit_breaker(api_name: str, breaker_instance):
    """Register circuit breaker for API."""
    _circuit_breakers[api_name] = breaker_instance
    logger.info(f"Registered circuit breaker for API: {api_name}")


def get_circuit_breaker(api_name: str):
    """Get circuit breaker for API."""
    return _circuit_breakers.get(api_name)


async def initialize_external_apis():
    """Initialize all external API infrastructure."""
    try:
        logger.info("Initializing external API infrastructure...")
        
        # This will be called during application startup
        # to initialize API clients, rotation managers, and circuit breakers
        
        logger.info("External API infrastructure initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize external API infrastructure: {e}")
        raise


async def cleanup_external_apis():
    """Cleanup external API resources."""
    try:
        # Close any open connections, clear caches, etc.
        _api_clients_registry.clear()
        _api_rotation_managers.clear()
        _circuit_breakers.clear()
        
        logger.info("External API infrastructure cleaned up")
        
    except Exception as e:
        logger.error(f"Failed to cleanup external API infrastructure: {e}")


def get_api_status() -> Dict[str, Any]:
    """Get status of all registered APIs."""
    status = {
        'registered_clients': len(_api_clients_registry),
        'rotation_managers': len(_api_rotation_managers),
        'circuit_breakers': len(_circuit_breakers),
        'categories': list(API_CATEGORIES.keys()),
        'clients': list(_api_clients_registry.keys())
    }
    
    return status


__all__ = [
    'API_CATEGORIES',
    'API_PRIORITIES',
    'DEFAULT_API_LIMITS',
    'CIRCUIT_BREAKER_CONFIG',
    'ExternalAPIError',
    'APIRateLimitError',
    'APICircuitBreakerError',
    'APIRotationError',
    'get_api_config',
    'get_category_apis',
    'get_api_priority',
    'register_api_client',
    'get_api_client',
    'register_rotation_manager',
    'get_rotation_manager',
    'register_circuit_breaker',
    'get_circuit_breaker',
    'initialize_external_apis',
    'cleanup_external_apis',
    'get_api_status'
]