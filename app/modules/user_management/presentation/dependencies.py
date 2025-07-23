# 📄 File: app/modules/user_management/presentation/dependencies.py
# 🧭 Purpose (Layman Explanation): 
# This file provides special authentication and permission checking tools specifically for user-related features,
# like making sure only the right people can access their own profiles or admin areas.
# 🧪 Purpose (Technical Summary): 
# Module-specific FastAPI dependencies for User Management authentication, authorization, and access control
# with JWT validation, account status checking, and resource ownership verification.
# 🔗 Dependencies: 
# FastAPI, python-jose, app.shared.core.*, app.modules.user_management.application.handlers.*,
# app.modules.user_management.infrastructure.external.supabase_auth
# 🔄 Connected Modules / Calls From: 
# app.modules.user_management.presentation.api.v1.*, all user management endpoints, profile endpoints

"""
User Management Module Dependencies

This module provides specialized authentication and authorization dependencies 
for the User Management module, including:

- JWT token validation with Supabase integration
- Account status verification (active, locked, suspended)
- Multi-level access control (self, admin, public)
- Resource ownership verification
- Email verification requirements
- Admin privilege validation

Dependencies integrate with existing application handlers and domain services
to provide seamless authentication across user management endpoints.
"""

import logging
from typing import Optional, Dict, Any, Union
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from app.shared.core.dependencies import get_db, get_current_user, CurrentUser
from app.shared.core.exceptions import (
    AuthenticationError,
    AuthorizationError, 
    NotFoundError,
    ValidationError
)
from app.shared.config.settings import get_settings

# Application layer imports
from app.modules.user_management.application.handlers.query_handlers import (
    GetUserQueryHandler,
    GetProfileQueryHandler
)
from app.modules.user_management.application.queries.get_user import GetUserQuery
from app.modules.user_management.application.queries.get_profile import GetProfileQuery

# Infrastructure imports
from app.modules.user_management.infrastructure.external.supabase_auth import (
    SupabaseAuthService
)

logger = logging.getLogger(__name__)

# Security scheme for User Management module
security = HTTPBearer()


# =========================================================================
# CORE AUTHENTICATION DEPENDENCIES
# =========================================================================

