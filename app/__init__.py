    # 📄 File: app/__init__.py
#
# 🧭 Purpose (Layman Explanation):
# The main entry point that tells Python this 'app' folder contains our Plant Care application code
# and sets up the basic version and package information.
#
# 🧪 Purpose (Technical Summary):
# Application package initialization with version info, basic configuration,
# and package-level imports for the Plant Care FastAPI application.
#
# 🔗 Dependencies:
# - Python packaging system
# - Version management
#
# 🔄 Connected Modules / Calls From:
# - main.py (application entry point)
# - Package imports throughout the application
# - Setup and deployment scripts

"""
Plant Care Application - AI-Powered Plant Management System

A comprehensive backend API for managing plant collections, care schedules,
health monitoring, and community features with intelligent recommendations.
"""

__version__ = "1.0.0"
__title__ = "Plant Care Backend API"
__description__ = "AI-Powered Plant Care Management System"
__author__ = "Plant Care Team"
__author_email__ = "dev@plantcare.app"
__license__ = "MIT"
__url__ = "https://plantcare.app"

# Application metadata
__all__ = [
    "__version__",
    "__title__", 
    "__description__",
    "__author__",
    "__author_email__",
    "__license__",
    "__url__",
]