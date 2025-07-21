# 📄 File: app/api/v1/router.py
# 🧭 Purpose (Layman Explanation): 
# This file acts like a traffic director for all API version 1 requests, organizing and routing them
# to the right places like sending plant requests to plant handlers and user requests to user handlers.
# 🧪 Purpose (Technical Summary): 
# Main API v1 router aggregation that combines all module routers, configures route prefixes,
# and provides centralized routing management for the FastAPI application.
# 🔗 Dependencies: 
# FastAPI, app.api.v1.health, future module routers
# 🔄 Connected Modules / Calls From: 
# app.main.py, all v1 module routers (when implemented)

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import get_api_info, ROUTE_PREFIXES, API_TAGS
from .health import health_router

logger = logging.getLogger(__name__)

# Create main API v1 router
api_v1_router = APIRouter()

# Include health check router (no prefix - direct access)
api_v1_router.include_router(
    health_router,
    tags=["Health Check"]
)

# =========================================================================
# API V1 INFO ENDPOINT
# =========================================================================

@api_v1_router.get("/",
                  summary="API v1 Information",
                  description="Get API v1 version information and available endpoints",
                  tags=["API Info"])
async def api_v1_info() -> JSONResponse:
    """
    API v1 information endpoint
    
    Provides comprehensive information about API v1 including:
    - Version details
    - Available endpoints and routes
    - Feature flags
    - Rate limiting information
    - API documentation links
    """
    try:
        api_info = get_api_info()
        
        # Add runtime information
        runtime_info = {
            "endpoints": {
                "health_check": "/health",
                "detailed_health": "/health/detailed", 
                "liveness_probe": "/health/live",
                "readiness_probe": "/health/ready",
                "startup_probe": "/health/startup",
                "metrics": "/metrics"
            },
            "documentation": {
                "openapi_schema": "/openapi.json",
                "swagger_ui": "/docs",
                "redoc": "/redoc"
            },
            "available_modules": _get_available_modules(),
            "module_status": _get_module_status()
        }
        
        return JSONResponse(
            status_code=200,
            content={
                **api_info,
                "runtime_info": runtime_info
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get API v1 info: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve API information",
                "detail": str(e)
            }
        )


@api_v1_router.get("/status",
                  summary="API v1 Status",
                  description="Get current API v1 operational status",
                  tags=["API Info"])
async def api_v1_status() -> JSONResponse:
    """
    API v1 status endpoint
    
    Provides current operational status including:
    - Service availability
    - Module health status
    - Feature availability
    - System load information
    """
    try:
        status_info = {
            "service": "plant-care-api-v1",
            "status": "operational",
            "modules": _get_module_status(),
            "features": _get_feature_status(),
            "last_updated": "2024-01-15T00:00:00Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=status_info
        )
        
    except Exception as e:
        logger.error(f"Failed to get API v1 status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve API status",
                "detail": str(e)
            }
        )


# =========================================================================
# MODULE ROUTER INCLUDES (TO BE ADDED AS MODULES ARE IMPLEMENTED)
# =========================================================================

# NOTE: These router includes will be uncommented as modules are implemented

# Authentication & Users
# from app.modules.user_management.presentation.api.v1.auth import auth_router
# from app.modules.user_management.presentation.api.v1.users import users_router
# from app.modules.user_management.presentation.api.v1.profiles import profiles_router

# api_v1_router.include_router(
#     auth_router,
#     prefix=ROUTE_PREFIXES["auth"],
#     tags=["Authentication"]
# )

# api_v1_router.include_router(
#     users_router,
#     prefix=ROUTE_PREFIXES["users"],
#     tags=["Users"]
# )

# Plant Management
# from app.modules.plant_management.presentation.api.v1.plants import plants_router
# from app.modules.plant_management.presentation.api.v1.library import library_router
# from app.modules.plant_management.presentation.api.v1.identification import identification_router

# api_v1_router.include_router(
#     plants_router,
#     prefix=ROUTE_PREFIXES["plants"],
#     tags=["Plants"]
# )

