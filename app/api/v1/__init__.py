# 📄 File: app/api/v1/__init__.py
# 🧭 Purpose (Layman Explanation): 
# This file organizes version 1 of our API, like having a dedicated section for the first version
# of our plant care features so we can add new versions later without breaking existing apps.
# 🧪 Purpose (Technical Summary): 
# Package initialization for API version 1, providing router organization, version-specific
# configuration, and centralized imports for all v1 API endpoints.
# 🔗 Dependencies: 
# FastAPI, app.shared.config.settings
# 🔄 Connected Modules / Calls From: 
# app.api.v1.router, app.main.py, all v1 route modules

"""
Plant Care Application API Version 1

This package contains all API version 1 endpoints and functionality.
API v1 provides the core plant care features including:

Core Features:
- User authentication and profile management
- Plant management (CRUD, identification, library)
- Care scheduling and reminders
- Health monitoring and diagnosis
- Growth tracking and analytics
- Community features and social interactions
- AI-powered smart features
- Weather and environmental data
- Analytics and insights
- Notifications and communication
- Payment and subscription management
- Content management

Structure:
    v1/
    ├── __init__.py          # This file
    ├── router.py            # Main v1 router aggregation
    ├── health.py            # Health check endpoints
    └── [future modules]/    # Individual module routers
        ├── users.py         # User management endpoints
        ├── plants.py        # Plant management endpoints  
        ├── care.py          # Care management endpoints
        ├── health.py        # Health monitoring endpoints
        ├── growth.py        # Growth tracking endpoints
        ├── community.py     # Community features endpoints
        ├── ai.py            # AI features endpoints
        ├── weather.py       # Weather endpoints
        ├── analytics.py     # Analytics endpoints
        ├── notifications.py # Notification endpoints
        ├── payments.py      # Payment endpoints
        └── content.py       # Content management endpoints
"""

from typing import Dict, Any

# API v1 metadata
__version__ = "1.0.0"
__api_version__ = "v1"
__release_date__ = "2024-01-15"
__status__ = "stable"

# API v1 configuration
API_V1_CONFIG = {
    "version": __version__,
    "api_version": __api_version__,
    "release_date": __release_date__,
    "status": __status__,
    "description": "Plant Care Application API Version 1",
    "features": [
        "user_management",
        "plant_management", 
        "care_scheduling",
        "health_monitoring",
        "growth_tracking",
        "community_features",
        "ai_smart_features",
        "weather_integration",
        "analytics_insights",
        "notifications",
        "payments",
        "content_management"
    ],
    "deprecated_features": [],
    "breaking_changes": [],
    "migration_notes": "Initial API version - no migration needed"
}

# API v1 route prefixes
ROUTE_PREFIXES = {
    "auth": "/auth",
    "users": "/users", 
    "plants": "/plants",
    "care": "/care",
    "health": "/health",
    "growth": "/growth",
    "community": "/community",
    "ai": "/ai",
    "weather": "/weather",
    "analytics": "/analytics",
    "notifications": "/notifications",
    "payments": "/payments",
    "content": "/content",
    "admin": "/admin"
}

# API v1 tags for OpenAPI documentation
API_TAGS = [
    {
        "name": "Authentication",
        "description": "User authentication and authorization endpoints"
    },
    {
        "name": "Users",
        "description": "User profile and account management"
    },
    {
        "name": "Plants",
        "description": "Plant management, identification, and library"
    },
    {
        "name": "Care",
        "description": "Plant care scheduling and task management"
    },
    {
        "name": "Health",
        "description": "Plant health monitoring and diagnosis"
    },
    {
        "name": "Growth", 
        "description": "Plant growth tracking and milestones"
    },
    {
        "name": "Community",
        "description": "Social features and community interactions"
    },
    {
        "name": "AI",
        "description": "AI-powered smart features and recommendations"
    },
    {
        "name": "Weather",
        "description": "Weather data and environmental monitoring"
    },
    {
        "name": "Analytics",
        "description": "Analytics, insights, and reporting"
    },
    {
        "name": "Notifications",
        "description": "Notification and communication management"
    },
    {
        "name": "Payments",
        "description": "Payment processing and subscription management"
    },
    {
        "name": "Content",
        "description": "Content and knowledge base management"
    },
    {
        "name": "Admin",
        "description": "Administrative functions and system management"
    },
    {
        "name": "Health Check",
        "description": "System health and status monitoring"
    }
]

# Response schemas for common API responses
COMMON_RESPONSES = {
    200: {"description": "Successful operation"},
    201: {"description": "Resource created successfully"},
    400: {"description": "Bad request - validation error"},
    401: {"description": "Unauthorized - authentication required"},
    403: {"description": "Forbidden - insufficient permissions"},
    404: {"description": "Resource not found"},
    409: {"description": "Conflict - resource already exists"},
    422: {"description": "Unprocessable entity - validation failed"},
    429: {"description": "Too many requests - rate limit exceeded"},
    500: {"description": "Internal server error"},
    503: {"description": "Service unavailable"}
}

# Rate limiting configuration for v1 endpoints
RATE_LIMITS = {
    "default": "100/minute",
    "auth_login": "5/minute",
    "auth_register": "3/minute", 
    "plant_identification": "10/minute",
    "file_upload": "20/minute",
    "ai_chat": "30/minute",
    "premium_default": "500/minute",
    "admin_default": "1000/minute"
}

# Feature flags for v1 API
FEATURE_FLAGS = {
    "plant_identification": True,
    "ai_chat": True,
    "community_features": True,
    "payment_processing": True,
    "admin_panel": True,
    "weather_integration": True,
    "growth_tracking": True,
    "health_monitoring": True,
    "notifications": True,
    "analytics": True
}

def get_api_info() -> Dict[str, Any]:
    """
    Get API v1 information and configuration
    
    Returns:
        Dictionary with API v1 metadata and configuration
    """
    return {
        "api_info": API_V1_CONFIG,
        "route_prefixes": ROUTE_PREFIXES,
        "tags": API_TAGS,
        "rate_limits": RATE_LIMITS,
        "feature_flags": FEATURE_FLAGS,
        "common_responses": COMMON_RESPONSES
    }

def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if a feature is enabled in v1 API
    
    Args:
        feature_name: Name of the feature to check
        
    Returns:
        True if feature is enabled, False otherwise
    """
    return FEATURE_FLAGS.get(feature_name, False)

# Export commonly used items
__all__ = [
    "API_V1_CONFIG",
    "ROUTE_PREFIXES", 
    "API_TAGS",
    "COMMON_RESPONSES",
    "RATE_LIMITS",
    "FEATURE_FLAGS",
    "get_api_info",
    "is_feature_enabled"
]