# 📄 File: app/modules/user_management/infrastructure/external/__init__.py
# 🧭 Purpose (Layman Explanation):
# This file organizes connections to external services like Google sign-in, Apple ID,
# and Supabase authentication that help users log into our plant care app easily.
#
# 🧪 Purpose (Technical Summary):
# External services integration layer for user management, providing OAuth providers,
# Supabase authentication, and third-party service integrations for user authentication.
#
# 🔗 Dependencies:
# - Supabase client and authentication services
# - OAuth provider SDKs (Google, Apple)
# - External API clients and authentication libraries
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.infrastructure.__init__ (service registration)
# - app.modules.user_management.domain.services (external authentication)
# - app.modules.user_management.application.handlers (OAuth authentication flows)

"""
User Management External Services

This module provides integrations with external authentication services
and OAuth providers for seamless user authentication experiences.

External Services:
- Supabase: Authentication service integration
- OAuth Providers: Google, Apple, and other OAuth integrations
- Third-party APIs: External authentication and user verification services
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.user_management.infrastructure.external.supabase_auth import SupabaseAuthService
    from app.modules.user_management.infrastructure.external.oauth_providers import (
        OAuthProviderManager,
        GoogleOAuthProvider,
        AppleOAuthProvider,
    )

__all__ = [
    "SupabaseAuthService",
    "OAuthProviderManager",
    "GoogleOAuthProvider", 
    "AppleOAuthProvider",
]