# 📄 File: app/modules/user_management/domain/services/__init__.py
# 🧭 Purpose (Layman Explanation): 
# Organizes the business logic services that handle complex user operations like registration, authentication, and profile management
# 🧪 Purpose (Technical Summary): 
# Package initialization for domain services implementing core business logic and orchestrating user management operations
# 🔗 Dependencies: 
# Domain services, domain models, repositories, events
# 🔄 Connected Modules / Calls From: 
# Application layer, command handlers, query handlers, API endpoints

"""
User Management Domain Services

This package contains domain services that implement core business logic
for user management operations:

Domain Services:
- UserService: Core user lifecycle management and business operations
- AuthService: Authentication and authorization business logic
- ProfileService: Profile management and social features

Domain services orchestrate complex business operations that:
- Span multiple entities
- Require business rule validation
- Trigger domain events
- Coordinate with external services
- Implement business workflows

Each service follows domain-driven design principles:
- Encapsulates business logic
- Maintains domain model integrity
- Publishes domain events
- Validates business rules
- Coordinates with repositories
"""

# Import domain services
from .user_service import UserService
from .auth_service import AuthService
from .profile_service import ProfileService

# Export all domain services
__all__ = [
    "UserService",
    "AuthService", 
    "ProfileService"
]