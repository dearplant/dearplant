# 📄 File: app/modules/user_management/application/dto/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes all the "data transfer objects" for user management, which are like
# standardized packages for sending user and profile information between different parts of our app.
#
# 🧪 Purpose (Technical Summary):
# DTOs package initialization providing data transfer objects for user management
# application layer, standardizing data exchange between handlers and presentation layer.
#
# 🔗 Dependencies:
# - pydantic models for DTO validation and serialization
# - app.modules.user_management.domain.models (domain entities for mapping)
# - JSON serialization support for API responses
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers (handlers return DTOs)
# - app.modules.user_management.presentation.api (API endpoints use DTOs)
# - Application layer initialization (DTO registration for serialization)

"""
User Management Data Transfer Objects (DTOs)

This module contains all DTO definitions for user management operations,
providing standardized data structures for communication between
application layer handlers and presentation layer endpoints.

DTO Categories:
- User DTOs: User account data transfer and responses
- Profile DTOs: Profile information transfer and responses
- Command DTOs: Input validation for commands
- Query DTOs: Response formatting for queries

DTOs serve multiple purposes:
- Data validation and serialization
- API response standardization
- Security field filtering
- Documentation generation
- Type safety for data exchange

All DTOs are immutable and validate data according to
Core Doc specifications and security requirements.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # User DTOs
    from app.modules.user_management.application.dto.user_dto import (
        UserDTO,
        CreateUserDTO,
        UpdateUserDTO,
        UserResponseDTO,
        UserListResponseDTO,
        UserSecurityDTO,
    )
    
    # Profile DTOs
    from app.modules.user_management.application.dto.profile_dto import (
        ProfileDTO,
        CreateProfileDTO,
        UpdateProfileDTO,
        ProfileResponseDTO,
        ProfileListResponseDTO,
        ProfileCompletenessDTO,
        ProfilePrivacyDTO,
    )

__all__ = [
    # User DTOs
    "UserDTO",
    "CreateUserDTO",
    "UpdateUserDTO",
    "UserResponseDTO",
    "UserListResponseDTO",
    "UserSecurityDTO",
    
    # Profile DTOs
    "ProfileDTO",
    "CreateProfileDTO",
    "UpdateProfileDTO",
    "ProfileResponseDTO",
    "ProfileListResponseDTO",
    "ProfileCompletenessDTO",
    "ProfilePrivacyDTO",
]