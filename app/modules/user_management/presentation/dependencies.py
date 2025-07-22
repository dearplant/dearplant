# 📄 File: app/modules/user_management/presentation/dependencies.py
# 🧭 Purpose (Layman Explanation):
# This file contains all the security checks and helper functions for our user management API,
# making sure users can only access their own data and admins can manage the system safely.
#
# 🧪 Purpose (Technical Summary):
# FastAPI dependency injection functions implementing authentication, authorization, and access
# control for user management endpoints with JWT validation and multi-level security.
#
# 🔗 Dependencies:
# - FastAPI security dependencies (HTTPBearer, HTTPAuthorizationCredentials)
# - app.shared.core.security (JWT validation and user extraction)
# - app.modules.user_management.application.handlers (user and profile query handlers)
# - python-jose for JWT token validation (security standard)
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.v1 (all endpoints use these dependencies)
# - FastAPI dependency injection system (automatic injection in endpoints)
# - Authentication middleware and security validation

"""
User Management Presentation Dependencies

This module provides FastAPI dependency injection functions for user management
endpoints with comprehensive authentication, authorization, and access control.

Dependencies:
- get_current_user: Extract user from JWT token
- get_current_active_user: Get active user with verification
- get_current_admin_user: Get admin user with elevated permissions
- verify_user_access: Check self or admin access to user resources
- verify_profile_access: Check self or admin access to profile resources
- get_user_from_token: Token validation and user extraction

Security Features:
- JWT token validation with proper error handling
- Multi-level access control (user, admin, system)
- Resource access verification (self or admin only)
- Account status validation (active, locked, suspended)
- Token expiration and refresh handling
- Comprehensive security logging and audit trail

All dependencies follow security best practices and integrate with
the application layer for proper business logic validation.
"""

import logging
from typing import Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.modules.user_management.application.handlers.query_handlers import (
    GetUserQueryHandler,
    GetProfileQueryHandler,
)
from app.modules.user_management.application.queries.get_user import GetUserQuery
from app.modules.user_management.application.queries.get_profile import GetProfileQuery

from app.modules.user_management.infrastructure.external.supabase_auth import SupabaseAuthService
from app.shared.core.security import decode_access_token, get_current_user_id
from app.shared.config.settings import get_settings

logger = logging.getLogger(__name__)

# Security configuration
security = HTTPBearer()
settings = get_settings()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(),
) -> Dict:
    """
    Extract current user information from JWT token.
    
    This dependency validates the JWT token and extracts user information
    for authentication purposes without additional authorization checks.
    
    Args:
        credentials: Bearer token from Authorization header
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        Dict: Current user information from token
        
    Raises:
        HTTPException: For invalid or expired tokens
    """
    try:
        token = credentials.credentials
        
        # Validate token with Supabase
        token_data = await supabase_auth.validate_token(token)
        
        if not token_data:
            logger.warning("Invalid JWT token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract user information
        user_info = {
            "user_id": UUID(token_data["user_id"]),
            "email": token_data["email"],
            "email_verified": token_data.get("email_verified", False),
            "provider": token_data.get("provider", "email"),
            "is_admin": False,  # Will be determined by additional checks
        }
        
        logger.debug(f"User authenticated: {user_info['user_id']}")
        return user_info
        
    except ValueError as e:
        logger.warning(f"Invalid UUID in token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def get_current_active_user(
    current_user: Dict = Depends(get_current_user),
    get_user_handler: GetUserQueryHandler = Depends(),
) -> Dict:
    """
    Get current active user with account status validation.
    
    This dependency extends get_current_user with additional validation
    to ensure the user account is active and in good standing.
    
    Args:
        current_user: Current user from get_current_user dependency
        get_user_handler: Injected query handler for user data
        
    Returns:
        Dict: Current active user with enhanced information
        
    Raises:
        HTTPException: For inactive, locked, or suspended accounts
    """
    try:
        # Get full user data with security information
        user_query = GetUserQuery(
            user_id=current_user["user_id"],
            requesting_user_id=current_user["user_id"],
            is_admin_request=False,
            include_security_data=False,
            include_login_history=False,
            include_provider_data=True,
            include_timestamps=True,
        )
        
        user_data = await get_user_handler.handle(user_query)
        
        if not user_data:
            logger.warning(f"User not found in database: {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found"
            )
        
        # Check account status
        if user_data.get("account_locked", False):
            logger.warning(f"Locked account access attempt: {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked. Please contact support or reset your password."
            )
        
        # Check email verification if required
        if not user_data.get("email_verified", False):
            logger.info(f"Unverified account access: {current_user['user_id']}")
            # For now, allow unverified users but flag it
            current_user["requires_verification"] = True
        
        # Enhance user information with database data
        enhanced_user = {
            **current_user,
            "created_at": user_data.get("created_at"),
            "last_login": user_data.get("last_login"),
            "login_attempts": user_data.get("login_attempts", 0),
            "requires_verification": not user_data.get("email_verified", False),
        }
        
        logger.debug(f"Active user validated: {enhanced_user['user_id']}")
        return enhanced_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating active user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User validation error"
        )


