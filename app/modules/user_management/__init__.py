# 📄 File: app/modules/user_management/__init__.py
# 🧭 Purpose (Layman Explanation): 
# Organizes the user management system that handles user accounts, profiles, login/logout, and subscription features for plant care users
# 🧪 Purpose (Technical Summary): 
# Package initialization for user management module implementing domain-driven design with CQRS pattern for user authentication, profiles, and subscription management
# 🔗 Dependencies: 
# FastAPI, SQLAlchemy, app.shared.core, pydantic, passlib
# 🔄 Connected Modules / Calls From: 
# app.main.py, authentication middleware, all user-related API endpoints

"""
User Management Module

This module handles all user-related functionality including:
- User registration and authentication (1.1 Authentication Submodule)
- User profile management (1.2 Profile Management Submodule)  
- Subscription and billing management (1.3 Subscription Management Submodule)
- User preferences and settings
- Password management and security

Architecture follows Domain-Driven Design:
- Domain: Core business logic and entities
- Application: Use cases, commands, queries, and handlers
- Infrastructure: Data persistence and external integrations
- Presentation: API endpoints and request/response schemas

Key Features:
- JWT-based authentication with OAuth support
- Role-based access control (RBAC)
- User profile management with photo upload
- Subscription tiers (free/premium_monthly/premium_yearly)
- Email verification and password reset
- Multi-language user preferences
- Account security features
"""

from typing import Dict, Any

# Module metadata
__version__ = "1.0.0"
__module_name__ = "user_management"
__description__ = "User Management and Authentication Module"

# Module configuration following core doc specifications
USER_MANAGEMENT_CONFIG = {
    "version": __version__,
    "module_name": __module_name__,
    "description": __description__,
    "submodules": {
        "authentication": {
            "enabled": True,
            "features": ["registration", "login", "oauth", "password_reset", "account_lockout"],
            "providers": ["email", "google", "apple"],
            "max_login_attempts": 5
        },
        "profile_management": {
            "enabled": True,
            "features": ["profile_creation", "photo_upload", "location_weather", "privacy_settings"],
            "max_bio_length": 500,
            "supported_themes": ["light", "dark", "auto"]
        },
        "subscription_management": {
            "enabled": True,
            "plans": ["free", "premium_monthly", "premium_yearly"],
            "trial_duration_days": 7,
            "payment_providers": ["razorpay", "stripe"],
            "auto_renew": True
        }
    },
    "security": {
        "password_hashing": "bcrypt",
        "token_type": "JWT",
        "session_management": True,
        "account_lockout": True,
        "email_verification": True
    }
}

def get_module_config() -> Dict[str, Any]:
    """
    Get user management module configuration.
    
    Returns:
        Module configuration dictionary following core doc specifications
    """
    return USER_MANAGEMENT_CONFIG.copy()

def get_module_info() -> Dict[str, str]:
    """
    Get basic module information.
    
    Returns:
        Module information dictionary
    """
    return {
        "name": __module_name__,
        "version": __version__,
        "description": __description__
    }

# Export key configuration for other modules
__all__ = [
    "__version__",
    "__module_name__", 
    "__description__",
    "USER_MANAGEMENT_CONFIG",
    "get_module_config",
    "get_module_info"
]