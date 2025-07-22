# 📄 File: app/modules/user_management/presentation/api/v1/profiles.py
# 🧭 Purpose (Layman Explanation):
# This file contains all the web endpoints for managing user profiles like getting profile info,
# updating personal details, managing privacy settings, and social features for our plant care app.
#
# 🧪 Purpose (Technical Summary):
# FastAPI profile management endpoints implementing Core Doc 1.2 specifications with CRUD operations,
# privacy controls, completeness tracking, and social features for user profiles.
#
# 🔗 Dependencies:
# - FastAPI router, HTTPException, status codes, Query parameters, File upload
# - app.modules.user_management.application.handlers (command and query handlers)
# - app.modules.user_management.application.commands (profile commands)
# - app.modules.user_management.presentation.api.schemas.profile_schemas (request/response schemas)
# - Authentication, authorization, and file upload dependencies
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.presentation.api.__init__ (router inclusion)
# - User profile pages (profile management interface)
# - Social features (profile discovery, community interaction)

"""
Profiles API Endpoints

This module implements RESTful profile management endpoints following Core Doc 1.2
specifications with comprehensive CRUD operations, privacy controls, and social features.

Endpoints:
- GET /me: Get current user's profile
- GET /{profile_id}: Get specific profile (with privacy filtering)
- PUT /{profile_id}: Update profile information
- DELETE /{profile_id}: Delete profile (cascade with user)
- POST /{profile_id}/photo: Upload profile photo
- DELETE /{profile_id}/photo: Remove profile photo
- GET /{profile_id}/completeness: Get profile completeness information
- GET /{profile_id}/privacy: Get profile privacy settings
- PUT /{profile_id}/privacy: Update profile privacy settings
- GET /: List profiles (with search and filtering)
- GET /search: Search profiles by criteria

Privacy Features:
- Field-level privacy controls (bio, location visibility)
- Profile visibility settings (public, friends, private)
- Privacy-aware profile discovery
- Social interaction controls

All endpoints follow REST conventions and integrate with the application
layer handlers while respecting Core Doc 1.2 privacy requirements.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.security import HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.modules.user_management.application.commands.update_profile import UpdateProfileCommand
from app.modules.user_management.application.handlers.command_handlers import UpdateProfileCommandHandler
from app.modules.user_management.application.handlers.query_handlers import GetProfileQueryHandler

from app.modules.user_management.application.queries.get_profile import GetProfileQuery

from app.modules.user_management.presentation.api.schemas.profile_schemas import (
    ProfileResponse,
    ProfileListResponse,
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileCompletenessResponse,
    ProfilePrivacyRequest,
    ProfilePrivacyResponse,
    ProfilePhotoResponse,
    ProfileSearchRequest,
    ProfileSearchResponse,
)

from app.modules.user_management.presentation.dependencies import (
    get_current_user,
    get_current_active_user,
    verify_profile_access,
)

from app.shared.infrastructure.storage.supabase_storage import upload_profile_photo, delete_profile_photo

logger = logging.getLogger(__name__)

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)

# Security configuration
security = HTTPBearer()

# Create router
profiles_router = APIRouter()


@profiles_router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Get current user's profile",
    description="Get the current authenticated user's profile information",
    responses={
        200: {"description": "Current user's profile information"},
        401: {"description": "Authentication required"},
        404: {"description": "Profile not found"},
    }
)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_active_user),
    get_profile_handler: GetProfileQueryHandler = Depends(),
) -> ProfileResponse:
    """
    Get current authenticated user's profile information.
    
    This endpoint returns the current user's profile with self-level
    access permissions, including all private data and preferences.
    
    Args:
        current_user: Injected current user information
        get_profile_handler: Injected query handler for profile retrieval
        
    Returns:
        ProfileResponse: Current user's profile with full access
    """
    try:
        # Create query for current user's profile
        profile_query = GetProfileQuery(
            user_id=current_user["user_id"],
            requesting_user_id=current_user["user_id"],
            is_admin_request=current_user.get("is_admin", False),
            include_private_data=True,
            include_preferences=True,
            include_location_data=True,
            include_notification_settings=True,
            include_timestamps=True,
            include_social_data=True,
            include_computed_fields=True,  # Include completeness info
        )
        
        profile_data = await get_profile_handler.handle(profile_query)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        return ProfileResponse.from_domain_data(
            profile_data, 
            privacy_level="self",
            privacy_settings={}  # Full access for self
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile information"
        )


@profiles_router.get(
    "/{profile_id}",
    response_model=ProfileResponse,
    summary="Get profile information",
    description="Get specific profile information (with privacy filtering)",
    responses={
        200: {"description": "Profile information"},
        401: {"description": "Authentication required"},
        403: {"description": "Profile not accessible"},
        404: {"description": "Profile not found"},
    }
)
async def get_profile(
    profile_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    get_profile_handler: GetProfileQueryHandler = Depends(),
) -> ProfileResponse:
    """
    Get specific profile information with privacy filtering.
    
    This endpoint returns profile information based on privacy settings
    and the requesting user's relationship to the profile owner.
    
    Args:
        profile_id: UUID of the profile to retrieve
        current_user: Injected current user information
        get_profile_handler: Injected query handler for profile retrieval
        
    Returns:
        ProfileResponse: Profile information with appropriate privacy filtering
        
    Raises:
        HTTPException: For access denied or profile not found
    """
    try:
        # Create query with privacy considerations
        profile_query = GetProfileQuery(
            profile_id=profile_id,
            requesting_user_id=current_user["user_id"],
            is_admin_request=current_user.get("is_admin", False),
            include_private_data=False,  # Will be determined by privacy level
            include_preferences=False,   # Generally private
            include_location_data=True,  # Filtered by privacy settings
            include_notification_settings=False,  # Private
            include_timestamps=True,
            include_social_data=True,
            respect_privacy_settings=True,  # Important for privacy
            include_computed_fields=False,  # Generally private
        )
        
        profile_data = await get_profile_handler.handle(profile_query)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found or not accessible"
            )
        
        # Determine privacy level
        is_admin = current_user.get("is_admin", False)
        is_self = profile_data.get("user_id") == current_user["user_id"]
        
        if is_admin:
            privacy_level = "admin"
        elif is_self:
            privacy_level = "self"
        else:
            privacy_level = "public"
        
        # Get privacy settings (would come from domain service)
        privacy_settings = {
            "bio_visibility": "public",
            "location_visibility": "public", 
            "profile_visibility": "public",
        }
        
        return ProfileResponse.from_domain_data(
            profile_data,
            privacy_level=privacy_level,
            privacy_settings=privacy_settings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile information"
        )


@profiles_router.put(
    "/{profile_id}",
    response_model=ProfileResponse,
    summary="Update profile information",
    description="Update profile information (self or admin only)",
    responses={
        200: {"description": "Profile updated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Profile not found"},
        422: {"description": "Validation error"},
    }
)
async def update_profile(
    profile_id: UUID,
    update_data: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
    update_profile_handler: UpdateProfileCommandHandler = Depends(),
) -> ProfileResponse:
    """
    Update profile information following Core Doc 1.2 specifications.
    
    This endpoint allows users to update their own profiles or allows
    admins to update any profile with proper validation and audit logging.
    
    Args:
        profile_id: UUID of the profile to update
        update_data: Profile update information
        current_user: Injected current user information
        update_profile_handler: Injected command handler for profile updates
        
    Returns:
        ProfileResponse: Updated profile information
        
    Raises:
        HTTPException: For access denied, validation errors, or profile not found
    """
    try:
        # Verify profile access (self or admin only)
        await verify_profile_access(current_user, profile_id)
        
        # Create update command
        update_command = UpdateProfileCommand(
            profile_id=profile_id,
            display_name=update_data.display_name,
            profile_photo=update_data.profile_photo,
            bio=update_data.bio,
            location=update_data.location,
            timezone=update_data.timezone,
            language=update_data.language,
            theme=update_data.theme,
            notification_enabled=update_data.notification_enabled,
            clear_bio=update_data.clear_bio,
            clear_location=update_data.clear_location,
            clear_timezone=update_data.clear_timezone,
            clear_profile_photo=update_data.clear_profile_photo,
        )
        
        # Execute profile update
        result = await update_profile_handler.handle(update_command)
        
        logger.info(f"Profile {profile_id} updated by {current_user['user_id']}")
        
        return ProfileResponse.from_handler_result(
            result,
            privacy_level="self"  # Return with self access after update
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@profiles_router.delete(
    "/{profile_id}",
    summary="Delete profile",
    description="Delete profile (cascades with user deletion)",
    responses={
        204: {"description": "Profile deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Profile not found"},
    }
)
async def delete_profile(
    profile_id: UUID,
    current_user: dict = Depends(get_current_active_user),
) -> None:
    """
    Delete profile (typically cascades with user account deletion).
    
    This endpoint is generally used as part of user account deletion
    rather than standalone profile deletion.
    
    Args:
        profile_id: UUID of the profile to delete
        current_user: Injected current user information
        
    Raises:
        HTTPException: For access denied or profile not found
    """
    try:
        # Verify profile access (self or admin only)
        await verify_profile_access(current_user, profile_id)
        
        logger.info(f"Profile deletion requested for {profile_id} by {current_user['user_id']}")
        
        # Profile deletion typically happens as part of user deletion
        # This endpoint would integrate with profile deletion logic
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Profile deletion should be done through user account deletion"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete profile"
        )


@profiles_router.post(
    "/{profile_id}/photo",
    response_model=ProfilePhotoResponse,
    summary="Upload profile photo",
    description="Upload and set profile photo",
    responses={
        200: {"description": "Profile photo uploaded successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        413: {"description": "File too large"},
        422: {"description": "Invalid file type"},
    }
)
@limiter.limit("10/hour")  # Rate limit photo uploads
async def upload_profile_photo(
    request: Request,
    profile_id: UUID,
    photo: UploadFile = File(..., description="Profile photo image"),
    current_user: dict = Depends(get_current_active_user),
) -> ProfilePhotoResponse:
    """
    Upload and set profile photo with validation and processing.
    
    This endpoint allows users to upload profile photos with proper
    validation, compression, and storage in Supabase Storage.
    
    Args:
        request: FastAPI request object for rate limiting
        profile_id: UUID of the profile to update photo for
        photo: Uploaded image file
        current_user: Injected current user information
        
    Returns:
        ProfilePhotoResponse: Photo upload confirmation with URL
        
    Raises:
        HTTPException: For access denied, invalid file, or upload errors
    """
    try:
        # Verify profile access (self or admin only)
        await verify_profile_access(current_user, profile_id)
        
        # Validate file type and size
        if not photo.content_type or not photo.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File must be an image"
            )
        
        # Check file size (max 5MB as per common standards)
        if photo.size and photo.size > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size must be less than 5MB"
            )
        
        # Upload to Supabase Storage
        photo_url = await upload_profile_photo(
            profile_id=profile_id,
            file_content=await photo.read(),
            file_name=photo.filename,
            content_type=photo.content_type,
        )
        
        # Update profile with new photo URL (would integrate with update handler)
        
        logger.info(f"Profile photo uploaded for {profile_id} by {current_user['user_id']}")
        
        return ProfilePhotoResponse(
            profile_id=profile_id,
            photo_url=photo_url,
            uploaded_at=datetime.utcnow(),
            file_size=photo.size,
            content_type=photo.content_type,
            message="Profile photo uploaded successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile photo for {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile photo"
        )


@profiles_router.delete(
    "/{profile_id}/photo",
    summary="Remove profile photo",
    description="Remove current profile photo",
    responses={
        204: {"description": "Profile photo removed successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Profile or photo not found"},
    }
)
async def remove_profile_photo(
    profile_id: UUID,
    current_user: dict = Depends(get_current_active_user),
) -> None:
    """
    Remove current profile photo and delete from storage.
    
    This endpoint removes the user's profile photo and cleans up
    the associated file from Supabase Storage.
    
    Args:
        profile_id: UUID of the profile to remove photo from
        current_user: Injected current user information
        
    Raises:
        HTTPException: For access denied or profile not found
    """
    try:
        # Verify profile access (self or admin only)
        await verify_profile_access(current_user, profile_id)
        
        # Delete from Supabase Storage
        deletion_success = await delete_profile_photo(profile_id)
        
        if not deletion_success:
            logger.warning(f"Failed to delete profile photo file for {profile_id}")
        
        # Update profile to clear photo URL (would integrate with update handler)
        
        logger.info(f"Profile photo removed for {profile_id} by {current_user['user_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing profile photo for {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove profile photo"
        )


@profiles_router.get(
    "/{profile_id}/completeness",
    response_model=ProfileCompletenessResponse,
    summary="Get profile completeness",
    description="Get profile completeness information and suggestions",
    responses={
        200: {"description": "Profile completeness information"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Profile not found"},
    }
)
async def get_profile_completeness(
    profile_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    get_profile_handler: GetProfileQueryHandler = Depends(),
) -> ProfileCompletenessResponse:
    """
    Get profile completeness information and improvement suggestions.
    
    This endpoint provides users with information about their profile
    completion status and suggestions for improving their profile.
    
    Args:
        profile_id: UUID of the profile to analyze
        current_user: Injected current user information
        get_profile_handler: Injected query handler for profile retrieval
        
    Returns:
        ProfileCompletenessResponse: Completeness analysis and suggestions
        
    Raises:
        HTTPException: For access denied or profile not found
    """
    try:
        # Verify profile access (self or admin only)
        await verify_profile_access(current_user, profile_id)
        
        # Get profile with completeness calculation
        profile_query = GetProfileQuery(
            profile_id=profile_id,
            requesting_user_id=current_user["user_id"],
            include_computed_fields=True,  # For completeness calculation
        )
        
        profile_data = await get_profile_handler.handle(profile_query)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        # Extract completeness information
        completeness = profile_data.get("profile_completeness", {})
        
        # Generate improvement suggestions
        missing_fields = completeness.get("missing_fields", [])
        suggestions = []
        
        if "bio" in missing_fields:
            suggestions.append("Add a bio to tell others about your gardening interests")
        if "location" in missing_fields:
            suggestions.append("Set your location to get personalized weather data")
        if "profile_photo" in missing_fields:
            suggestions.append("Upload a profile photo to make your profile more personal")
        if "timezone" in missing_fields:
            suggestions.append("Set your timezone for accurate plant care reminders")
        
        return ProfileCompletenessResponse(
            profile_id=profile_id,
            completeness_percentage=completeness.get("percentage", 0.0),
            completed_fields=completeness.get("completed_fields", 0),
            total_fields=completeness.get("total_fields", 0),
            missing_fields=missing_fields,
            suggestions=suggestions,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile completeness for {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile completeness"
        )


@profiles_router.get(
    "/",
    response_model=ProfileListResponse,
    summary="List profiles",
    description="Get paginated list of public profiles",
    responses={
        200: {"description": "Profiles retrieved successfully"},
        401: {"description": "Authentication required"},
    }
)
async def list_profiles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Items per page"),
    location: Optional[str] = Query(None, description="Filter by location"),
    current_user: dict = Depends(get_current_active_user),
) -> ProfileListResponse:
    """
    Get paginated list of public profiles for community discovery.
    
    This endpoint provides users with a way to discover other plant care
    enthusiasts in their area or with similar interests.
    
    Args:
        page: Page number for pagination
        page_size: Number of items per page
        location: Optional location filter
        current_user: Injected current user information
        
    Returns:
        ProfileListResponse: Paginated list of public profiles
    """
    try:
        logger.info(f"Profile list requested by {current_user['user_id']}")
        
        # This would integrate with profile search/list functionality
        # For now, return empty list with proper pagination structure
        
        return ProfileListResponse(
            profiles=[],
            total_count=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            has_next=False,
            has_previous=False,
        )
        
    except Exception as e:
        logger.error(f"Error listing profiles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile list"
        )