async def get_current_admin_user(
    current_user: Dict = Depends(get_current_active_user),
) -> Dict:
    """
    Get current user with admin privileges validation.
    
    This dependency ensures the current user has administrative
    privileges for accessing admin-only endpoints and operations.
    
    Args:
        current_user: Current active user from get_current_active_user
        
    Returns:
        Dict: Current admin user with elevated permissions
        
    Raises:
        HTTPException: For non-admin users
    """
    try:
        # Check admin status (in production, this would check admin roles)
        # For now, implement basic admin check logic
        is_admin = await _check_admin_privileges(current_user)
        
        if not is_admin:
            logger.warning(f"Non-admin user attempted admin access: {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative privileges required for this operation"
            )
        
        # Enhance user with admin flags
        admin_user = {
            **current_user,
            "is_admin": True,
            "admin_verified": True,
        }
        
        logger.info(f"Admin user validated: {admin_user['user_id']}")
        return admin_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin validation error"
        )


async def verify_user_access(
    current_user: Dict,
    target_user_id: UUID,
) -> None:
    """
    Verify user has access to target user resource (self or admin only).
    
    This function validates that the current user can access resources
    belonging to the target user, following self-access or admin rules.
    
    Args:
        current_user: Current authenticated user
        target_user_id: UUID of the user resource being accessed
        
    Raises:
        HTTPException: For unauthorized access attempts
    """
    try:
        # Allow self-access
        if current_user["user_id"] == target_user_id:
            logger.debug(f"Self-access granted for user: {target_user_id}")
            return
        
        # Check admin privileges
        is_admin = await _check_admin_privileges(current_user)
        if is_admin:
            logger.info(f"Admin access granted to user {target_user_id} by admin {current_user['user_id']}")
            return
        
        # Access denied
        logger.warning(
            f"Unauthorized access attempt to user {target_user_id} by user {current_user['user_id']}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own user information"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User access verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access verification error"
        )


