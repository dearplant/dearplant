# 📄 File: app/api/v1/router.py
# 🧭 Purpose (Layman Explanation): 
# This is the main traffic controller for version 1 of our API, organizing all the different
# plant care features into clean sections and making sure everything works together properly.
# 🧪 Purpose (Technical Summary): 
# Central API v1 router that aggregates all module routers, provides health checks,
# implements proper error handling, and manages route organization with consistent tagging.
# 🔗 Dependencies: 
# FastAPI, individual module routers, logging, exception handling
# 🔄 Connected Modules / Calls From: 
# app.main, all v1 module routers, client applications

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create the main v1 router
api_v1_router = APIRouter()

# =========================================================================
# ROUTE PREFIXES CONFIGURATION
# =========================================================================

ROUTE_PREFIXES = {
    "auth": "/auth",
    "users": "/users", 
    "plants": "/plants",
    "library": "/plant-library",
    "care": "/care",
    "health": "/plant-health",
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

# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================

def _get_module_status() -> Dict[str, str]:
    """Get current status of all modules."""
    return {
        "user_management": "active",
        "plant_management": "pending",
        "care_management": "pending", 
        "health_monitoring": "pending",
        "growth_tracking": "pending",
        "community_social": "pending",
        "ai_smart_features": "pending",
        "weather_environmental": "pending",
        "analytics_insights": "pending",
        "notification_communication": "pending",
        "payment_subscription": "pending",
        "content_management": "pending",
        "admin_management": "pending"
    }

def _get_feature_status() -> Dict[str, str]:
    """Get current status of major features."""
    return {
        "authentication": "available",
        "user_profiles": "available", 
        "plant_crud": "development",
        "plant_identification": "development",
        "care_scheduling": "planned",
        "health_monitoring": "planned",
        "growth_tracking": "planned",
        "community_posts": "planned",
        "ai_recommendations": "planned",
        "weather_integration": "planned",
        "analytics_dashboard": "planned",
        "push_notifications": "planned",
        "payment_processing": "planned",
        "content_management": "planned"
    }

def _count_available_endpoints() -> int:
    """Count currently available API endpoints."""
    total_routes = 0
    for route in api_v1_router.routes:
        if hasattr(route, 'methods'):
            total_routes += len(route.methods)
    return total_routes

# =========================================================================
# HEALTH AND STATUS ENDPOINTS  
# =========================================================================

@api_v1_router.get("/",
                  summary="API v1 root information",
                  description="Get API v1 overview and available endpoints",
                  tags=["API Info"])
async def api_v1_root() -> JSONResponse:
    """
    API v1 root endpoint
    
    Provides overview of API v1 including:
    - Available modules and endpoints
    - Current service status
    - API version information
    - Feature availability status
    """
    try:
        root_info = {
            "service": "Plant Care API v1",
            "version": "1.0.0",
            "status": "operational",
            "description": "AI-Powered Plant Care Management System API",
            "modules": _get_module_status(),
            "features": _get_feature_status(), 
            "available_endpoints": _count_available_endpoints(),
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_schema": "/openapi.json"
            },
            "support": {
                "github": "https://github.com/your-org/plant-care-api",
                "documentation": "https://docs.plantcare.com",
                "support_email": "support@plantcare.com"
            }
        }
        
        return JSONResponse(
            status_code=200,
            content=root_info
        )
        
    except Exception as e:
        logger.error(f"Failed to get API v1 root info: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve API information",
                "detail": str(e)
            }
        )


@api_v1_router.get("/status",
                  summary="Plant Care API v1 operational status",
                  description="Get current Plant Care API v1 operational status",
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
# MODULE ROUTER INCLUDES
# =========================================================================

# IMPORTANT: Only uncomment router includes when the module is fully implemented
# and all endpoints have proper Pydantic schemas for response models

try:
    # User Management Module - ACTIVE
    from app.modules.user_management.presentation.api.v1.auth import auth_router
    from app.modules.user_management.presentation.api.v1.users import users_router
    from app.modules.user_management.presentation.api.v1.profiles import profiles_router

    # Add User Management routers
    api_v1_router.include_router(
        auth_router,
        prefix=ROUTE_PREFIXES["auth"],
        tags=["Authentication"]
    )

    api_v1_router.include_router(
        users_router,
        prefix=ROUTE_PREFIXES["users"],
        tags=["Users"]
    )
    
    api_v1_router.include_router(
        profiles_router,
        prefix=ROUTE_PREFIXES["users"],  # Profiles under /users path
        tags=["User Profiles"]
    )
    
    logger.info("✅ User Management routes loaded successfully")
    
except ImportError as e:
    logger.warning(f"❌ User Management routes not available: {e}")
except Exception as e:
    logger.error(f"❌ Failed to load User Management routes: {e}")
 