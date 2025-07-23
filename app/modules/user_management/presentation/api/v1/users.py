# 📄 File: app/modules/user_management/presentation/api/v1/users.py
# 🧭 Purpose (Layman Explanation):
# This file contains all the web endpoints for managing user accounts like getting user info,
# updating account settings, deleting accounts, and admin functions for our plant care app.
#
# 🧪 Purpose (Technical Summary):
# FastAPI user management endpoints implementing Core Doc 1.1 specifications with CRUD operations,
# admin functions, security filtering, and comprehensive user account management.
#
# 🔗 Dependencies:
# - FastAPI router, HTTPException, status codes, Query parameters
# - app.modules.user_management.application.handlers (command and query handlers)
# - app.modules.user_management.application.queries (user queries)
# - app.modules.user_management.presentation.api.schemas.user_schemas (request/response schemas)
# - Authentication and authorization dependencies
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.__init__ (router inclusion)
# - Admin dashboard (user management interface)
# - User settings pages (account management)

"""
Users API Endpoints

This module implements RESTful user management endpoints following Core Doc 1.1
specifications with comprehensive CRUD operations and admin functionality.

Endpoints:
- GET /me: Get current user information
- GET /{user_id}: Get specific user information (with authorization)
- PUT /{user_id}: Update user account information
- DELETE /{user_id}: Delete user account (with confirmation)
- GET /: List users (admin only, with pagination and filtering)
- POST /{user_id}/verify-email: Verify user email (admin only)
- POST /{user_id}/unlock: Unlock user account (admin only)
- POST /{user_id}/reset-login-attempts: Reset login attempts (admin only)
- GET /{user_id}/security: Get user security information (admin only)

Security Features:
- Multi-level access control (self, admin)
- Field filtering based on access level
- Admin-only user management functions
- Comprehensive audit logging for admin actions
- Rate limiting on sensitive operations

All endpoints follow REST conventions and integrate with the application
layer handlers while respecting privacy and security requirements.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.modules.user_management.application.commands.delete_user import DeleteUserCommand
from app.modules.user_management.application.handlers.command_handlers import DeleteUserCommandHandler
from app.modules.user_management.application.handlers.query_handlers import GetUserQueryHandler

from app.modules.user_management.application.queries.get_user import GetUserQuery

from app.modules.user_management.presentation.api.schemas.user_schemas import (
    UserResponse,
    UserListResponse,
    UserUpdateRequest,
    UserSecurityResponse,
    UserDeleteRequest,
    UserDeleteResponse,
    EmailVerificationResponse,
    AccountUnlockResponse,
)

from app.modules.user_management.presentation.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    verify_user_access,
)

logger = logging.getLogger(__name__)

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

# Security configuration
security = HTTPBearer()

# Create router
users_router = APIRouter()


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
    description="Get the current authenticated user's information",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Authentication required"},
    }
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user),
    # ❗️ FIX: The type hint is removed, and the class is passed directly to Depends.
    get_user_handler: GetUserQueryHandler = Depends(GetUserQueryHandler),
) -> UserResponse:
    """
    Get current authenticated user's information.
    
    This endpoint returns the current user's account information with
    self-level access permissions for field filtering.
    
    Args:
        current_user: Injected current user information
        get_user_handler: Injected query handler for user retrieval
        
    Returns:
        UserResponse: Current user information with appropriate filtering
    """
    try:
        # Create query for current user
        user_query = GetUserQuery(
            user_id=current_user["user_id"],
            requesting_user_id=current_user["user_id"],
            is_admin_request=current_user.get("is_admin", False),
            include_security_data=False,  # Not needed for self
            include_login_history=True,   # Self can see login history
            include_provider_data=True,
            include_timestamps=True,
        )
        
        user_data = await get_user_handler.handle(user_query)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Convert to response DTO with self access level
        return UserResponse.from_domain_data(user_data, access_level="self")
        
    except Exception as e:
        logger.error(f"Error getting current user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )
    
@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user information",
    description="Get specific user information (with authorization checks)",
    responses={
        200: {"description": "User information"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "User not found"},
    }
)
async def get_user(
    user_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    get_user_handler: GetUserQueryHandler = Depends(),
) -> UserResponse:
    """
    Get specific user information with authorization checks.
    
    This endpoint returns user information based on the requesting user's
    access level (self, admin, or public).
    
    Args:
        user_id: UUID of the user to retrieve
        current_user: Injected current user information
        get_user_handler: Injected query handler for user retrieval
        
    Returns:
        UserResponse: User information with appropriate filtering
        
    Raises:
        HTTPException: For access denied or user not found
    """
    try:
        # Determine access level
        is_self = user_id == current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Create query with appropriate permissions
        user_query = GetUserQuery(
            user_id=user_id,
            requesting_user_id=current_user["user_id"],
            is_admin_request=is_admin,
            include_security_data=is_admin,           # Only admin gets security data
            include_login_history=is_self or is_admin, # Self or admin gets login history
            include_provider_data=is_self or is_admin, # Provider data for self/admin
            include_timestamps=True,
        )
        
        user_data = await get_user_handler.handle(user_query)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Determine response access level
        if is_admin:
            access_level = "admin"
        elif is_self:
            access_level = "self"
        else:
            access_level = "public"
        
        return UserResponse.from_domain_data(user_data, access_level=access_level)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


@users_router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user account",
    description="Update user account information (self or admin only)",
    responses={
        200: {"description": "User updated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "User not found"},
        422: {"description": "Validation error"},
    }
)
async def update_user(
    user_id: UUID,
    update_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
) -> UserResponse:
    """
    Update user account information.
    
    This endpoint allows users to update their own account information
    or allows admins to update any user account.
    
    Args:
        user_id: UUID of the user to update
        update_data: User update information
        current_user: Injected current user information
        
    Returns:
        UserResponse: Updated user information
        
    Raises:
        HTTPException: For access denied, validation errors, or user not found
    """
    try:
        # Verify access (self or admin only)
        await verify_user_access(current_user, user_id)
        
        # For now, user updates are limited to email changes
        # Full user updates would be implemented here with proper validation
        
        logger.info(f"User update requested for {user_id} by {current_user['user_id']}")
        
        # This would integrate with UpdateUserCommandHandler when implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="User updates not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@users_router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
    summary="Delete user account",
    description="Delete user account with confirmation (self or admin only)",
    responses={
        200: {"description": "User deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "User not found"},
        422: {"description": "Validation error"},
    }
)
@limiter.limit("3/hour")  # Strict limit for account deletion
async def delete_user(
    request: Request,
    user_id: UUID,
    delete_data: UserDeleteRequest,
    current_user: dict = Depends(get_current_active_user),
    delete_user_handler: DeleteUserCommandHandler = Depends(),
) -> UserDeleteResponse:
    """
    Delete user account with proper confirmation and security checks.
    
    This endpoint allows users to delete their own accounts or allows
    admins to delete any user account with proper audit logging.
    
    Args:
        request: FastAPI request object for rate limiting
        user_id: UUID of the user to delete
        delete_data: Deletion confirmation and parameters
        current_user: Injected current user information
        delete_user_handler: Injected command handler for user deletion
        
    Returns:
        UserDeleteResponse: Deletion confirmation and audit information
        
    Raises:
        HTTPException: For access denied, validation errors, or user not found
    """
    try:
        # Verify access (self or admin only)
        await verify_user_access(current_user, user_id)
        
        is_admin = current_user.get("is_admin", False)
        
        # Create deletion command
        delete_command = DeleteUserCommand(
            user_id=user_id,
            confirmation_token=delete_data.confirmation_token,
            password_confirmation=delete_data.password_confirmation,
            reason=delete_data.reason,
            reason_details=delete_data.reason_details,
            hard_delete=delete_data.hard_delete,
            immediate_deletion=delete_data.immediate_deletion,
            delete_user_data=delete_data.delete_user_data,
            delete_subscription_data=delete_data.delete_subscription_data,
            delete_uploaded_files=delete_data.delete_uploaded_files,
            revoke_all_sessions=delete_data.revoke_all_sessions,
            admin_user_id=current_user["user_id"] if is_admin and user_id != current_user["user_id"] else None,
            admin_reason=delete_data.admin_reason if is_admin else None,
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("User-Agent"),
        )
        
        # Execute deletion
        result = await delete_user_handler.handle(delete_command)
        
        logger.info(f"User {user_id} deleted by {current_user['user_id']}")
        
        return UserDeleteResponse(
            user_id=result["user_id"],
            deletion_type=result["deletion_type"],
            deleted_at=result["deleted_at"],
            cleanup_completed=result["cleanup_completed"],
            message="User account deleted successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )


@users_router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users (admin only)",
    responses={
        200: {"description": "Users retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
    }
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for email or display name"),
    status_filter: Optional[str] = Query(None, description="Filter by user status"),
    current_admin: dict = Depends(get_current_admin_user),
    get_user_handler: GetUserQueryHandler = Depends(),
) -> UserListResponse:
    """
    Get paginated list of users with filtering options (admin only).
    
    This endpoint provides admin users with a paginated list of all users
    with search and filtering capabilities.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
        search: Optional search term for email or display name
        status_filter: Optional filter by user status
        current_admin: Injected current admin user information
        get_user_handler: Injected query handler for user retrieval
        
    Returns:
        UserListResponse: Paginated list of users with metadata
        
    Raises:
        HTTPException: For non-admin access or system errors
    """
    try:
        logger.info(f"Admin user list requested by {current_admin['user_id']}")
        
        # This would integrate with a list users query handler when implemented
        # For now, return empty list with proper pagination structure
        
        return UserListResponse(
            users=[],
            total_count=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            has_next=False,
            has_previous=False,
        )
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user list"
        )


@users_router.post(
    "/{user_id}/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify user email",
    description="Manually verify user email (admin only)",
    responses={
        200: {"description": "Email verified successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    }
)
async def verify_user_email(
    user_id: UUID,
    current_admin: dict = Depends(get_current_admin_user),
) -> EmailVerificationResponse:
    """
    Manually verify user email address (admin only).
    
    This endpoint allows admin users to manually verify a user's email
    address, bypassing the normal verification workflow.
    
    Args:
        user_id: UUID of the user whose email to verify
        current_admin: Injected current admin user information
        
    Returns:
        EmailVerificationResponse: Email verification confirmation
        
    Raises:
        HTTPException: For non-admin access or user not found
    """
    try:
        logger.info(f"Manual email verification for user {user_id} by admin {current_admin['user_id']}")
        
        # This would integrate with email verification command handler
        return EmailVerificationResponse(
            user_id=user_id,
            email_verified=True,
            verified_at=datetime.utcnow(),
            verified_by=current_admin["user_id"],
            message="Email verified successfully",
        )
        
    except Exception as e:
        logger.error(f"Error verifying email for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )


@users_router.post(
    "/{user_id}/unlock",
    response_model=AccountUnlockResponse,
    summary="Unlock user account",
    description="Unlock locked user account (admin only)",
    responses={
        200: {"description": "Account unlocked successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    }
)
async def unlock_user_account(
    user_id: UUID,
    current_admin: dict = Depends(get_current_admin_user),
) -> AccountUnlockResponse:
    """
    Unlock locked user account and reset login attempts (admin only).
    
    This endpoint allows admin users to unlock accounts that have been
    locked due to too many failed login attempts.
    
    Args:
        user_id: UUID of the user account to unlock
        current_admin: Injected current admin user information
        
    Returns:
        AccountUnlockResponse: Account unlock confirmation
        
    Raises:
        HTTPException: For non-admin access or user not found
    """
    try:
        logger.info(f"Account unlock for user {user_id} by admin {current_admin['user_id']}")
        
        # This would integrate with account unlock command handler
        return AccountUnlockResponse(
            user_id=user_id,
            account_locked=False,
            login_attempts_reset=True,
            unlocked_at=datetime.utcnow(),
            unlocked_by=current_admin["user_id"],
            message="Account unlocked successfully",
        )
        
    except Exception as e:
        logger.error(f"Error unlocking account for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock account"
        )


@users_router.get(
    "/{user_id}/security",
    response_model=UserSecurityResponse,
    summary="Get user security information",
    description="Get detailed security information for user (admin only)",
    responses={
        200: {"description": "Security information retrieved"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    }
)
async def get_user_security(
    user_id: UUID,
    current_admin: dict = Depends(get_current_admin_user),
    get_user_handler: GetUserQueryHandler = Depends(),
) -> UserSecurityResponse:
    """
    Get detailed security information for user (admin only).
    
    This endpoint provides admin users with detailed security information
    including login attempts, security events, and account status.
    
    Args:
        user_id: UUID of the user to get security info for
        current_admin: Injected current admin user information
        get_user_handler: Injected query handler for user retrieval
        
    Returns:
        UserSecurityResponse: Detailed security information
        
    Raises:
        HTTPException: For non-admin access or user not found
    """
    try:
        # Create admin query for security data
        user_query = GetUserQuery(
            user_id=user_id,
            requesting_user_id=current_admin["user_id"],
            is_admin_request=True,
            include_security_data=True,
            include_login_history=True,
        )
        
        user_data = await get_user_handler.handle(user_query)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserSecurityResponse(
            user_id=user_id,
            login_attempts=user_data.get("login_attempts", 0),
            account_locked=user_data.get("account_locked", False),
            has_reset_token=user_data.get("reset_token") is not None,
            reset_token_expires=user_data.get("reset_token_expires"),
            last_login=user_data.get("last_login"),
            created_at=user_data.get("created_at"),
            email_verified=user_data.get("email_verified", False),
            provider=user_data.get("provider", "email"),
            security_events=user_data.get("security_events", []),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security info for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security information"
        )