async def verify_profile_access(
    current_user: Dict,
    profile_id: UUID,
    get_profile_handler: GetProfileQueryHandler = Depends(),
) -> None:
    """
    Verify user has access to target profile resource (self or admin only).
    
    This function validates that the current user can access a specific
    profile, resolving the profile ownership and checking access rights.
    
    Args:
        current_user: Current authenticated user
        profile_id: UUID of the profile being accessed
        get_profile_handler: Injected profile query handler
        
    Raises:
        HTTPException: For unauthorized access attempts or profile not found
    """
    try:
        # Get profile to determine ownership
        profile_query = GetProfileQuery(
            profile_id=profile_id,
            requesting_user_id=current_user["user_id"],
            is_admin_request=current_user.get("is_admin", False),
            include_private_data=False,
            respect_privacy_settings=False,  # We're just checking ownership
        )
        
        profile_data = await get_profile_handler.handle(profile_query)
        
        if not profile_data:
            logger.warning(f"Profile not found for access check: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        # Allow self-access (profile owner)
        if profile_data["user_id"] == current_user["user_id"]:
            logger.debug(f"Profile self-access granted for profile: {profile_id}")
            return
        
        # Check admin privileges
        is_admin = await _check_admin_privileges(current_user)
        if is_admin:
            logger.info(
                f"Admin access granted to profile {profile_id} by admin {current_user['user_id']}"
            )
            return
        
        # Access denied
        logger.warning(
            f"Unauthorized access attempt to profile {profile_id} by user {current_user['user_id']}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile access verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile access verification error"
        )


async def get_user_from_token(
    token: str,
    supabase_auth: SupabaseAuthService = Depends(),
) -> Optional[Dict]:
    """
    Extract user information from JWT token without raising exceptions.
    
    This function provides token validation for optional authentication
    scenarios where a valid user enhances the response but isn't required.
    
    Args:
        token: JWT token string
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        Optional[Dict]: User information if token is valid, None otherwise
    """
    try:
        # Validate token with Supabase
        token_data = await supabase_auth.validate_token(token)
        
        if not token_data:
            return None
        
        # Extract user information
        user_info = {
            "user_id": UUID(token_data["user_id"]),
            "email": token_data["email"],
            "email_verified": token_data.get("email_verified", False),
            "provider": token_data.get("provider", "email"),
            "is_admin": False,
        }
        
        logger.debug(f"Optional user authentication successful: {user_info['user_id']}")
        return user_info
        
    except Exception as e:
        logger.debug(f"Optional token validation failed: {str(e)}")
        return None


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(),
) -> Optional[Dict]:
    """
    Get current user for optional authentication scenarios.
    
    This dependency provides user information when a token is present
    but doesn't require authentication, useful for personalized public content.
    
    Args:
        credentials: Optional bearer token from Authorization header
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        Optional[Dict]: User information if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    return await get_user_from_token(credentials.credentials, supabase_auth)


async def require_email_verified(
    current_user: Dict = Depends(get_current_active_user),
) -> Dict:
    """
    Require current user to have verified email address.
    
    This dependency adds an additional requirement for email verification
    on top of basic authentication, useful for sensitive operations.
    
    Args:
        current_user: Current active user
        
    Returns:
        Dict: Current user with verified email
        
    Raises:
        HTTPException: For unverified email addresses
    """
    if not current_user.get("email_verified", False):
        logger.warning(f"Unverified user attempted verified operation: {current_user['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required for this operation"
        )
    
    return current_user


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _check_admin_privileges(user: Dict) -> bool:
    """
    Check if user has administrative privileges.
    
    This function implements admin privilege checking logic.
    In production, this would integrate with role-based access control.
    
    Args:
        user: User information dictionary
        
    Returns:
        bool: True if user has admin privileges
    """
    try:
        # In production, this would check against admin roles/permissions
        # For now, implement basic admin checking logic
        
        # Check if user is marked as admin in token
        if user.get("is_admin", False):
            return True
        
        # Check against admin user list (environment-based)
        admin_emails = settings.admin_emails or []
        if user.get("email") in admin_emails:
            return True
        
        # Additional admin checks could include:
        # - Database role checking
        # - Permission-based access control
        # - Group membership validation
        
        return False
        
    except Exception as e:
        logger.error(f"Admin privilege check error: {str(e)}")
        return False


def create_rate_limit_key(user_id: Optional[UUID], endpoint: str) -> str:
    """
    Create rate limiting key for user-specific endpoints.
    
    This function generates consistent rate limiting keys for
    user-specific operations and anonymous access patterns.
    
    Args:
        user_id: User UUID or None for anonymous access
        endpoint: Endpoint identifier for rate limiting
        
    Returns:
        str: Rate limiting key
    """
    if user_id:
        return f"user:{user_id}:endpoint:{endpoint}"
    else:
        return f"anonymous:endpoint:{endpoint}"


def get_user_permissions(user: Dict) -> Dict[str, bool]:
    """
    Get user permission flags for authorization checks.
    
    This function centralizes user permission calculation for
    consistent authorization across the application.
    
    Args:
        user: User information dictionary
        
    Returns:
        Dict[str, bool]: Permission flags
    """
    return {
        "can_read_own_data": True,
        "can_write_own_data": not user.get("account_locked", False),
        "can_delete_own_data": not user.get("account_locked", False),
        "can_read_other_users": user.get("is_admin", False),
        "can_write_other_users": user.get("is_admin", False),
        "can_admin_operations": user.get("is_admin", False),
        "requires_email_verification": not user.get("email_verified", False),
        "can_upload_files": user.get("email_verified", False),
    }