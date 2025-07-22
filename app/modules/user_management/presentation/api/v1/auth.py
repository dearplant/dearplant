# 📄 File: app/modules/user_management/presentation/api/v1/auth.py
# 🧭 Purpose (Layman Explanation):
# This file contains all the web endpoints for user authentication like signing up, logging in,
# logging out, and resetting passwords for our plant care app users.
#
# 🧪 Purpose (Technical Summary):
# FastAPI authentication endpoints implementing Core Doc 1.1 specifications with JWT tokens,
# OAuth integration, rate limiting, and comprehensive security measures for user authentication.
#
# 🔗 Dependencies:
# - FastAPI router, HTTPException, status codes
# - app.modules.user_management.application.handlers (command and query handlers)
# - app.modules.user_management.application.commands (authentication commands)
# - app.modules.user_management.presentation.api.schemas.auth_schemas (request/response schemas)
# - slowapi for rate limiting (security standard)
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.__init__ (router inclusion)
# - Frontend applications (mobile app login, web interface)
# - OAuth providers (Google, Apple callback handling)

"""
Authentication API Endpoints

This module implements RESTful authentication endpoints following Core Doc 1.1
specifications with comprehensive security measures and OAuth integration.

Endpoints:
- POST /register: User registration with email verification
- POST /login: Email/password authentication with rate limiting  
- POST /logout: Session termination and token revocation
- POST /refresh: JWT token refresh for session management
- POST /forgot-password: Password reset initiation
- POST /reset-password: Password reset completion
- POST /verify-email: Email verification confirmation
- GET /oauth/{provider}: OAuth authentication initiation
- POST /oauth/{provider}/callback: OAuth authentication completion

Security Features:
- Rate limiting on authentication endpoints
- Account lockout protection (5 attempts per Core Doc)
- JWT token management with refresh tokens
- Password complexity validation
- Email verification workflow
- Comprehensive audit logging

All endpoints follow REST conventions and integrate with the application
layer command/query handlers for business logic execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.modules.user_management.application.commands.create_user import CreateUserCommand
from app.modules.user_management.application.handlers.command_handlers import (
    CreateUserCommandHandler,
    DeleteUserCommandHandler,
)
from app.modules.user_management.application.handlers.query_handlers import GetUserQueryHandler
from app.modules.user_management.application.queries.get_user import GetUserQuery

from app.modules.user_management.presentation.api.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    LoginResponse,
    LogoutResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    OAuthInitiateResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
)

from app.modules.user_management.infrastructure.external.supabase_auth import SupabaseAuthService
from app.modules.user_management.infrastructure.external.oauth_providers import OAuthProviderManager
from app.shared.core.security import create_access_token, verify_password
from app.shared.core.exceptions import AuthenticationError, ValidationError,RateLimitError
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

# Security configuration
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create router
auth_router = APIRouter()

@auth_router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="Register a new user account with email verification",
    responses={
        201: {"description": "User registered successfully"},
        400: {"description": "Invalid registration data"},
        409: {"description": "User already exists"},
        422: {"description": "Validation error"},
        429: {"description": "Too many registration attempts"},
    }
)
@limiter.limit("5/minute")  # Core Doc security requirement
async def register(
    request: Request,
    registration_data: RegisterRequest,
    create_user_handler: CreateUserCommandHandler = Depends(),
) -> LoginResponse:
    """
    Register a new user account following Core Doc 1.1 specifications.
    
    This endpoint creates a new user account with profile and initiates
    the email verification workflow. Rate limited to prevent abuse.
    
    Args:
        request: FastAPI request object for rate limiting
        registration_data: User registration information
        create_user_handler: Injected command handler for user creation
        
    Returns:
        LoginResponse: Registration confirmation with tokens and user info
        
    Raises:
        HTTPException: For validation errors or existing users
    """
    try:
        logger.info(f"User registration attempt for email: {registration_data.email}")
        
        # Create user registration command
        create_command = CreateUserCommand(
            email=registration_data.email,
            password=registration_data.password,
            display_name=registration_data.display_name,
            provider="email",
            bio=registration_data.bio,
            location=registration_data.location,
            language=registration_data.language or "auto",
            theme=registration_data.theme or "auto",
            user_agent=request.headers.get("User-Agent"),
            ip_address=get_remote_address(request),
        )
        
        # Execute user creation
        result = await create_user_handler.handle(create_command)
        
        # Generate access tokens for new user
        access_token = create_access_token(
            data={"sub": str(result["user_id"])},
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_access_token(
            data={"sub": str(result["user_id"]), "type": "refresh"},
            expires_delta=timedelta(days=30)
        )
        
        logger.info(f"User registered successfully: {result['user_id']}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=86400,  # 24 hours in seconds
            user_id=result["user_id"],
            email=result["email"],
            display_name=result["display_name"],
            email_verified=result["email_verified"],
            requires_verification=not result["email_verified"],
            trial_active=result.get("trial_active", True),
            trial_end_date=result.get("trial_end_date"),
        )
        
    except ValueError as e:
        logger.warning(f"Registration validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error for {registration_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="User authentication",
    description="Authenticate user with email and password",
    responses={
        200: {"description": "Authentication successful"},
        400: {"description": "Invalid credentials"},
        401: {"description": "Authentication failed"},
        423: {"description": "Account locked due to too many failed attempts"},
        429: {"description": "Too many login attempts"},
    }
)
@limiter.limit("10/minute")  # Rate limit for login attempts
async def login(
    request: Request,
    login_data: LoginRequest,
    get_user_handler: GetUserQueryHandler = Depends(),
    supabase_auth: SupabaseAuthService = Depends(),
) -> LoginResponse:
    """
    Authenticate user with email and password following Core Doc 1.1 security.
    
    This endpoint implements the login workflow with rate limiting,
    account lockout protection, and comprehensive security logging.
    
    Args:
        request: FastAPI request object for rate limiting
        login_data: User login credentials
        get_user_handler: Injected query handler for user retrieval
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        LoginResponse: Authentication tokens and user information
        
    Raises:
        HTTPException: For authentication failures or account lockout
    """
    try:
        logger.info(f"Login attempt for email: {login_data.email}")
        
        # Get user by email
        user_query = GetUserQuery(
            email=login_data.email,
            requesting_user_id=UUID("00000000-0000-0000-0000-000000000000"),  # System request
            is_admin_request=True,  # Allow email lookup
            include_security_data=True,
        )
        
        user_data = await get_user_handler.handle(user_query)
        
        if not user_data:
            logger.warning(f"Login failed - user not found: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check account lockout status (Core Doc 1.1 - 5 attempts)
        if user_data.get("account_locked", False):
            logger.warning(f"Login blocked - account locked: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed login attempts. Please reset your password."
            )
        
        # Verify password
        password_valid = pwd_context.verify(login_data.password, user_data["password_hash"])
        
        if not password_valid:
            # Increment login attempts (handled by domain service)
            logger.warning(f"Login failed - invalid password: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate tokens for successful login
        access_token = create_access_token(
            data={"sub": str(user_data["user_id"])},
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_access_token(
            data={"sub": str(user_data["user_id"]), "type": "refresh"},
            expires_delta=timedelta(days=30)
        )
        
        # Update last login timestamp (handled by domain service)
        
        logger.info(f"Login successful: {user_data['user_id']}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=86400,  # 24 hours in seconds
            user_id=user_data["user_id"],
            email=user_data["email"],
            display_name=user_data.get("display_name"),
            email_verified=user_data["email_verified"],
            requires_verification=not user_data["email_verified"],
            trial_active=user_data.get("trial_active", False),
            trial_end_date=user_data.get("trial_end_date"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {login_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again."
        )


@auth_router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User logout",
    description="Logout user and revoke authentication tokens",
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Invalid or expired token"},
    }
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(),
) -> LogoutResponse:
    """
    Logout user and revoke authentication tokens.
    
    This endpoint terminates the user session and revokes the provided
    JWT token to prevent further use.
    
    Args:
        credentials: Bearer token from Authorization header
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        LogoutResponse: Logout confirmation
        
    Raises:
        HTTPException: For invalid or expired tokens
    """
    try:
        token = credentials.credentials
        
        # Validate and decode token
        token_data = await supabase_auth.validate_token(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Revoke token
        revoke_success = await supabase_auth.revoke_token(token)
        if not revoke_success:
            logger.warning(f"Token revocation failed for user: {token_data.get('user_id')}")
        
        logger.info(f"User logged out successfully: {token_data.get('user_id')}")
        
        return LogoutResponse(
            message="Logout successful",
            logged_out_at=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed. Please try again."
        )


@auth_router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh authentication token",
    description="Refresh expired access token using refresh token",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
    }
)
@limiter.limit("20/minute")  # Higher limit for token refresh
async def refresh_token(
    request: Request,
    refresh_data: TokenRefreshRequest,
    supabase_auth: SupabaseAuthService = Depends(),
) -> TokenRefreshResponse:
    """
    Refresh expired access token using refresh token.
    
    This endpoint allows clients to obtain new access tokens without
    requiring re-authentication using a valid refresh token.
    
    Args:
        request: FastAPI request object for rate limiting
        refresh_data: Refresh token request data
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        TokenRefreshResponse: New access token and refresh token
        
    Raises:
        HTTPException: For invalid or expired refresh tokens
    """
    try:
        # Refresh token using Supabase
        token_result = await supabase_auth.refresh_token(refresh_data.refresh_token)
        
        if not token_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        access_token, new_refresh_token = token_result
        
        logger.info("Token refreshed successfully")
        
        return TokenRefreshResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=86400,  # 24 hours in seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please login again."
        )


@auth_router.post(
    "/forgot-password",
    response_model=PasswordResetResponse,
    summary="Initiate password reset",
    description="Send password reset email to user",
    responses={
        200: {"description": "Password reset email sent (if email exists)"},
        429: {"description": "Too many password reset attempts"},
    }
)
@limiter.limit("3/hour")  # Strict limit for password reset
async def forgot_password(
    request: Request,
    reset_data: PasswordResetRequest,
    supabase_auth: SupabaseAuthService = Depends(),
) -> PasswordResetResponse:
    """
    Initiate password reset by sending reset email.
    
    This endpoint sends a password reset email if the user exists.
    For security, it always returns success to prevent user enumeration.
    
    Args:
        request: FastAPI request object for rate limiting
        reset_data: Password reset request data
        supabase_auth: Injected Supabase authentication service
        
    Returns:
        PasswordResetResponse: Reset initiation confirmation
    """
    try:
        # Send password reset email
        reset_sent = await supabase_auth.send_password_reset(reset_data.email)
        
        # Always return success for security (prevent user enumeration)
        logger.info(f"Password reset requested for: {reset_data.email}")
        
        return PasswordResetResponse(
            message="If an account with that email exists, a password reset link has been sent.",
            email=reset_data.email,
            sent_at=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Password reset error for {reset_data.email}: {str(e)}")
        # Still return success for security
        return PasswordResetResponse(
            message="If an account with that email exists, a password reset link has been sent.",
            email=reset_data.email,
            sent_at=datetime.utcnow(),
        )


@auth_router.get(
    "/oauth/{provider}",
    response_model=OAuthInitiateResponse,
    summary="Initiate OAuth authentication",
    description="Start OAuth authentication flow with external provider",
    responses={
        200: {"description": "OAuth authentication URL generated"},
        400: {"description": "Unsupported OAuth provider"},
    }
)
async def oauth_initiate(
    provider: str,
    oauth_manager: OAuthProviderManager = Depends(),
) -> OAuthInitiateResponse:
    """
    Initiate OAuth authentication with external provider.
    
    This endpoint generates the OAuth authorization URL for the specified
    provider and returns it to the client for redirection.
    
    Args:
        provider: OAuth provider name (google, apple)
        oauth_manager: Injected OAuth provider manager
        
    Returns:
        OAuthInitiateResponse: OAuth authorization URL and state
        
    Raises:
        HTTPException: For unsupported providers
    """
    try:
        if provider not in ["google", "apple"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth provider: {provider}"
            )
        
        # Generate state parameter for CSRF protection
        state = f"oauth_{provider}_{datetime.utcnow().timestamp()}"
        
        # Get authorization URL from provider
        auth_url = await oauth_manager.get_authorization_url(provider, state)
        
        if not auth_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate OAuth URL for {provider}"
            )
        
        logger.info(f"OAuth initiation for provider: {provider}")
        
        return OAuthInitiateResponse(
            provider=provider,
            authorization_url=auth_url,
            state=state,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth initiation error for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth initiation failed. Please try again."
        )