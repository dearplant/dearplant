# 📄 File: app/main.py
#
# 🧭 Purpose (Layman Explanation):
# The main control center that starts up our Plant Care app, connects all the different parts together,
# and makes sure everything is ready to handle requests from mobile apps and admin panels.
#
# 🧪 Purpose (Technical Summary):
# FastAPI application factory and entry point with middleware setup, router registration,
# database initialization, and production-ready configuration for the modular monolith architecture.
#
# 🔗 Dependencies:
# - FastAPI framework
# - app.shared.config.settings
# - app.shared.infrastructure.database.connection
# - All module routers (will be added as modules are implemented)
#
# 🔄 Connected Modules / Calls From:
# - uvicorn server startup
# - Docker container entry point
# - Development server commands

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import _get_available_modules

import uvicorn

from app.shared.config.settings import get_settings
from app.shared.core.exceptions import PlantCareException
from app.shared.utils.logging import setup_logging
from app.api.middleware.authentication import AuthenticationMiddleware
from app.api.middleware.rate_limiting import RateLimitingMiddleware
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.middleware.error_handling import ErrorHandlingMiddleware
from app.api.middleware.cors import PlantCareCORSMiddleware
from app.api.middleware.localization import LocalizationMiddleware
from app.api.v1.router import api_v1_router
from app.api.v1.health import health_router
# Import the blueprint (UserRepository) and the real implementation (UserRepositoryImpl)
from app.modules.user_management.domain.repositories.user_repository import UserRepository
from app.modules.user_management.infrastructure.database.user_repository_impl import UserRepositoryImpl

# You will likely need to do this for your other repositories as well. For example:
from app.modules.user_management.domain.repositories.profile_repository import ProfileRepository
# (Assuming you have a similar implementation file for the profile repository)
from app.modules.user_management.infrastructure.database.profile_repository_impl import ProfileRepositoryImpl

from app.modules.user_management.domain.repositories.subscription_repository import SubscriptionRepository
from app.modules.user_management.infrastructure.database.subscription_repository_impl import SubscriptionRepositoryImpl

from datetime import datetime
from fastapi.routing import APIRoute
import inspect
from app.shared.infrastructure.database.session import initialize_sessions

# Monkey patch to log invalid response_model usage
original_route_init = APIRoute.__init__

# def logged_route_init(self, *args, **kwargs):
#     response_model = kwargs.get('response_model', None)
#     endpoint = kwargs.get('endpoint', None)

#     if response_model and not hasattr(response_model, '__fields__'):
#         print("🚨 INVALID response_model detected:", response_model)
#         print("👉 Used by endpoint:", getattr(endpoint, '__name__', str(endpoint)))
#         print("📍 Traceback:")
#         for frame in inspect.stack()[1:5]:
#             print(f"  {frame.filename}:{frame.lineno} - {frame.function}")
#     return original_route_init(self, *args, **kwargs)

# APIRoute.__init__ = logged_route_init

