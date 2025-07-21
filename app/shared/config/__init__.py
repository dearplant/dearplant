# 📄 File: app/shared/config/__init__.py
#
# 🧭 Purpose (Layman Explanation):
# Contains all the settings and configuration files that tell our Plant Care app
# how to connect to databases, external services, and adjust its behavior.
#
# 🧪 Purpose (Technical Summary):
# Configuration package initialization with exports for settings management,
# database configuration, and external service connections.
#
# 🔗 Dependencies:
# - settings.py (application settings)
# - database.py (database configuration)
# - External service configurations
#
# 🔄 Connected Modules / Calls From:
# - app.main (application startup)
# - All modules requiring configuration
# - Infrastructure components

"""
Configuration Management Package

Handles all application configuration including:
- Environment-based settings
- Database connection configuration
- External API credentials and settings
- Caching and Redis configuration
- Supabase integration settings
"""

from .settings import get_settings, Settings

__all__ = [
    "get_settings", 
    "Settings",
]