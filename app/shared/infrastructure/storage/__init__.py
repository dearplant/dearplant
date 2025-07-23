# 📄 File: app/shared/infrastructure/storage/__init__.py
#
# 🧭 Purpose (Layman Explanation):
# Sets up the file storage system that handles uploading, storing, and managing
# user photos (plant pictures, profile photos) using Supabase Storage.
#
# 🧪 Purpose (Technical Summary):
# Initializes the storage infrastructure layer with Supabase Storage integration,
# file management utilities, and storage operations for all file handling needs.
#
# 🔗 Dependencies:
# - app/shared/infrastructure/storage/supabase_storage.py
# - app/shared/infrastructure/storage/file_manager.py
# - supabase (storage client)
#
# 🔄 Connected Modules / Calls From:
# - All modules requiring file storage (user profiles, plant photos, etc.)
# - Image upload endpoints (plant identification, growth tracking)
# - Background jobs (image processing and optimization)

"""
Storage Infrastructure Package

This package provides comprehensive file storage capabilities including:
- Supabase Storage integration for cloud file storage
- File upload and download operations with validation
- Image processing and optimization
- File metadata management
- Storage quota and usage tracking

Storage Organization:
- users/{user_id}/profile/ - User profile photos
- plants/{user_id}/{plant_id}/ - Plant photos and growth tracking
- community/{user_id}/posts/ - Community post media
- temp/ - Temporary file storage for processing
- public/ - Publicly accessible files (plant library images)

Supported File Types:
- Images: JPEG, PNG, WebP (auto-optimized)
- Documents: PDF (for care guides)
- Maximum file size: 10MB for images, 50MB for documents

Usage Examples:
    from app.shared.infrastructure.storage import get_file_manager
    
    file_manager = get_file_manager()
    
    # Upload plant photo
    url = await file_manager.upload_plant_photo(
        user_id="123", 
        plant_id="456", 
        file_data=image_bytes,
        filename="growth_week1.jpg"
    )
    
    # Download file
    file_data = await file_manager.download_file(url)
"""

from typing import Optional, Dict, Any, List, Union, BinaryIO
import logging
from pathlib import Path

# Import storage components
from .supabase_storage import SupabaseStorageClient, get_storage_client as get_supabase_storage
from .file_manager import FileManager, get_file_manager

logger = logging.getLogger(__name__)

# Module-level storage instances
_supabase_storage: Optional[SupabaseStorageClient] = None
_file_manager: Optional[FileManager] = None

# Storage configuration constants
STORAGE_BUCKETS = {
    "user_content": "user-content",      # User-generated content
    "plant_library": "plant-library",    # Plant library images
    "community": "community",            # Community posts media
    "system": "system",                  # System files and assets
    "temp": "temp"                       # Temporary file storage
}

# File type configurations
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png", 
    "image/webp": ".webp",
    "image/heic": ".heic"
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/json": ".json"
}

# Size limits (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024      # 10MB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024   # 50MB
MAX_TEMP_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Storage paths
STORAGE_PATHS = {
    "user_profiles": "users/{user_id}/profile/",
    "plant_photos": "plants/{user_id}/{plant_id}/",
    "growth_tracking": "plants/{user_id}/{plant_id}/growth/",
    "health_photos": "plants/{user_id}/{plant_id}/health/",
    "community_posts": "community/{user_id}/posts/",
    "plant_library": "library/{category}/",
    "temp_uploads": "temp/{user_id}/",
    "system_assets": "system/{type}/"
}

# Image optimization settings
IMAGE_OPTIMIZATION = {
    "thumbnail_size": (150, 150),
    "medium_size": (800, 600),
    "large_size": (1920, 1080),
    "quality": 85,
    "format": "webp"  # Default optimized format
}


async def initialize_storage() -> None:
    """
    Initialize the storage infrastructure.
    
    This function sets up Supabase Storage connection and file manager,
    and should be called during application startup.
    """
    global _supabase_storage, _file_manager
    
    try:
        logger.info("Initializing storage infrastructure...")
        
        # Initialize Supabase Storage client
        _supabase_storage = get_supabase_storage()
        await _supabase_storage.initialize()
        
        # Initialize file manager
        _file_manager = get_file_manager()
        await _file_manager.initialize()
        
        # Ensure required buckets exist
        await _ensure_buckets_exist()
        
        # Perform health checks
        health_check = await _supabase_storage.health_check()
        if not health_check["healthy"]:
            logger.warning(f"Storage health check failed: {health_check.get('error')}")
        
        logger.info("Storage infrastructure initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize storage infrastructure: {e}")
        raise


async def shutdown_storage() -> None:
    """
    Shutdown the storage infrastructure.
    
    This function closes storage connections and should be called
    during application shutdown.
    """
    global _supabase_storage, _file_manager
    
    try:
        logger.info("Shutting down storage infrastructure...")
        
        if _file_manager:
            await _file_manager.close()
            _file_manager = None
            
        if _supabase_storage:
            await _supabase_storage.close()
            _supabase_storage = None
            
        logger.info("Storage infrastructure shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during storage shutdown: {e}")
        raise


