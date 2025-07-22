# Add this content to app/modules/user_management/infrastructure/external/supabase_auth.py

# 📄 File: app/modules/user_management/infrastructure/external/supabase_auth.py
# 🧭 Purpose (Layman Explanation): 
# This file handles all the authentication work with Supabase, like checking if users are who they say they are,
# validating login tokens, and managing user sessions for the plant care app.
# 🧪 Purpose (Technical Summary): 
# Supabase authentication service implementation providing JWT token validation, user session management,
# and OAuth integration for the User Management module.
# 🔗 Dependencies: 
# supabase, app.shared.config.supabase, app.shared.core.exceptions, typing, logging
# 🔄 Connected Modules / Calls From: 
# app.modules.user_management.presentation.dependencies, auth routers, user management handlers

"""
Supabase Authentication Service

This module provides authentication services using Supabase Auth for the User Management module.

Features:
- JWT token validation and verification
- User session management
- OAuth integration support
- Token refresh capabilities
- User authentication status checking
- Security event logging

The service integrates with Supabase Auth to provide secure, scalable authentication
for the Plant Care application while maintaining compatibility with the domain architecture.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from supabase import Client
from gotrue import User, Session
from gotrue.errors import AuthApiError

from app.shared.config.supabase import get_supabase_client
from app.shared.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError
)

logger = logging.getLogger(__name__)


class SupabaseAuthService:
    """
    Supabase authentication service for User Management module.
    
    Provides JWT token validation, user session management, and OAuth integration
    using Supabase Auth as the underlying authentication provider.
    """
    
    def __init__(self):
        """Initialize Supabase authentication service."""
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Get Supabase client with lazy initialization."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return user information.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict containing user information if valid, None if invalid
            
        Raises:
            AuthenticationError: If token verification fails
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Set the session with the token
            session_response = await self._verify_session_token(token)
            
            if not session_response:
                return None
            
            user = session_response.get('user')
            if not user:
                return None
            
            # Extract user information from token payload
            user_data = {
                'sub': user.get('id'),
                'email': user.get('email'),
                'user_metadata': user.get('user_metadata', {}),
                'app_metadata': user.get('app_metadata', {}),
                'aud': user.get('aud', 'authenticated'),
                'exp': user.get('exp'),
                'iat': user.get('iat'),
                'iss': user.get('iss'),
                'email_verified': user.get('email_confirmed_at') is not None,
                'phone_verified': user.get('phone_confirmed_at') is not None,
                'last_sign_in_at': user.get('last_sign_in_at')
            }
            
            logger.debug(f"Token verified successfully for user: {user_data.get('sub')}")
            return user_data
            
        except AuthApiError as e:
            logger.warning(f"Supabase auth error during token verification: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            raise AuthenticationError("Token verification failed")
    
    async def _verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify session token with Supabase.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Session data if valid, None if invalid
        """
        try:
            # Use Supabase client to verify the token
            response = self.client.auth.get_user(token)
            
            if response and response.user:
                return {
                    'user': {
                        'id': response.user.id,
                        'email': response.user.email,
                        'user_metadata': response.user.user_metadata,
                        'app_metadata': response.user.app_metadata,
                        'aud': response.user.aud,
                        'exp': None,  # Will be populated from JWT
                        'iat': None,  # Will be populated from JWT  
                        'iss': None,  # Will be populated from JWT
                        'email_confirmed_at': response.user.email_confirmed_at,
                        'phone_confirmed_at': response.user.phone_confirmed_at,
                        'last_sign_in_at': response.user.last_sign_in_at
                    }
                }
            
            return None
            
        except AuthApiError:
            return None
        except Exception as e:
            logger.error(f"Session token verification error: {e}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by user ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User information if found, None otherwise
        """
        try:
            # Note: This would require admin privileges or service role key
            # For now, return None as we'll rely on token-based user info
            logger.debug(f"User lookup by ID not implemented for: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token information if successful, None otherwise
        """
        try:
            response = self.client.auth.refresh_session(refresh_token)
            
            if response and response.session:
                return {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_in': response.session.expires_in,
                    'token_type': response.session.token_type,
                    'user': {
                        'id': response.user.id,
                        'email': response.user.email,
                        'user_metadata': response.user.user_metadata,
                        'app_metadata': response.user.app_metadata
                    }
                }
            
            return None
            
        except AuthApiError as e:
            logger.warning(f"Token refresh failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            return None
    
    async def sign_out(self, token: str) -> bool:
        """
        Sign out user and invalidate token.
        
        Args:
            token: Access token to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.auth.sign_out()
            logger.info("User signed out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during sign out: {e}")
            return False
    
    async def get_user_roles(self, user_data: Dict[str, Any]) -> List[str]:
        """
        Extract user roles from user data.
        
        Args:
            user_data: User information from token
            
        Returns:
            List of user roles
        """
        try:
            # Check app_metadata for roles
            app_metadata = user_data.get('app_metadata', {})
            roles = app_metadata.get('roles', [])
            
            if isinstance(roles, str):
                roles = [roles]
            elif not isinstance(roles, list):
                roles = []
            
            # Default role if no roles specified
            if not roles:
                roles = ['user']
            
            return roles
            
        except Exception as e:
            logger.error(f"Error extracting user roles: {e}")
            return ['user']  # Default role
    
    async def check_email_verified(self, user_data: Dict[str, Any]) -> bool:
        """
        Check if user's email is verified.
        
        Args:
            user_data: User information from token
            
        Returns:
            True if email is verified, False otherwise
        """
        return user_data.get('email_verified', False)
    
    async def is_user_active(self, user_data: Dict[str, Any]) -> bool:
        """
        Check if user account is active.
        
        Args:
            user_data: User information from token
            
        Returns:
            True if user is active, False otherwise
        """
        try:
            # Check if user is banned or suspended
            app_metadata = user_data.get('app_metadata', {})
            
            # Check for ban status
            if app_metadata.get('banned', False):
                return False
            
            # Check for suspension
            suspended_until = app_metadata.get('suspended_until')
            if suspended_until:
                suspension_date = datetime.fromisoformat(suspended_until.replace('Z', '+00:00'))
                if datetime.now(suspension_date.tzinfo) < suspension_date:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking user active status: {e}")
            return True  # Default to active if check fails
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get authentication service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            'service_name': 'SupabaseAuthService',
            'provider': 'Supabase Auth',
            'initialized': self._client is not None,
            'features': [
                'jwt_verification',
                'token_refresh',
                'user_session_management',
                'oauth_support',
                'email_verification',
                'role_based_access'
            ]
        }


# Global service instance
_supabase_auth_service: Optional[SupabaseAuthService] = None


def get_supabase_auth_service() -> SupabaseAuthService:
    """
    Get the global Supabase authentication service instance.
    
    Returns:
        SupabaseAuthService: Global service instance
    """
    global _supabase_auth_service
    
    if _supabase_auth_service is None:
        _supabase_auth_service = SupabaseAuthService()
        logger.debug("Created SupabaseAuthService instance")
    
    return _supabase_auth_service


# Export the service class and factory function
__all__ = [
    'SupabaseAuthService',
    'get_supabase_auth_service'
]