# Care Management
# from app.modules.care_management.presentation.api.v1.schedules import schedules_router
# from app.modules.care_management.presentation.api.v1.tasks import tasks_router
# from app.modules.care_management.presentation.api.v1.history import history_router

# api_v1_router.include_router(
#     schedules_router,
#     prefix=ROUTE_PREFIXES["care"],
#     tags=["Care"]
# )

# Health Monitoring
# from app.modules.health_monitoring.presentation.api.v1.health import health_monitoring_router
# from app.modules.health_monitoring.presentation.api.v1.diagnosis import diagnosis_router
# from app.modules.health_monitoring.presentation.api.v1.treatments import treatments_router

# api_v1_router.include_router(
#     health_monitoring_router,
#     prefix=ROUTE_PREFIXES["health"],
#     tags=["Health"]
# )

# Growth Tracking
# from app.modules.growth_tracking.presentation.api.v1.growth import growth_router
# from app.modules.growth_tracking.presentation.api.v1.milestones import milestones_router
# from app.modules.growth_tracking.presentation.api.v1.analysis import analysis_router

# api_v1_router.include_router(
#     growth_router,
#     prefix=ROUTE_PREFIXES["growth"],
#     tags=["Growth"]
# )

# Community & Social
# from app.modules.community_social.presentation.api.v1.posts import posts_router
# from app.modules.community_social.presentation.api.v1.feed import feed_router
# from app.modules.community_social.presentation.api.v1.interactions import interactions_router

# api_v1_router.include_router(
#     posts_router,
#     prefix=ROUTE_PREFIXES["community"],
#     tags=["Community"]
# )

# AI & Smart Features
# from app.modules.ai_smart_features.presentation.api.v1.chat import chat_router
# from app.modules.ai_smart_features.presentation.api.v1.recommendations import recommendations_router
# from app.modules.ai_smart_features.presentation.api.v1.automation import automation_router

# api_v1_router.include_router(
#     chat_router,
#     prefix=ROUTE_PREFIXES["ai"],
#     tags=["AI"]
# )

# Weather & Environmental
# from app.modules.weather_environmental.presentation.api.v1.weather import weather_router
# from app.modules.weather_environmental.presentation.api.v1.environment import environment_router

# api_v1_router.include_router(
#     weather_router,
#     prefix=ROUTE_PREFIXES["weather"],
#     tags=["Weather"]
# )

# Analytics & Insights
# from app.modules.analytics_insights.presentation.api.v1.analytics import analytics_router
# from app.modules.analytics_insights.presentation.api.v1.insights import insights_router

# api_v1_router.include_router(
#     analytics_router,
#     prefix=ROUTE_PREFIXES["analytics"],
#     tags=["Analytics"]
# )

# Notification & Communication
# from app.modules.notification_communication.presentation.api.v1.notifications import notifications_router
# from app.modules.notification_communication.presentation.api.v1.templates import templates_router

# api_v1_router.include_router(
#     notifications_router,
#     prefix=ROUTE_PREFIXES["notifications"],
#     tags=["Notifications"]
# )

# Payment & Subscription
# from app.modules.payment_subscription.presentation.api.v1.payments import payments_router
# from app.modules.payment_subscription.presentation.api.v1.subscriptions import subscriptions_router
# from app.modules.payment_subscription.presentation.api.v1.webhooks import webhooks_router

# api_v1_router.include_router(
#     payments_router,
#     prefix=ROUTE_PREFIXES["payments"],
#     tags=["Payments"]
# )

# Content Management
# from app.modules.content_management.presentation.api.v1.content import content_router
# from app.modules.content_management.presentation.api.v1.knowledge import knowledge_router
# from app.modules.content_management.presentation.api.v1.translations import translations_router
# from app.modules.content_management.presentation.api.v1.locales import locales_router

# api_v1_router.include_router(
#     content_router,
#     prefix=ROUTE_PREFIXES["content"],
#     tags=["Content"]
# )