async def _ensure_buckets_exist() -> None:
    """Ensure all required storage buckets exist."""
    if not _supabase_storage:
        logger.warning("Supabase storage not initialized, skipping bucket creation")
        return
        
    try:
        for bucket_name, bucket_id in STORAGE_BUCKETS.items():
            exists = await _supabase_storage.bucket_exists(bucket_id)
            if not exists:
                logger.info(f"Creating storage bucket: {bucket_id}")
                await _supabase_storage.create_bucket(
                    bucket_id,
                    public=bucket_name in ["plant_library", "system"]  # Make some buckets public
                )
            else:
                logger.debug(f"Storage bucket exists: {bucket_id}")
                
    except Exception as e:
        logger.error(f"Failed to ensure buckets exist: {e}")
        # Don't raise exception as app can still function without all buckets


def get_storage_path(path_type: str, **kwargs) -> str:
    """
    Get a standardized storage path.
    
    Args:
        path_type: Type of storage path (from STORAGE_PATHS)
        **kwargs: Variables to substitute in path template
        
    Returns:
        str: Formatted storage path
        
    Example:
        get_storage_path("plant_photos", user_id="123", plant_id="456")
        -> "plants/123/456/"
    """
    if path_type not in STORAGE_PATHS:
        raise ValueError(f"Unknown storage path type: {path_type}")
    
    path_template = STORAGE_PATHS[path_type]
    
    try:
        return path_template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required parameter for storage path: {e}")


def get_file_size_limit(file_type: str) -> int:
    """
    Get the size limit for a file type.
    
    Args:
        file_type: MIME type of the file
        
    Returns:
        int: Maximum file size in bytes
    """
    if file_type in ALLOWED_IMAGE_TYPES:
        return MAX_IMAGE_SIZE
    elif file_type in ALLOWED_DOCUMENT_TYPES:
        return MAX_DOCUMENT_SIZE
    else:
        return MAX_TEMP_FILE_SIZE


def is_allowed_file_type(file_type: str, category: str = "any") -> bool:
    """
    Check if a file type is allowed.
    
    Args:
        file_type: MIME type of the file
        category: Category restriction ("image", "document", or "any")
        
    Returns:
        bool: True if file type is allowed
    """
    if category == "image":
        return file_type in ALLOWED_IMAGE_TYPES
    elif category == "document":
        return file_type in ALLOWED_DOCUMENT_TYPES
    else:
        return file_type in {**ALLOWED_IMAGE_TYPES, **ALLOWED_DOCUMENT_TYPES}


def get_file_extension(file_type: str) -> Optional[str]:
    """
    Get the file extension for a MIME type.
    
    Args:
        file_type: MIME type of the file
        
    Returns:
        Optional[str]: File extension or None if not found
    """
    all_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_DOCUMENT_TYPES}
    return all_types.get(file_type)


async def get_storage_stats() -> Dict[str, Any]:
    """
    Get storage statistics and usage information.
    
    Returns:
        Dict containing storage statistics
    """
    if not _supabase_storage or not _file_manager:
        return {
            "status": "not_initialized",
            "supabase_storage_ready": False,
            "file_manager_ready": False
        }
    
    try:
        # Get Supabase Storage stats
        storage_stats = await _supabase_storage.get_stats()
        
        # Get file manager stats
        file_manager_stats = await _file_manager.get_stats()
        
        return {
            "status": "healthy",
            "supabase_storage_ready": True,
            "file_manager_ready": True,
            "storage_stats": storage_stats,
            "file_manager_stats": file_manager_stats,
            "buckets": list(STORAGE_BUCKETS.values()),
            "configuration": {
                "max_image_size_mb": MAX_IMAGE_SIZE // (1024 * 1024),
                "max_document_size_mb": MAX_DOCUMENT_SIZE // (1024 * 1024),
                "allowed_image_types": list(ALLOWED_IMAGE_TYPES.keys()),
                "allowed_document_types": list(ALLOWED_DOCUMENT_TYPES.keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        return {
            "status": "error",
            "error": str(e),
            "supabase_storage_ready": False,
            "file_manager_ready": False
        }


async def cleanup_temp_files(older_than_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified hours.
    
    Args:
        older_than_hours: Clean files older than this many hours
        
    Returns:
        int: Number of files cleaned up
    """
    if not _file_manager:
        logger.warning("File manager not initialized")
        return 0
    
    try:
        cleaned_count = await _file_manager.cleanup_temp_files(older_than_hours)
        logger.info(f"Cleaned up {cleaned_count} temporary files")
        return cleaned_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup temporary files: {e}")
        return 0


# Export main components for easy importing
__all__ = [
    # Classes
    "SupabaseStorageClient",
    "FileManager",
    
    # Functions
    "get_supabase_storage",
    "get_file_manager", 
    "initialize_storage",
    "shutdown_storage",
    "get_storage_path",
    "get_file_size_limit",
    "is_allowed_file_type",
    "get_file_extension",
    "get_storage_stats",
    "cleanup_temp_files",
    
    # Constants
    "STORAGE_BUCKETS",
    "ALLOWED_IMAGE_TYPES",
    "ALLOWED_DOCUMENT_TYPES",
    "MAX_IMAGE_SIZE",
    "MAX_DOCUMENT_SIZE",
    "STORAGE_PATHS",
    "IMAGE_OPTIMIZATION",
]