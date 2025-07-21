# 📄 File: app/shared/infrastructure/storage/supabase_storage.py

# 🧭 Purpose (Layman Explanation):
# This file handles uploading and downloading files (like plant photos) to cloud storage,
# organizing them in folders and making sure they're accessible when needed.

# 🧪 Purpose (Technical Summary):
# Implements Supabase Storage client wrapper with file upload/download, bucket management,
# image optimization, path organization, and comprehensive error handling for plant care app assets.

# 🔗 Dependencies:
# - supabase: Storage client and auth
# - PIL (Pillow): Image processing and optimization
# - asyncio: Async file operations
# - typing: Type annotations
# - pathlib: Path handling

# 🔄 Connected Modules / Calls From:
# Called by: file_manager.py, plant photo uploads, user profile images, growth journal photos
# Connects to: Supabase cloud storage, image optimization pipeline, file validation system

import asyncio
import io
import logging
import mimetypes
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from uuid import uuid4

from PIL import Image, ImageOps
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from app.shared.config.settings import get_settings
from app.shared.core.exceptions import (
    StorageError,
    FileNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
    StorageQuotaExceededError
)
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SupabaseStorageClient:
    """
    Comprehensive Supabase Storage client for the Plant Care Application.
    
    Handles all file operations including:
    - Image uploads with optimization
    - File downloads and URL generation
    - Bucket management and organization
    - Security and access control
    - Storage quota management
    """
    
    def __init__(self):
        """Initialize Supabase Storage client with configuration."""
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_SERVICE_KEY
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET
        
        # Initialize Supabase client
        self.client: Optional[Client] = None
        self.storage = None
        
        # Image optimization settings
        self.image_quality = 85
        self.max_image_size = (2048, 2048)  # Max width, height
        self.thumbnail_size = (300, 300)
        
        # File size limits (in bytes)
        self.max_file_sizes = {
            'image': 10 * 1024 * 1024,  # 10MB for images
            'document': 5 * 1024 * 1024,  # 5MB for documents
            'video': 50 * 1024 * 1024,  # 50MB for videos
        }
        
        # Allowed file types
        self.allowed_image_types = {
            'image/jpeg', 'image/png', 'image/webp', 'image/gif'
        }
        self.allowed_document_types = {
            'application/pdf', 'text/plain', 'application/json'
        }
        
        # Storage paths
        self.storage_paths = {
            'plants': 'plants/{user_id}/{plant_id}',
            'profiles': 'profiles/{user_id}',
            'growth': 'growth/{user_id}/{plant_id}',
            'health': 'health/{user_id}/{plant_id}',
            'community': 'community/{user_id}',
            'temp': 'temp/{user_id}'
        }
    
    async def initialize(self) -> None:
        """Initialize the Supabase client and storage."""
        try:
            # Create Supabase client
            self.client = create_client(
                self.supabase_url,
                self.supabase_key,
                options=ClientOptions(
                    postgrest_client_timeout=10,
                    storage_client_timeout=30
                )
            )
            
            self.storage = self.client.storage
            
            # Ensure main bucket exists
            await self._ensure_bucket_exists()
            
            logger.info("Supabase Storage client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase Storage: {e}")
            raise StorageError(f"Storage initialization failed: {e}")
    
    async def _ensure_bucket_exists(self) -> None:
        """Ensure the main storage bucket exists."""
        try:
            # Check if bucket exists
            buckets = self.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.bucket_name not in bucket_names:
                # Create bucket if it doesn't exist
                self.storage.create_bucket(
                    self.bucket_name,
                    options={
                        "public": False,
                        "file_size_limit": 52428800,  # 50MB
                        "allowed_mime_types": list(
                            self.allowed_image_types | self.allowed_document_types
                        )
                    }
                )
                logger.info(f"Created storage bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise StorageError(f"Bucket setup failed: {e}")
    
    def _generate_file_path(
        self,
        category: str,
        user_id: str,
        filename: str,
        plant_id: Optional[str] = None,
        subfolder: Optional[str] = None
    ) -> str:
        """Generate organized file path based on category and parameters."""
        # Get base path template
        if category not in self.storage_paths:
            raise ValueError(f"Unknown storage category: {category}")
        
        path_template = self.storage_paths[category]
        
        # Format path with provided parameters
        if plant_id:
            base_path = path_template.format(user_id=user_id, plant_id=plant_id)
        else:
            base_path = path_template.format(user_id=user_id)
        
        # Add subfolder if provided
        if subfolder:
            base_path = f"{base_path}/{subfolder}"
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_uuid = str(uuid4())[:8]
        
        # Get file extension
        file_ext = Path(filename).suffix.lower()
        if not file_ext:
            file_ext = '.jpg'  # Default for images
        
        # Construct final filename
        final_filename = f"{timestamp}_{file_uuid}{file_ext}"
        
        return f"{base_path}/{final_filename}"
    
    def _validate_file(self, file_data: bytes, file_type: str, filename: str) -> None:
        """Validate file size, type, and content."""
        # Check file size
        file_size = len(file_data)
        category = self._get_file_category(filename)
        max_size = self.max_file_sizes.get(category, self.max_file_sizes['image'])
        
        if file_size > max_size:
            raise FileTooLargeError(
                f"File size {file_size} exceeds maximum {max_size} bytes"
            )
        
        # Check MIME type
        if file_type not in (self.allowed_image_types | self.allowed_document_types):
            raise InvalidFileTypeError(f"File type {file_type} not allowed")
        
        # Additional validation for images
        if file_type in self.allowed_image_types:
            try:
                with Image.open(io.BytesIO(file_data)) as img:
                    # Verify it's a valid image
                    img.verify()
            except Exception as e:
                raise InvalidFileTypeError(f"Invalid image file: {e}")
    
    def _get_file_category(self, filename: str) -> str:
        """Determine file category based on extension."""
        ext = Path(filename).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            return 'image'
        elif ext in ['.pdf', '.txt', '.json']:
            return 'document'
        elif ext in ['.mp4', '.mov', '.avi']:
            return 'video'
        else:
            return 'image'  # Default to image
    
    async def _optimize_image(
        self,
        image_data: bytes,
        optimize_for: str = 'upload'
    ) -> Tuple[bytes, Dict[str, any]]:
        """
        Optimize image for storage with compression and resizing.
        
        Args:
            image_data: Original image bytes
            optimize_for: 'upload' for full size, 'thumbnail' for small size
        
        Returns:
            Tuple of (optimized_bytes, metadata)
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Get original dimensions
                original_size = img.size
                
                # Determine target size
                if optimize_for == 'thumbnail':
                    target_size = self.thumbnail_size
                    quality = 80
                else:
                    target_size = self.max_image_size
                    quality = self.image_quality
                
                # Resize if necessary (maintain aspect ratio)
                if img.size[0] > target_size[0] or img.size[1] > target_size[1]:
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Save optimized image
                output = io.BytesIO()
                img.save(
                    output,
                    format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True
                )
                
                optimized_data = output.getvalue()
                
                # Generate metadata
                metadata = {
                    'original_size': original_size,
                    'optimized_size': img.size,
                    'original_bytes': len(image_data),
                    'optimized_bytes': len(optimized_data),
                    'compression_ratio': len(optimized_data) / len(image_data),
                    'format': 'JPEG',
                    'quality': quality
                }
                
                return optimized_data, metadata
                
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            # Return original if optimization fails
            return image_data, {'error': str(e)}
    
    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        filename: str,
        category: str,
        user_id: str,
        plant_id: Optional[str] = None,
        subfolder: Optional[str] = None,
        optimize_image: bool = True,
        generate_thumbnail: bool = False
    ) -> Dict[str, any]:
        """
        Upload file to Supabase Storage with optimization.
        
        Args:
            file_data: File data as bytes or file-like object
            filename: Original filename
            category: Storage category (plants, profiles, growth, etc.)
            user_id: User ID for path organization
            plant_id: Plant ID if applicable
            subfolder: Additional subfolder
            optimize_image: Whether to optimize images
            generate_thumbnail: Whether to generate thumbnail
        
        Returns:
            Dict with upload results and metadata
        """
        try:
            # Convert file data to bytes if needed
            if hasattr(file_data, 'read'):
                file_bytes = file_data.read()
            else:
                file_bytes = file_data
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Validate file
            self._validate_file(file_bytes, mime_type, filename)
            
            # Generate storage path
            storage_path = self._generate_file_path(
                category, user_id, filename, plant_id, subfolder
            )
            
            upload_results = {}
            
            # Process image optimization if applicable
            if mime_type in self.allowed_image_types and optimize_image:
                optimized_data, optimization_metadata = await self._optimize_image(
                    file_bytes, 'upload'
                )
                upload_data = optimized_data
                upload_results['optimization'] = optimization_metadata
            else:
                upload_data = file_bytes
            
            # Upload main file
            upload_response = self.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=upload_data,
                file_options={
                    "content-type": mime_type,
                    "cache-control": "3600",
                    "upsert": False
                }
            )
            
            if upload_response.get('error'):
                raise StorageError(f"Upload failed: {upload_response['error']}")
            
            # Generate thumbnail if requested
            thumbnail_path = None
            if generate_thumbnail and mime_type in self.allowed_image_types:
                thumbnail_data, thumb_metadata = await self._optimize_image(
                    file_bytes, 'thumbnail'
                )
                
                thumbnail_path = storage_path.replace(
                    Path(storage_path).suffix,
                    f"_thumb{Path(storage_path).suffix}"
                )
                
                thumb_response = self.storage.from_(self.bucket_name).upload(
                    path=thumbnail_path,
                    file=thumbnail_data,
                    file_options={
                        "content-type": mime_type,
                        "cache-control": "3600"
                    }
                )
                
                if not thumb_response.get('error'):
                    upload_results['thumbnail'] = {
                        'path': thumbnail_path,
                        'metadata': thumb_metadata
                    }
            
            # Get public URL
            public_url = self.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            # Compile upload results
            upload_results.update({
                'success': True,
                'path': storage_path,
                'public_url': public_url,
                'thumbnail_path': thumbnail_path,
                'file_size': len(upload_data),
                'original_filename': filename,
                'mime_type': mime_type,
                'category': category,
                'uploaded_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"File uploaded successfully: {storage_path}")
            return upload_results
            
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise StorageError(f"Upload failed: {e}")
    
    async def download_file(self, file_path: str) -> bytes:
        """Download file from storage."""
        try:
            response = self.storage.from_(self.bucket_name).download(file_path)
            
            if isinstance(response, bytes):
                return response
            else:
                raise FileNotFoundError(f"File not found: {file_path}")
                
        except Exception as e:
            logger.error(f"File download failed: {e}")
            raise StorageError(f"Download failed: {e}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage."""
        try:
            response = self.storage.from_(self.bucket_name).remove([file_path])
            
            if response and not response[0].get('error'):
                logger.info(f"File deleted successfully: {file_path}")
                return True
            else:
                logger.error(f"Failed to delete file: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return False
    
    async def get_file_url(
        self,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        """Generate signed URL for private file access."""
        try:
            if expires_in > 0:
                # Generate signed URL for temporary access
                response = self.storage.from_(self.bucket_name).create_signed_url(
                    file_path, expires_in
                )
                return response.get('signedURL', '')
            else:
                # Get public URL
                return self.storage.from_(self.bucket_name).get_public_url(file_path)
                
        except Exception as e:
            logger.error(f"URL generation failed: {e}")
            raise StorageError(f"URL generation failed: {e}")
    
    async def list_files(
        self,
        folder_path: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, any]]:
        """List files in a folder."""
        try:
            response = self.storage.from_(self.bucket_name).list(
                path=folder_path,
                limit=limit,
                offset=offset
            )
            
            files = []
            for item in response:
                files.append({
                    'name': item['name'],
                    'path': f"{folder_path}/{item['name']}",
                    'size': item.get('metadata', {}).get('size', 0),
                    'last_modified': item.get('updated_at'),
                    'mime_type': item.get('metadata', {}).get('mimetype')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"File listing failed: {e}")
            return []
    
    async def get_storage_usage(self, user_id: str) -> Dict[str, any]:
        """Get storage usage statistics for a user."""
        try:
            usage_stats = {
                'total_bytes': 0,
                'file_count': 0,
                'categories': {}
            }
            
            # Check each category
            for category, path_template in self.storage_paths.items():
                if category == 'temp':
                    continue
                
                try:
                    folder_path = path_template.format(user_id=user_id).split('/')[0:2]
                    folder_path = '/'.join(folder_path)
                    
                    files = await self.list_files(folder_path)
                    
                    category_bytes = sum(file.get('size', 0) for file in files)
                    category_count = len(files)
                    
                    usage_stats['categories'][category] = {
                        'bytes': category_bytes,
                        'count': category_count
                    }
                    
                    usage_stats['total_bytes'] += category_bytes
                    usage_stats['file_count'] += category_count
                    
                except Exception as cat_error:
                    logger.warning(f"Failed to get usage for category {category}: {cat_error}")
                    usage_stats['categories'][category] = {'bytes': 0, 'count': 0}
            
            return usage_stats
            
        except Exception as e:
            logger.error(f"Storage usage calculation failed: {e}")
            return {'total_bytes': 0, 'file_count': 0, 'categories': {}}
    
    async def cleanup_temp_files(self, user_id: str, older_than_hours: int = 24) -> int:
        """Clean up temporary files older than specified hours."""
        try:
            temp_path = self.storage_paths['temp'].format(user_id=user_id)
            temp_files = await self.list_files(temp_path)
            
            cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
            deleted_count = 0
            
            for file_info in temp_files:
                if file_info.get('last_modified'):
                    file_time = datetime.fromisoformat(
                        file_info['last_modified'].replace('Z', '+00:00')
                    ).replace(tzinfo=None)
                    
                    if file_time < cutoff_time:
                        if await self.delete_file(file_info['path']):
                            deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} temporary files for user {user_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}")
            return 0
    
    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """Move file from one location to another."""
        try:
            # Download source file
            file_data = await self.download_file(source_path)
            
            # Upload to destination
            upload_response = self.storage.from_(self.bucket_name).upload(
                path=destination_path,
                file=file_data,
                file_options={"upsert": True}
            )
            
            if not upload_response.get('error'):
                # Delete source file
                await self.delete_file(source_path)
                logger.info(f"File moved: {source_path} -> {destination_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"File move failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, any]:
        """Perform storage health check."""
        try:
            # Try to list buckets
            buckets = self.storage.list_buckets()
            
            # Try a simple operation
            test_path = f"health_check/{datetime.utcnow().isoformat()}.txt"
            test_data = b"health_check"
            
            upload_response = self.storage.from_(self.bucket_name).upload(
                path=test_path,
                file=test_data
            )
            
            # Clean up test file
            if not upload_response.get('error'):
                await self.delete_file(test_path)
            
            return {
                'status': 'healthy',
                'bucket_accessible': True,
                'upload_working': not upload_response.get('error'),
                'buckets_count': len(buckets),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Global storage client instance
storage_client: Optional[SupabaseStorageClient] = None


async def get_storage_client() -> SupabaseStorageClient:
    """Get initialized storage client (dependency injection)."""
    global storage_client
    
    if storage_client is None:
        storage_client = SupabaseStorageClient()
        await storage_client.initialize()
    
    return storage_client


async def cleanup_storage_client():
    """Clean up storage client resources."""
    global storage_client
    if storage_client:
        # Perform any cleanup if needed
        storage_client = None
        logger.info("Storage client cleaned up")


# Utility functions for common operations
async def upload_plant_photo(
    file_data: bytes,
    filename: str,
    user_id: str,
    plant_id: str,
    subfolder: str = "photos"
) -> Dict[str, any]:
    """Upload plant photo with optimization."""
    client = await get_storage_client()
    return await client.upload_file(
        file_data=file_data,
        filename=filename,
        category="plants",
        user_id=user_id,
        plant_id=plant_id,
        subfolder=subfolder,
        optimize_image=True,
        generate_thumbnail=True
    )


async def upload_profile_photo(
    file_data: bytes,
    filename: str,
    user_id: str
) -> Dict[str, any]:
    """Upload user profile photo."""
    client = await get_storage_client()
    return await client.upload_file(
        file_data=file_data,
        filename=filename,
        category="profiles",
        user_id=user_id,
        optimize_image=True,
        generate_thumbnail=True
    )


async def upload_growth_journal_photo(
    file_data: bytes,
    filename: str,
    user_id: str,
    plant_id: str
) -> Dict[str, any]:
    """Upload growth journal photo."""
    client = await get_storage_client()
    return await client.upload_file(
        file_data=file_data,
        filename=filename,
        category="growth",
        user_id=user_id,
        plant_id=plant_id,
        optimize_image=True,
        generate_thumbnail=True
    )