# Get application settings
settings = get_settings()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

 
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application,
    including database connections, cache initialization, and cleanup.
    """
    # Startup events
    logger.info("🌱 Plant Care API starting up...")
    
    try:

        # Initialize database connection
        from app.shared.infrastructure.database.connection import init_database
        await init_database()
        logger.info("✅ Database connection initialized")
        
        from app.shared.infrastructure.database.session import initialize_sessions
        await initialize_sessions()
        logger.info("✅ Session manager initialized")

        # Initialize Redis cache
        from app.shared.infrastructure.cache.redis_client import init_redis
        await init_redis()
        logger.info("✅ Redis cache initialized")
        
        # Initialize external API clients
        from app.shared.infrastructure.external_apis.api_client import init_api_clients
        await init_api_clients()
        logger.info("✅ External API clients initialized")
        
        # Start background tasks monitoring
        logger.info("✅ Plant Care API startup complete")
        
        yield  # Application is running
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    finally:
        # Shutdown events
        logger.info("🔄 Plant Care API shutting down...")
        
        try:
            # Close database connections
            from app.shared.infrastructure.database.connection import close_database
            await close_database()
            logger.info("✅ Database connections closed")
            
            # Close Redis connections
            from app.shared.infrastructure.cache.redis_client import close_redis
            await close_redis()
            logger.info("✅ Redis connections closed")
            
            # Cleanup external API clients
            from app.shared.infrastructure.external_apis.api_client import cleanup_api_clients
            await cleanup_api_clients()
            logger.info("✅ API clients cleanup complete")
            
            logger.info("✅ Plant Care API shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")


def create_application() -> FastAPI:
    """
    Application factory function.
    
    Creates and configures the FastAPI application with all necessary
    middleware, routers, and settings based on the current environment.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    # Create FastAPI application
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
        debug=settings.DEBUG,
    )
    
    # =========================================================================
    # MIDDLEWARE CONFIGURATION
    # =========================================================================
    
    # Error handling middleware (first to catch all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # # Request logging middleware
    if settings.ENVIRONMENT != "test":
        app.add_middleware(RequestLoggingMiddleware)
    
    # Rate limiting middleware
    app.add_middleware(
        RateLimitingMiddleware,
        global_rate_limit=settings.GLOBAL_RATE_LIMIT,
        premium_rate_limit=settings.PREMIUM_RATE_LIMIT,
        admin_rate_limit=settings.ADMIN_RATE_LIMIT,
    )
    
    # CORS Middleware (should be early in the stack)
    app.add_middleware(PlantCareCORSMiddleware)

    # Localization Middleware (after CORS, before authentication)
    app.add_middleware(LocalizationMiddleware)

    # Authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"],
    )
    
    # GZip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
        # This creates a global rule for your entire application.
    # It tells FastAPI: "Whenever any part of the app asks for UserRepository,
    # give it an instance of UserRepositoryImpl."
    app.dependency_overrides[UserRepository] = UserRepositoryImpl
    app.dependency_overrides[ProfileRepository] = ProfileRepositoryImpl # Add this for profiles too
    app.dependency_overrides[SubscriptionRepository] = SubscriptionRepositoryImpl # Add this for profiles too


    # =========================================================================
    # ROUTER REGISTRATION
    # =========================================================================
    
    # Health check routes (no prefix)
    # app.include_router(health_router, tags=["Health"])
    
    # API v1 routes
    app.include_router(
        api_v1_router,
        prefix="/api/v1",
        tags=["API v1"]
    )
    
    # =========================================================================
    # EXCEPTION HANDLERS
    # =========================================================================
    
    @app.exception_handler(PlantCareException)
    async def plant_care_exception_handler(
        request: Request, 
        exc: PlantCareException
    ) -> JSONResponse:
        """Handle custom Plant Care application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": getattr(exc, "timestamp", datetime.utcnow()).isoformat(),
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> JSONResponse:
        """Handle 404 Not Found errors."""
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found",
                    "details": {"path": str(request.url.path)},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
    
    @app.exception_handler(500)
    async def internal_server_error_handler(
        request: Request, 
        exc: Exception
    ) -> JSONResponse:
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": {"error_type": type(exc).__name__} if settings.DEBUG else {},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
    


    @app.exception_handler(404)
    async def v1_not_found_handler(request: Request, exc) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "ENDPOINT_NOT_FOUND",
                    "message": f"API v1 endpoint not found: {request.url.path}",
                    "available_endpoints": list(_get_available_modules().keys()),
                    "suggestion": "Check the API documentation for available endpoints"
                }
            }
        )

    @app.middleware("http")
    async def v1_logging_middleware(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-API-Version"] = "v1"
        response.headers["X-Service"] = "plant-care-api"
        return response    # =========================================================================
    # ROOT ENDPOINTS
    # =========================================================================
    
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": settings.APP_DESCRIPTION,
            "docs_url": "/docs" if settings.DEBUG else None,
            "health_check": "/health",
            "api_base": "/api/v1",
        }
    
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Favicon endpoint to prevent 404 errors."""
        return Response(status_code=204)
    
    return app


# Create the FastAPI application
app = create_application()



def main():
    """
    Main function for running the application in development.
    
    This function is used when running the application directly
    with python -m app.main or as a script entry point.
    """
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD and settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        workers=1 if settings.RELOAD else settings.WORKERS,
    )


if __name__ == "__main__":
    main()