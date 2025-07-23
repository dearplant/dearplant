# 📄 File: app/api/v1/router.py
# 🧭 Purpose (Layman Explanation): 
# This file acts like a traffic director for all API version 1 requests, organizing and routing them
# to the right places like sending plant requests to plant handlers and user requests to user handlers.
# 🧪 Purpose (Technical Summary): 
# Main API v1 router aggregation that combines all module routers, configures route prefixes,
# and provides centralized routing management for the FastAPI application.
# 🔗 Dependencies: 
# FastAPI, app.api.v1.health, app.modules.user_management.presentation.api.v1.*
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
# MODULE ROUTER INCLUDES - USER MANAGEMENT MODULE (ACTIVE)
# =========================================================================


# 🎉 USER MANAGEMENT MODULE - FULLY IMPLEMENTED AND ACTIVE
logger.info("🚀 Loading User Management module routers...")

for name, prefix, import_path, tag in [
    ("Authentication", ROUTE_PREFIXES["auth"], "app.modules.user_management.presentation.api.v1.auth:auth_router", "Authentication"),
    ("Users", ROUTE_PREFIXES["users"], "app.modules.user_management.presentation.api.v1.users:users_router", "Users"),
    ("Profiles", "/profiles", "app.modules.user_management.presentation.api.v1.profiles:profiles_router", "Profiles")
]:
    try:
        module_path, router_name = import_path.split(":")
        mod = __import__(module_path, fromlist=[router_name])
        router = getattr(mod, router_name)
        api_v1_router.include_router(router, prefix=prefix, tags=[tag])
        logger.info(f"✅ {name} router loaded")
    except ImportError as e:
        logger.error(f"❌ Failed to load {name} router: {e}")
        logger.warning(f"🔄 {name} module router not available - check implementation")
    except Exception as e:
        import traceback
        logger.error(f"❌ Unexpected error loading {name} module: {e}")
        traceback.print_exc()

logger.info("🌟 User Management module router setup complete!")


# =========================================================================
# MODULE ROUTER INCLUDES (TO BE ADDED AS MODULES ARE IMPLEMENTED)
# =========================================================================

# NOTE: These router includes will be uncommented as modules are implemented

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

def _get_available_modules() -> Dict[str, Any]:
    """
    Get list of available and loaded modules.
    
    Returns:
        Dict[str, Any]: Module availability status
    """
    modules = {
        "user_management": {
            "status": "active",
            "version": "1.0.0", 
            "endpoints": [
                "auth",
                "users", 
                "profiles"
            ],
            "description": "User authentication, profiles, and account management"
        },
        "plant_management": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Plant CRUD, identification, and library management"
        },
        "care_management": {
            "status": "planned",
            "version": "1.0.0", 
            "endpoints": [],
            "description": "Care scheduling, tasks, and history tracking"
        },
        "health_monitoring": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Plant health assessment and diagnosis"
        },
        "growth_tracking": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Growth milestones and analysis tracking"
        },
        "community_social": {
            "status": "planned", 
            "version": "1.0.0",
            "endpoints": [],
            "description": "Community posts, feed, and social interactions"
        },
        "ai_smart_features": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "AI chat, recommendations, and automation"
        },
        "weather_environmental": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Weather data and environmental monitoring"
        },
        "analytics_insights": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Analytics dashboards and insights"
        },
        "notification_communication": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Push notifications and communication templates"
        },
        "payment_subscription": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Payment processing and subscription management"
        },
        "content_management": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Content management and multilingual support"
        },
        "admin_management": {
            "status": "planned",
            "version": "1.0.0",
            "endpoints": [],
            "description": "Administrative dashboards and system controls"
        }
    }
    
    return modules


def _get_module_status() -> Dict[str, str]:
    """
    Get current status of all modules.
    
    Returns:
        Dict[str, str]: Module name to status mapping
    """
    try:
        modules = _get_available_modules()
        return {name: info["status"] for name, info in modules.items()}
    except Exception as e:
        logger.error(f"Failed to get module status: {e}")
        return {"error": "status_unavailable"}


def _get_feature_status() -> Dict[str, Any]:
    """
    Get current feature availability status.
    
    Returns:
        Dict[str, Any]: Feature availability information
    """
    try:
        features = {
            "authentication": {
                "available": True,
                "endpoints": ["/auth/login", "/auth/register", "/auth/refresh"],
                "oauth_providers": ["google", "apple"]
            },
            "user_management": {
                "available": True,
                "endpoints": ["/users", "/users/{id}", "/users/me"],
                "features": ["profile_management", "account_settings"]
            },
            "profile_management": {
                "available": True,
                "endpoints": ["/profiles", "/profiles/{id}"],
                "features": ["photo_upload", "bio_management", "privacy_settings"]
            },
            "plant_management": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "care_scheduling": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "health_monitoring": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "growth_tracking": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "community_features": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "ai_features": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "weather_integration": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "analytics": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "notifications": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "payments": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "content_management": {
                "available": False,
                "reason": "module_not_implemented"
            },
            "admin_features": {
                "available": False,
                "reason": "module_not_implemented"
            }
        }
        
        return features
        
    except Exception as e:
        logger.error(f"Failed to get feature status: {e}")
        return {"error": "feature_status_unavailable"}