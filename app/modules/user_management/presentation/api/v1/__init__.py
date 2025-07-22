# 📄 File: app/modules/user_management/presentation/api/v1/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes version 1 of our user management API endpoints, keeping all the current
# stable web services for user accounts, logins, and profiles organized in one place.
#
# 🧪 Purpose (Technical Summary):
# API version 1 initialization providing FastAPI router organization for current stable
# user management endpoints with proper versioning and backward compatibility support.
#
# 🔗 Dependencies:
# - FastAPI APIRouter for endpoint organization
# - app.modules.user_management.application.handlers (command and query handlers)
# - app.modules.user_management.presentation.api.schemas (Pydantic validation schemas)
# - HTTP authentication and authorization dependencies
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.__init__ (router inclusion)
# - Frontend applications consuming v1 API endpoints
# - API documentation and testing tools

"""
User Management API Version 1

This module contains version 1 of the user management API endpoints,
providing stable RESTful services for user account and profile management.

API Version 1 Endpoints:
- Authentication API (/auth): User authentication and session management
- Users API (/users): User account operations and administration
- Profiles API (/profiles): Profile management and social features

Version 1 Features:
- Stable API contract with backward compatibility
- Comprehensive CRUD operations for all resources
- Proper HTTP method usage (GET, POST, PUT, PATCH, DELETE)
- Request/response validation with Pydantic schemas
- Authentication and authorization middleware integration
- Rate limiting for security-sensitive endpoints
- Comprehensive error handling and status codes

All v1 endpoints are production-ready and follow REST conventions
with full integration to the application layer handlers.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # v1 API Routers
    from app.modules.user_management.presentation.api.v1.auth import auth_router
    from app.modules.user_management.presentation.api.v1.users import users_router  
    from app.modules.user_management.presentation.api.v1.profiles import profiles_router

__all__ = [
    "auth_router",
    "users_router",
    "profiles_router",
]


# API Version Information
API_VERSION = "1.0.0"
API_TITLE = "Plant Care User Management API"
API_DESCRIPTION = """
## Plant Care User Management API v1

This API provides comprehensive user management functionality for the Plant Care application.

### Authentication
- User registration with email verification
- Email/password and OAuth authentication (Google, Apple)
- JWT token-based session management
- Password reset and security features

### User Management  
- User account CRUD operations
- Account security and administration
- User search and filtering
- Admin-only user management features

### Profile Management
- User profile creation and updates
- Privacy settings and visibility controls
- Profile completeness tracking
- Social features for community interaction

### Security Features
- Multi-level access control (public, self, admin)
- Field-level privacy filtering
- Rate limiting on sensitive endpoints
- Comprehensive audit logging
- Account lockout protection

All endpoints follow REST conventions and provide detailed error responses
with proper HTTP status codes.
"""

API_TAGS_METADATA = [
    {
        "name": "Authentication",
        "description": "User authentication and session management endpoints",
        "externalDocs": {
            "description": "Authentication documentation",
            "url": "https://docs.plantcare.app/api/auth",
        },
    },
    {
        "name": "Users", 
        "description": "User account management and administration endpoints",
        "externalDocs": {
            "description": "User management documentation",
            "url": "https://docs.plantcare.app/api/users",
        },
    },
    {
        "name": "Profiles",
        "description": "User profile and social feature management endpoints", 
        "externalDocs": {
            "description": "Profile management documentation",
            "url": "https://docs.plantcare.app/api/profiles",
        },
    },
]


def get_api_version_info() -> dict:
    """
    Get API version information for documentation.
    
    Returns:
        dict: API version metadata
    """
    return {
        "version": API_VERSION,
        "title": API_TITLE,
        "description": API_DESCRIPTION,
        "tags_metadata": API_TAGS_METADATA,
        "contact": {
            "name": "Plant Care API Support",
            "url": "https://support.plantcare.app",
            "email": "api-support@plantcare.app",
        },
        "license": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    }