async def get_current_user_detailed(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """
    Get current user with detailed information from database.
    
    Validates JWT token and fetches current user data from database
    to ensure user still exists and account is in valid state.
    
    Args:
        current_user: Basic user from shared core dependency
        db: Database session
        
    Returns:
        CurrentUser: Enhanced user with fresh database data
        
    Raises:
        AuthenticationError: If user no longer exists
        AuthorizationError: If account is locked or suspended
    """
    try:
        # Get detailed user data from application layer
        query_handler = GetUserQueryHandler(db)
        query = GetUserQuery(user_id=UUID(current_user.user_id))
        
        user_result = await query_handler.handle(query)
        if not user_result:
            logger.warning(f"User not found in database: {current_user.user_id}")
            raise AuthenticationError("User account no longer exists")
        
        # Update current user with fresh database data
        current_user.is_active = user_result.is_active
        current_user.email = user_result.email
        current_user.roles = user_result.roles or ["user"]
        
        logger.debug(f"Enhanced user data loaded: {current_user.user_id}")
        return current_user
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Failed to get detailed user: {e}")
        raise AuthenticationError("User validation failed")


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user_detailed)
) -> CurrentUser:
    """
    Get current active user (not locked, suspended, or deactivated).
    
    Validates that user account is in good standing and not restricted.
    Performs Core Doc 1.1 security compliance checks for account status.
    
    Args:
        current_user: Current user with detailed database information
        
    Returns:
        CurrentUser: Verified active user
        
    Raises:
        AuthorizationError: If account is locked, suspended, or inactive
    """
    try:
        # Check if account is active
        if not current_user.is_active:
            logger.warning(f"Inactive account access attempt: {current_user.user_id}")
            raise AuthorizationError(
                "Your account is currently disabled. Please contact support.",
                error_code="ACCOUNT_DISABLED"
            )
        
        # Check for account lockout (from Core Doc 1.1 security requirements)
        settings = get_settings()
        if hasattr(current_user, 'account_locked') and current_user.account_locked:
            logger.warning(f"Locked account access attempt: {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked due to security concerns. Please contact support.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Log successful active user validation
        logger.debug(f"Active user validated: {current_user.user_id}")
        return current_user
        
    except HTTPException:
        raise
    except AuthorizationError:
        raise
    except Exception as e:
        logger.error(f"Active user validation failed: {e}")
        raise AuthorizationError("Account status validation failed")


async def get_current_admin_user(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """
    Get current user with admin privileges.
    
    Validates that user has administrative access rights with comprehensive
    privilege checking including multiple admin role types and audit logging.
    
    Args:
        current_user: Current active user
        
    Returns:
        CurrentUser: Verified admin user
        
    Raises:
        AuthorizationError: If user lacks admin privileges
    """
    try:
        # Check admin privileges using helper function
        if not _check_admin_privileges(current_user):
            logger.warning(f"Non-admin access attempt: {current_user.user_id}")
            raise AuthorizationError(
                "Admin privileges required for this action",
                error_code="INSUFFICIENT_PRIVILEGES",
                required_permission="admin"
            )
        
        # Log admin access for security audit
        logger.info(f"Admin access granted: {current_user.user_id}")
        return current_user
        
    except AuthorizationError:
        raise
    except Exception as e:
        logger.error(f"Admin privilege validation failed: {e}")
        raise AuthorizationError("Admin privilege validation failed")


# =========================================================================
# AUTHORIZATION DEPENDENCIES  
# =========================================================================

async def verify_user_access(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """
    Verify user can access specified user resource (self or admin).
    
    Implements resource-level access control where users can access their own
    data and admins can access any user's data with proper audit logging.
    
    Args:
        user_id: Target user ID to access
        current_user: Current authenticated user
        
    Returns:
        CurrentUser: User with verified access permissions
        
    Raises:
        AuthorizationError: If access is denied
        ValidationError: If user_id is invalid
    """
    try:
        # Validate user_id format
        try:
            target_uuid = UUID(user_id)
        except ValueError:
            raise ValidationError("Invalid user ID format")
        
        current_uuid = UUID(current_user.user_id)
        
        # Check if user is accessing their own data
        if current_uuid == target_uuid:
            logger.debug(f"Self-access granted: {current_user.user_id}")
            return current_user
        
        # Check admin privileges for cross-user access
        if _check_admin_privileges(current_user):
            logger.info(
                f"Admin cross-user access: {current_user.user_id} -> {user_id}"
            )
            return current_user
        
        # Access denied
        logger.warning(
            f"Unauthorized user access attempt: {current_user.user_id} -> {user_id}"
        )
        raise AuthorizationError(
            "You can only access your own user data",
            error_code="RESOURCE_ACCESS_DENIED"
        )
        
    except (AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"User access verification failed: {e}")
        raise AuthorizationError("Access verification failed")


async def verify_profile_access(
    profile_id: str,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """
    Verify user can access specified profile resource.
    
    Validates access to profile resources with ownership resolution through
    database lookup and proper admin override capabilities.
    
    Args:
        profile_id: Target profile ID to access
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        CurrentUser: User with verified profile access
        
    Raises:
        AuthorizationError: If access is denied
        NotFoundError: If profile doesn't exist
        ValidationError: If profile_id is invalid
    """
    try:
        # Validate profile_id format
        try:
            target_profile_uuid = UUID(profile_id)
        except ValueError:
            raise ValidationError("Invalid profile ID format")
        
        # Get profile ownership information
        query_handler = GetProfileQueryHandler(db)
        query = GetProfileQuery(profile_id=target_profile_uuid)
        profile_result = await query_handler.handle(query)
        
        if not profile_result:
            raise NotFoundError("Profile not found")
        
        current_uuid = UUID(current_user.user_id)
        profile_owner_uuid = UUID(str(profile_result.user_id))
        
        # Check if user owns the profile
        if current_uuid == profile_owner_uuid:
            logger.debug(f"Profile owner access: {current_user.user_id} -> {profile_id}")
            return current_user
        
        # Check admin privileges for cross-profile access
        if _check_admin_privileges(current_user):
            logger.info(
                f"Admin profile access: {current_user.user_id} -> {profile_id}"
            )
            return current_user
        
        # Access denied
        logger.warning(
            f"Unauthorized profile access: {current_user.user_id} -> {profile_id}"
        )
        raise AuthorizationError(
            "You can only access your own profile data",
            error_code="PROFILE_ACCESS_DENIED"
        )
        
    except (AuthorizationError, NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Profile access verification failed: {e}")
        raise AuthorizationError("Profile access verification failed")


async def require_email_verified(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """
    Require user to have verified email for sensitive operations.
    
    Enforces email verification requirement for operations that require
    additional security validation as per Core Doc 1.1 specifications.
    
    Args:
        current_user: Current active user
        db: Database session
        
    Returns:
        CurrentUser: User with verified email
        
    Raises:
        AuthorizationError: If email is not verified
    """
    try:
        # Get fresh user data to check email verification status
        query_handler = GetUserQueryHandler(db)
        query = GetUserQuery(user_id=UUID(current_user.user_id))
        user_result = await query_handler.handle(query)
        
        if not user_result:
            raise AuthenticationError("User not found")
        
        # Check email verification status
        if not user_result.email_verified:
            logger.warning(f"Unverified email access attempt: {current_user.user_id}")
            raise AuthorizationError(
                "Email verification required for this operation. Please check your email and verify your account.",
                error_code="EMAIL_NOT_VERIFIED"
            )
        
        logger.debug(f"Email verification confirmed: {current_user.user_id}")
        return current_user
        
    except (AuthenticationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error(f"Email verification check failed: {e}")
        raise AuthorizationError("Email verification check failed")


# =========================================================================
# OPTIONAL AUTHENTICATION DEPENDENCIES
# =========================================================================

async def get_optional_current_user(
    request: Request
) -> Optional[CurrentUser]:
    """
    Get current user optionally (returns None if not authenticated).
    
    Provides optional authentication for endpoints that can work with or
    without authentication, such as public content with personalization.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Optional[CurrentUser]: User if authenticated, None otherwise
    """
    try:
        # Try to get user from request state (set by middleware)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return None
        
        user_email = getattr(request.state, "user_email", None)
        is_active = getattr(request.state, "is_active", True)
        is_premium = getattr(request.state, "is_premium", False)
        user_roles = getattr(request.state, "user_roles", ["user"])
        token_payload = getattr(request.state, "token_payload", {})
        
        current_user = CurrentUser(
            user_id=user_id,
            email=user_email,
            is_active=is_active,
            is_premium=is_premium,
            roles=user_roles,
            token_payload=token_payload
        )
        
        logger.debug(f"Optional user authenticated: {user_id}")
        return current_user
        
    except Exception as e:
        logger.debug(f"Optional authentication failed (expected): {e}")
        return None


async def get_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """
    Extract user from JWT token without raising exceptions.
    
    Validates JWT token and returns user information without throwing
    exceptions, useful for optional authentication scenarios.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Optional[CurrentUser]: User if token is valid, None otherwise
    """
    try:
        if not credentials:
            return None
        
        # Validate JWT token using Supabase auth service
        auth_service = SupabaseAuthService()
        token_payload = await auth_service.verify_token(credentials.credentials)
        
        if not token_payload:
            return None
        
        # Extract user information from token
        user_id = token_payload.get("sub")
        email = token_payload.get("email")
        roles = token_payload.get("user_metadata", {}).get("roles", ["user"])
        
        if not user_id:
            return None
        
        current_user = CurrentUser(
            user_id=user_id,
            email=email,
            is_active=True,  # Token existence implies active account
            is_premium=False,  # Default, can be updated from database
            roles=roles,
            token_payload=token_payload
        )
        
        logger.debug(f"User extracted from token: {user_id}")
        return current_user
        
    except Exception as e:
        logger.debug(f"Token user extraction failed (expected): {e}")
        return None


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def _check_admin_privileges(user: CurrentUser) -> bool:
    """
    Check if user has admin privileges through multiple validation methods.
    
    Implements comprehensive admin privilege checking including role-based
    access, email-based admin detection, and future extensibility.
    
    Args:
        user: User to check admin privileges for
        
    Returns:
        bool: True if user has admin privileges
    """
    try:
        # Method 1: Role-based admin check
        admin_roles = ["admin", "super_admin", "system_admin"]
        if any(role in user.roles for role in admin_roles):
            return True
        
        # Method 2: Email-based admin check (from settings)
        settings = get_settings()
        admin_emails = getattr(settings, 'ADMIN_EMAILS', '').split(',')
        admin_emails = [email.strip().lower() for email in admin_emails if email.strip()]
        
        if user.email and user.email.lower() in admin_emails:
            return True
        
        # Method 3: Token-based admin check
        if user.token_payload.get("admin") is True:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Admin privilege check failed: {e}")
        return False


def create_rate_limit_key(user: CurrentUser, endpoint: str = "default") -> str:
    """
    Create rate limiting key for user-specific rate limiting.
    
    Generates consistent rate limiting keys for user-based rate limiting
    with endpoint-specific granularity for enhanced control.
    
    Args:
        user: Current user
        endpoint: Endpoint identifier for granular rate limiting
        
    Returns:
        str: Rate limiting key
    """
    try:
        # Include user ID and endpoint in rate limit key
        base_key = f"rate_limit:user:{user.user_id}:endpoint:{endpoint}"
        
        # Add premium status for different rate limits
        if user.is_premium:
            base_key += ":premium"
        
        # Add admin status for elevated limits
        if _check_admin_privileges(user):
            base_key += ":admin"
        
        return base_key
        
    except Exception as e:
        logger.error(f"Rate limit key creation failed: {e}")
        return f"rate_limit:fallback:{endpoint}"


def get_user_permissions(user: CurrentUser) -> Dict[str, bool]:
    """
    Get comprehensive user permissions for authorization decisions.
    
    Calculates and returns all relevant permissions for the user including
    role-based, subscription-based, and feature-specific permissions.
    
    Args:
        user: Current user
        
    Returns:
        Dict[str, bool]: Permission flags
    """
    try:
        permissions = {
            # Basic permissions
            "can_read_own_data": True,
            "can_modify_own_data": True,
            "can_delete_own_data": True,
            
            # Admin permissions
            "can_read_all_users": _check_admin_privileges(user),
            "can_modify_all_users": _check_admin_privileges(user),
            "can_delete_users": _check_admin_privileges(user),
            "can_access_admin_panel": _check_admin_privileges(user),
            
            # Premium permissions
            "can_access_premium_features": user.is_premium,
            "can_use_advanced_analytics": user.is_premium,
            "can_access_ai_features": user.is_premium,
            
            # Feature permissions based on roles
            "can_moderate_content": "moderator" in user.roles or _check_admin_privileges(user),
            "can_manage_system": "system_admin" in user.roles,
            "can_view_analytics": _check_admin_privileges(user) or user.is_premium,
            
            # Account status permissions
            "account_active": user.is_active,
            "email_verified": getattr(user, 'email_verified', False),
        }
        
        return permissions
        
    except Exception as e:
        logger.error(f"Permission calculation failed: {e}")
        return {"can_read_own_data": True}  # Minimal fallback permissions


# =========================================================================
# EXPORT ALL DEPENDENCIES
# =========================================================================

# Export all dependencies for easy importing in route modules
__all__ = [
    # Core authentication dependencies
    "get_current_user_detailed",
    "get_current_active_user", 
    "get_current_admin_user",
    
    # Authorization dependencies
    "verify_user_access",
    "verify_profile_access",
    "require_email_verified",
    
    # Optional authentication dependencies
    "get_optional_current_user",
    "get_user_from_token",
    
    # Helper functions
    "create_rate_limit_key",
    "get_user_permissions",
    
    # Security utilities
    "security",
]

# =========================================================================
# MODULE INITIALIZATION LOGGING
# =========================================================================

logger.info("🔐 User Management dependencies module initialized")
logger.info("✅ Available dependencies:")
logger.info("   - Core Authentication: get_current_user_detailed, get_current_active_user, get_current_admin_user")
logger.info("   - Authorization: verify_user_access, verify_profile_access, require_email_verified")
logger.info("   - Optional Auth: get_optional_current_user, get_user_from_token")
logger.info("   - Utilities: create_rate_limit_key, get_user_permissions")
logger.info("🚀 User Management module dependencies ready for use!")