# Admin Management
# from app.modules.admin_management.presentation.api.v1.admin_dashboard import admin_dashboard_router
# from app.modules.admin_management.presentation.api.v1.user_admin import user_admin_router
# from app.modules.admin_management.presentation.api.v1.plant_admin import plant_admin_router
# from app.modules.admin_management.presentation.api.v1.system_admin import system_admin_router

# api_v1_router.include_router(
#     admin_dashboard_router,
#     prefix=ROUTE_PREFIXES["admin"],
#     tags=["Admin"]
# )


# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================

def _get_available_modules() -> Dict[str, Dict[str, Any]]:
    """
    Get information about available API modules
    
    Returns:
        Dictionary with module availability and status
    """
    modules = {
        "authentication": {
            "status": "planned",
            "description": "User authentication and authorization",
            "routes": ["/auth/login", "/auth/register", "/auth/refresh"],
            "implemented": False
        },
        "users": {
            "status": "planned", 
            "description": "User profile and account management",
            "routes": ["/users/profile", "/users/settings"],
            "implemented": False
        },
        "plants": {
            "status": "planned",
            "description": "Plant management and identification",
            "routes": ["/plants", "/plants/identify", "/plants/library"],
            "implemented": False
        },
        "care": {
            "status": "planned",
            "description": "Plant care scheduling and tracking",
            "routes": ["/care/schedules", "/care/tasks", "/care/history"],
            "implemented": False
        },
        "health": {
            "status": "planned",
            "description": "Plant health monitoring and diagnosis", 
            "routes": ["/health/records", "/health/diagnosis"],
            "implemented": False
        },
        "growth": {
            "status": "planned",
            "description": "Plant growth tracking and analysis",
            "routes": ["/growth/timeline", "/growth/milestones"],
            "implemented": False
        },
        "community": {
            "status": "planned",
            "description": "Social features and community interaction",
            "routes": ["/community/posts", "/community/feed"],
            "implemented": False
        },
        "ai": {
            "status": "planned",
            "description": "AI-powered smart features",
            "routes": ["/ai/chat", "/ai/recommendations"],
            "implemented": False
        },
        "weather": {
            "status": "planned",
            "description": "Weather and environmental data",
            "routes": ["/weather/current", "/weather/forecast"],
            "implemented": False
        },
        "analytics": {
            "status": "planned",
            "description": "Analytics and insights",
            "routes": ["/analytics/dashboard", "/analytics/reports"],
            "implemented": False
        },
        "notifications": {
            "status": "planned",
            "description": "Notification and communication management",
            "routes": ["/notifications", "/notifications/preferences"],
            "implemented": False
        },
        "payments": {
            "status": "planned",
            "description": "Payment processing and subscriptions",
            "routes": ["/payments/process", "/payments/subscriptions"],
            "implemented": False
        },
        "content": {
            "status": "planned",
            "description": "Content and knowledge base management",
            "routes": ["/content/articles", "/content/knowledge"],
            "implemented": False
        },
        "admin": {
            "status": "planned",
            "description": "Administrative functions",
            "routes": ["/admin/dashboard", "/admin/users", "/admin/system"],
            "implemented": False
        }
    }
    
    return modules


def _get_module_status() -> Dict[str, str]:
    """
    Get current implementation status of all modules
    
    Returns:
        Dictionary with module names and their implementation status
    """
    modules = _get_available_modules()
    return {
        module_name: module_info["status"] 
        for module_name, module_info in modules.items()
    }


def _get_feature_status() -> Dict[str, str]:
    """
    Get current status of major features
    
    Returns:
        Dictionary with feature names and their availability status
    """
    return {
        "user_authentication": "planned",
        "plant_identification": "planned", 
        "care_scheduling": "planned",
        "health_monitoring": "planned",
        "growth_tracking": "planned",
        "ai_chat": "planned",
        "community_features": "planned",
        "weather_integration": "planned",
        "payment_processing": "planned",
        "admin_panel": "planned",
        "mobile_app_support": "planned",
        "real_time_notifications": "planned",
        "offline_mode": "planned",
        "multi_language": "planned"
    }
 