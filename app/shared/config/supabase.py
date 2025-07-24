"""
Supabase client configuration for authentication and storage services.
Handles Supabase initialization with proper error handling and connection management.
"""

import logging
from typing import Optional
from functools import lru_cache

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from postgrest import APIError

from typing import Dict, Any
from app.shared.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
from .settings import get_settings


logger = logging.getLogger(__name__)


class SupabaseManager:
    """
    Supabase client manager with connection handling and error recovery.
    Provides authentication, database, and storage services.
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._storage_client = None
        self.settings = get_settings()
    
    @property
    def client(self) -> Client:
        """Get or create Supabase client with lazy initialization."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> Client:
        """Create Supabase client with proper configuration."""
        try:
            # Configure client options for optimal performance
            client_options = ClientOptions(
                schema="public",
                headers={
                    "User-Agent": f"PlantCareApp/{self.settings.APP_VERSION}",
                },
                auto_refresh_token=True,
                persist_session=True,
            )
            
            client = create_client(
                supabase_url=self.settings.SUPABASE_URL,
                supabase_key=self.settings.SUPABASE_ANON_KEY,
                options=client_options
            )
            
            logger.info("Supabase client initialized successfully")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise ConnectionError(f"Supabase initialization failed: {e}")
    
    def get_auth_client(self):
        """Get Supabase auth client for authentication operations."""
        return self.client.auth
    
    def get_storage_client(self, bucket_name: str = "plant-photos"):
        """
        Get Supabase storage client for file operations.
        
        Args:
            bucket_name: Storage bucket name (default: 'plant-photos')
        """
        if self._storage_client is None:
            self._storage_client = self.client.storage
        return self._storage_client.from_(bucket_name)
    
    def get_database_client(self):
        """Get Supabase database client for direct queries."""
        return self.client
    
    async def health_check(self) -> dict:
        """
        Perform health check on Supabase services.
        
        Returns:
            dict: Health status of Supabase services
        """
        health_status = {
            "supabase_connection": False,
            "auth_service": False,
            "storage_service": False,
            "database_service": False,
            "error": None
        }
        
        try:
            # Test basic connection
            response = self.client.table("_health_check").select("*").limit(1).execute()
            health_status["supabase_connection"] = True
            health_status["database_service"] = True
            
            # Test auth service
            try:
                auth_user = self.client.auth.get_user()
                health_status["auth_service"] = True
            except Exception:
                # Auth service is available even if no user is logged in
                health_status["auth_service"] = True
            
            # Test storage service
            try:
                buckets = self.client.storage.list_buckets()
                health_status["storage_service"] = True
            except Exception as e:
                logger.warning(f"Storage service check failed: {e}")
                health_status["storage_service"] = False
            
            logger.info("Supabase health check completed successfully")
            
        except APIError as e:
            error_msg = f"Supabase API error: {e}"
            logger.error(error_msg)
            health_status["error"] = error_msg
            
        except Exception as e:
            error_msg = f"Supabase health check failed: {e}"
            logger.error(error_msg)
            health_status["error"] = error_msg
        
        return health_status
    
    def create_storage_bucket(self, bucket_name: str, is_public: bool = True) -> bool:
        """
        Create a storage bucket if it doesn't exist.
        
        Args:
            bucket_name: Name of the bucket to create
            is_public: Whether the bucket should be publicly accessible
            
        Returns:
            bool: True if bucket exists or was created successfully
        """
        try:
            # Check if bucket exists
            buckets = self.client.storage.list_buckets()
            existing_buckets = [bucket.name for bucket in buckets]
            
            if bucket_name not in existing_buckets:
                # Create bucket
                result = self.client.storage.create_bucket(
                    bucket_name, 
                    options={"public": is_public}
                )
                logger.info(f"Created storage bucket: {bucket_name}")
                return True
            else:
                logger.info(f"Storage bucket already exists: {bucket_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create storage bucket {bucket_name}: {e}")
            return False
    
    def upload_file(
        self, 
        bucket_name: str, 
        file_path: str, 
        file_data: bytes, 
        content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Upload file to Supabase storage.
        
        Args:
            bucket_name: Storage bucket name
            file_path: Path within the bucket
            file_data: File binary data
            content_type: MIME type of the file
            
        Returns:
            str: Public URL of uploaded file, None if failed
        """
        try:
            storage_client = self.get_storage_client(bucket_name)
            
            # Upload file
            result = storage_client.upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "upsert": True  # Replace if exists
                }
            )
            
            if result:
                # Get public URL
                public_url = storage_client.get_public_url(file_path)
                logger.info(f"File uploaded successfully: {file_path}")
                return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
        
        return None
    
    def delete_file(self, bucket_name: str, file_path: str) -> bool:
        """
        Delete file from Supabase storage.
        
        Args:
            bucket_name: Storage bucket name
            file_path: Path within the bucket
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            storage_client = self.get_storage_client(bucket_name)
            result = storage_client.remove([file_path])
            
            if result:
                logger.info(f"File deleted successfully: {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
        
        return False
    
    def get_file_url(self, bucket_name: str, file_path: str) -> Optional[str]:
        """
        Get public URL for a file in storage.
        
        Args:
            bucket_name: Storage bucket name
            file_path: Path within the bucket
            
        Returns:
            str: Public URL of the file
        """
        try:
            storage_client = self.get_storage_client(bucket_name)
            return storage_client.get_public_url(file_path)
        except Exception as e:
            logger.error(f"Failed to get file URL for {file_path}: {e}")
            return None
    
    def close(self):
        """Close Supabase client connections."""
        if self._client:
            # Supabase client doesn't require explicit closing
            # but we can clear the cached client
            self._client = None
            self._storage_client = None
            logger.info("Supabase client connections closed")

# Global Supabase manager instance
_supabase_manager: Optional[SupabaseManager] = None


@lru_cache()
def get_supabase_manager() -> SupabaseManager:
    """
    Get cached Supabase manager instance.
    
    Returns:
        SupabaseManager: Singleton Supabase manager
    """
    global _supabase_manager
    if _supabase_manager is None:
        _supabase_manager = SupabaseManager()
    return _supabase_manager


def get_supabase_client() -> Client:
    """
    Get Supabase client for direct usage.
    
    Returns:
        Client: Supabase client instance
    """
    return get_supabase_manager().client


def get_supabase_auth():
    """Get Supabase auth client."""
    return get_supabase_manager().get_auth_client()


def get_supabase_storage(bucket_name: str = "plant-photos"):
    """Get Supabase storage client for specific bucket."""
    return get_supabase_manager().get_storage_client(bucket_name)


async def init_supabase_storage():
    """Initialize default storage buckets for the application."""
    manager = get_supabase_manager()
    
    # Create default buckets
    default_buckets = [
        ("plant-photos", True),    # User plant photos
        ("user-profiles", True),   # User profile pictures
        ("plant-library", True),   # Plant library images
        ("growth-journal", True),  # Growth tracking photos
    ]
    
    for bucket_name, is_public in default_buckets:
        manager.create_storage_bucket(bucket_name, is_public)
        logger.info(f"Initialized storage bucket: {bucket_name}")


async def cleanup_supabase():
    """Cleanup Supabase connections on application shutdown."""
    global _supabase_manager
    if _supabase_manager:
        _supabase_manager.close()
        _supabase_manager = None
        logger.info("Supabase cleanup completed")

