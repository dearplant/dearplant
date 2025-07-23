# 📄 File: app/shared/infrastructure/storage/file_manager.py

# 🧭 Purpose (Layman Explanation):
# This file acts like a smart file organizer that knows how to handle different types of files
# (photos, documents) with proper organization, security checks, and automatic processing.

# 🧪 Purpose (Technical Summary):
# High-level file management service that orchestrates file operations, validation, processing,
# and organization while providing a clean interface for modules to handle file uploads/downloads.

# 🔗 Dependencies:
# - supabase_storage: Storage client operations
# - PIL: Image validation and metadata extraction
# - magic: File type detection
# - hashlib: File integrity checking
# - asyncio: Async file processing

# 🔄 Connected Modules / Calls From:
# Called by: Plant management (plant photos), User profiles (avatars), Growth tracking (journal photos),
# Health monitoring (diagnosis photos), Community posts (shared images)

import asyncio
import hashlib
import io
import mimetypes
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from uuid import uuid4

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

from PIL import Image
from PIL.ExifTags import TAGS

from app.shared.core.exceptions import (
    FileProcessingError,
    InvalidFileTypeError,
    FileTooLargeError,
    FileIntegrityError,
    FileStorageError
)
from app.shared.infrastructure.storage.supabase_storage import (
    get_storage_client,
    SupabaseStorageClient
)
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class FileManager:
    """
    High-level file management service for the Plant Care Application.
    
    Provides comprehensive file handling including:
    - File validation and security checks
    - Metadata extraction and processing
    - Organized storage management
    - File lifecycle management
    - Integration with storage backend
    """
    
    def __init__(self):
        """Initialize file manager with configuration."""
        self.storage_client: Optional[SupabaseStorageClient] = None
        
        # File validation settings
        self.max_files_per_upload = 10
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        self.supported_document_formats = {'.pdf', '.txt', '.json', '.csv'}
        
        # Security settings
        self.scan_files_for_malware = True
        self.extract_exif_data = True
        self.generate_checksums = True
        
        # Processing settings
        self.auto_optimize_images = True
        self.generate_thumbnails = True
        self.extract_metadata = True
        
        # File organization settings
        self.organize_by_date = True
        self.organize_by_type = True
        
        # Cache for file metadata
        self._metadata_cache = {}
    
    async def initialize(self) -> None:
        """Initialize file manager and dependencies."""
        try:
            self.storage_client = await get_storage_client()
            logger.info("File manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize file manager: {e}")
            raise FileProcessingError(f"File manager initialization failed: {e}")
    
    async def upload_files(
        self,
        files: List[Dict[str, any]],
        category: str,
        user_id: str,
        plant_id: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None
    ) -> Dict[str, any]:
        """
        Upload multiple files with comprehensive processing.
        
        Args:
            files: List of file dictionaries with 'data', 'filename', and optional 'metadata'
            category: File category (plants, profiles, growth, health, community)
            user_id: User ID for organization
            plant_id: Plant ID if applicable
            metadata: Additional metadata to attach
        
        Returns:
            Dict with upload results, processed files info, and any errors
        """
        if not self.storage_client:
            await self.initialize()
        
        # Validate input
        if len(files) > self.max_files_per_upload:
            raise FileTooLargeError(
                f"Too many files: {len(files)} (max: {self.max_files_per_upload})"
            )
        
        upload_results = {
            'success': [],
            'failed': [],
            'total_files': len(files),
            'total_size': 0,
            'processing_time': 0,
            'metadata': metadata or {}
        }
        
        start_time = datetime.utcnow()
        
        # Process files concurrently (in batches to avoid overwhelming storage)
        batch_size = 3
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            # Process batch
            batch_results = await asyncio.gather(
                *[
                    self._process_single_file(
                        file_data=file_item['data'],
                        filename=file_item['filename'],
                        category=category,
                        user_id=user_id,
                        plant_id=plant_id,
                        file_metadata=file_item.get('metadata', {})
                    )
                    for file_item in batch
                ],
                return_exceptions=True
            )
            
            # Collect results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    upload_results['failed'].append({
                        'filename': batch[j]['filename'],
                        'error': str(result),
                        'error_type': type(result).__name__
                    })
                else:
                    upload_results['success'].append(result)
                    upload_results['total_size'] += result.get('file_size', 0)
        
        # Calculate processing time
        upload_results['processing_time'] = (
            datetime.utcnow() - start_time
        ).total_seconds()
        
        # Log results
        logger.info(
            f"File upload completed: {len(upload_results['success'])} successful, "
            f"{len(upload_results['failed'])} failed, "
            f"total size: {upload_results['total_size']} bytes"
        )
        
        return upload_results
    
    async def _process_single_file(
        self,
        file_data: Union[bytes, BinaryIO],
        filename: str,
        category: str,
        user_id: str,
        plant_id: Optional[str] = None,
        file_metadata: Optional[Dict[str, any]] = None
    ) -> Dict[str, any]:
        """Process and upload a single file with full validation and metadata extraction."""
        try:
            # Convert to bytes if needed
            if hasattr(file_data, 'read'):
                file_bytes = file_data.read()
            else:
                file_bytes = file_data
            
            # Basic validation
            await self._validate_file(file_bytes, filename)
            
            # Extract metadata
            extracted_metadata = await self._extract_file_metadata(file_bytes, filename)
            
            # Merge metadata
            combined_metadata = {
                **extracted_metadata,
                **(file_metadata or {}),
                'processed_at': datetime.utcnow().isoformat(),
                'processor_version': '1.0'
            }
            
            # Security checks
            await self._security_scan(file_bytes, filename)
            
            # Determine subfolder based on file type and metadata
            subfolder = self._determine_subfolder(filename, combined_metadata)
            
            # Upload file
            upload_result = await self.storage_client.upload_file(
                file_data=file_bytes,
                filename=filename,
                category=category,
                user_id=user_id,
                plant_id=plant_id,
                subfolder=subfolder,
                optimize_image=self.auto_optimize_images,
                generate_thumbnail=self.generate_thumbnails
            )
            
            # Add extracted metadata to result
            upload_result['extracted_metadata'] = combined_metadata
            
            # Cache metadata for future reference
            self._metadata_cache[upload_result['path']] = combined_metadata
            
            return upload_result
            
        except Exception as e:
            logger.error(f"Failed to process file {filename}: {e}")
            raise FileProcessingError(f"File processing failed: {e}")
    
    async def _validate_file(self, file_data: bytes, filename: str) -> None:
        """Comprehensive file validation."""
        # Check file size
        if len(file_data) == 0:
            raise InvalidFileTypeError("File is empty")
        
        # Check filename
        if not filename or '..' in filename or filename.startswith('/'):
            raise InvalidFileTypeError("Invalid filename")
        
        # Get file extension
        file_ext = Path(filename).suffix.lower()
        
        # Validate file type by extension
        if file_ext not in (self.supported_image_formats | self.supported_document_formats):
            raise InvalidFileTypeError(f"Unsupported file type: {file_ext}")
        
        # Validate MIME type if magic is available
        if HAS_MAGIC:
            try:
                detected_mime = magic.from_buffer(file_data, mime=True)
                expected_mimes = self._get_expected_mime_types(file_ext)
                
                if detected_mime not in expected_mimes:
                    logger.warning(
                        f"MIME type mismatch: detected {detected_mime}, "
                        f"expected one of {expected_mimes}"
                    )
            except Exception as e:
                logger.warning(f"MIME type detection failed: {e}")
        
        # Additional validation for images
        if file_ext in self.supported_image_formats:
            await self._validate_image(file_data)
    
    def _get_expected_mime_types(self, file_ext: str) -> List[str]:
        """Get expected MIME types for file extension."""
        mime_map = {
            '.jpg': ['image/jpeg'],
            '.jpeg': ['image/jpeg'],
            '.png': ['image/png'],
            '.webp': ['image/webp'],
            '.gif': ['image/gif'],
            '.pdf': ['application/pdf'],
            '.txt': ['text/plain'],
            '.json': ['application/json'],
            '.csv': ['text/csv', 'application/csv']
        }
        return mime_map.get(file_ext, [])
    
    async def _validate_image(self, image_data: bytes) -> None:
        """Validate image file integrity and properties."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Verify image
                img.verify()
                
                # Re-open for additional checks (verify() closes the image)
                img = Image.open(io.BytesIO(image_data))
                
                # Check image dimensions
                width, height = img.size
                if width < 10 or height < 10:
                    raise InvalidFileTypeError("Image too small")
                
                if width > 10000 or height > 10000:
                    raise InvalidFileTypeError("Image too large")
                
                # Check for reasonable aspect ratio
                aspect_ratio = max(width, height) / min(width, height)
                if aspect_ratio > 10:
                    logger.warning(f"Unusual aspect ratio: {aspect_ratio}")
                
        except Exception as e:
            if isinstance(e, InvalidFileTypeError):
                raise
            raise InvalidFileTypeError(f"Invalid image file: {e}")
    
    async def _extract_file_metadata(
        self,
        file_data: bytes,
        filename: str
    ) -> Dict[str, any]:
        """Extract comprehensive metadata from file."""
        metadata = {
            'filename': filename,
            'size_bytes': len(file_data),
            'file_extension': Path(filename).suffix.lower(),
            'mime_type': mimetypes.guess_type(filename)[0],
            'checksum': await self._calculate_checksum(file_data) if self.generate_checksums else None
        }
        
        # Extract image-specific metadata
        if metadata['file_extension'] in self.supported_image_formats:
            image_metadata = await self._extract_image_metadata(file_data)
            metadata.update(image_metadata)
        
        return metadata
    
    async def _extract_image_metadata(self, image_data: bytes) -> Dict[str, any]:
        """Extract detailed metadata from image files."""
        metadata = {}
        
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Basic image properties
                metadata.update({
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                })
                
                # Extract EXIF data if available and enabled
                if self.extract_exif_data and hasattr(img, '_getexif'):
                    exif_data = img._getexif()
                    if exif_data:
                        exif_metadata = {}
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            # Only include safe, non-sensitive EXIF data
                            if tag in [
                                'DateTime', 'DateTimeOriginal', 'Make', 'Model',
                                'Orientation', 'XResolution', 'YResolution',
                                'Flash', 'FocalLength', 'ExposureTime', 'FNumber'
                            ]:
                                exif_metadata[tag] = str(value)
                        
                        if exif_metadata:
                            metadata['exif'] = exif_metadata
                
                # Calculate additional properties
                metadata['aspect_ratio'] = round(img.width / img.height, 2)
                metadata['megapixels'] = round((img.width * img.height) / 1000000, 2)
                
        except Exception as e:
            logger.warning(f"Failed to extract image metadata: {e}")
            metadata['extraction_error'] = str(e)
        
        return metadata
    
    async def _calculate_checksum(self, file_data: bytes) -> str:
        """Calculate SHA-256 checksum for file integrity."""
        return hashlib.sha256(file_data).hexdigest()
    
    async def _security_scan(self, file_data: bytes, filename: str) -> None:
        """Perform security scanning on file."""
        if not self.scan_files_for_malware:
            return
        
        try:
            # Basic security checks
            
            # Check for suspicious file headers
            suspicious_headers = [
                b'MZ',  # PE executable
                b'\x7fELF',  # ELF executable
                b'<!DOCTYPE html',  # HTML (potential XSS)
                b'<script',  # JavaScript
                b'<?php',  # PHP code
            ]
            
            file_start = file_data[:100].lower()
            for header in suspicious_headers:
                if header.lower() in file_start:
                    logger.warning(f"Suspicious file header detected in {filename}")
                    break
            
            # Check for embedded scripts in images
            if Path(filename).suffix.lower() in self.supported_image_formats:
                suspicious_strings = [b'<script', b'javascript:', b'data:', b'<?php']
                for string in suspicious_strings:
                    if string in file_data.lower():
                        logger.warning(f"Suspicious content detected in image {filename}")
                        break
            
        except Exception as e:
            logger.warning(f"Security scan failed for {filename}: {e}")
    
    def _determine_subfolder(
        self,
        filename: str,
        metadata: Dict[str, any]
    ) -> str:
        """Determine appropriate subfolder for file organization."""
        subfolders = []
        
        # Organize by file type
        if self.organize_by_type:
            file_ext = Path(filename).suffix.lower()
            if file_ext in self.supported_image_formats:
                subfolders.append('images')
            elif file_ext in self.supported_document_formats:
                subfolders.append('documents')
            else:
                subfolders.append('misc')
        
        # Organize by date
        if self.organize_by_date:
            today = datetime.utcnow()
            subfolders.append(f"{today.year}/{today.month:02d}")
        
        return '/'.join(subfolders) if subfolders else ''
    
    async def download_file(
        self,
        file_path: str,
        include_metadata: bool = False
    ) -> Union[bytes, Dict[str, any]]:
        """Download file with optional metadata."""
        if not self.storage_client:
            await self.initialize()
        
        try:
            file_data = await self.storage_client.download_file(file_path)
            
            if include_metadata:
                # Get cached metadata or extract fresh
                metadata = self._metadata_cache.get(file_path)
                if not metadata:
                    filename = Path(file_path).name
                    metadata = await self._extract_file_metadata(file_data, filename)
                    self._metadata_cache[file_path] = metadata
                
                return {
                    'data': file_data,
                    'metadata': metadata,
                    'path': file_path
                }
            
            return file_data
            
        except Exception as e:
            logger.error(f"Failed to download file {file_path}: {e}")
            raise FileProcessingError(f"Download failed: {e}")
    
    async def delete_files(
        self,
        file_paths: List[str],
        user_id: str
    ) -> Dict[str, any]:
        """Delete multiple files with proper authorization."""
        if not self.storage_client:
            await self.initialize()
        
        results = {
            'deleted': [],
            'failed': [],
            'total_files': len(file_paths)
        }
        
        for file_path in file_paths:
            try:
                # Verify user owns the file (security check)
                if not self._verify_file_ownership(file_path, user_id):
                    results['failed'].append({
                        'path': file_path,
                        'error': 'Unauthorized access'
                    })
                    continue
                
                # Delete file
                success = await self.storage_client.delete_file(file_path)
                
                if success:
                    results['deleted'].append(file_path)
                    # Remove from cache
                    self._metadata_cache.pop(file_path, None)
                else:
                    results['failed'].append({
                        'path': file_path,
                        'error': 'Deletion failed'
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'path': file_path,
                    'error': str(e)
                })
        
        logger.info(
            f"File deletion completed: {len(results['deleted'])} deleted, "
            f"{len(results['failed'])} failed"
        )
        
        return results
    
    def _verify_file_ownership(self, file_path: str, user_id: str) -> bool:
        """Verify that user owns the file (basic path-based check)."""
        # Simple check - ensure user_id is in the file path
        return user_id in file_path
    
    async def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get comprehensive file information."""
        if not self.storage_client:
            await self.initialize()
        
        try:
            # Get metadata from cache or extract
            metadata = self._metadata_cache.get(file_path)
            
            if not metadata:
                # Download file to extract metadata
                file_data = await self.storage_client.download_file(file_path)
                filename = Path(file_path).name
                metadata = await self._extract_file_metadata(file_data, filename)
                self._metadata_cache[file_path] = metadata
            
            # Get storage info
            file_url = await self.storage_client.get_file_url(file_path)
            
            return {
                'path': file_path,
                'url': file_url,
                'metadata': metadata,
                'cached': file_path in self._metadata_cache
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            raise FileProcessingError(f"File info retrieval failed: {e}")
    
    async def organize_user_files(self, user_id: str) -> Dict[str, any]:
        """Organize all files for a user according to current rules."""
        if not self.storage_client:
            await self.initialize()
        
        try:
            reorganization_results = {
                'moved': [],
                'failed': [],
                'total_processed': 0
            }
            
            # This would be a more complex operation to reorganize existing files
            # Implementation would depend on specific reorganization needs
            
            logger.info(f"File organization completed for user {user_id}")
            return reorganization_results
            
        except Exception as e:
            logger.error(f"File organization failed for user {user_id}: {e}")
            raise FileProcessingError(f"File organization failed: {e}")
    
    async def cleanup_expired_files(self, days_old: int = 30) -> int:
        """Clean up expired temporary and orphaned files."""
        if not self.storage_client:
            await self.initialize()
        
        try:
            cleanup_count = 0
            
            # This would implement cleanup logic for expired files
            # Would need to integrate with storage client's cleanup methods
            
            logger.info(f"Cleaned up {cleanup_count} expired files")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"File cleanup failed: {e}")
            return 0
    
    async def get_storage_statistics(self, user_id: str) -> Dict[str, any]:
        """Get comprehensive storage statistics for user."""
        if not self.storage_client:
            await self.initialize()
        
        try:
            # Get basic usage stats
            usage_stats = await self.storage_client.get_storage_usage(user_id)
            
            # Add file manager specific stats
            stats = {
                **usage_stats,
                'cache_entries': len(self._metadata_cache),
                'supported_formats': {
                    'images': list(self.supported_image_formats),
                    'documents': list(self.supported_document_formats)
                },
                'processing_settings': {
                    'auto_optimize': self.auto_optimize_images,
                    'generate_thumbnails': self.generate_thumbnails,
                    'extract_metadata': self.extract_metadata
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {}


# Global file manager instance
file_manager: Optional[FileManager] = None


async def get_file_manager() -> FileManager:
    """Get initialized file manager (dependency injection)."""
    global file_manager
    
    if file_manager is None:
        file_manager = FileManager()
        await file_manager.initialize()
    
    return file_manager


# Convenience functions for common operations
async def upload_plant_photos(
    photos: List[Dict[str, any]],
    user_id: str,
    plant_id: str
) -> Dict[str, any]:
    """Upload multiple plant photos with processing."""
    manager = await get_file_manager()
    return await manager.upload_files(
        files=photos,
        category="plants",
        user_id=user_id,
        plant_id=plant_id
    )


async def upload_growth_journal_entry(
    photo_data: bytes,
    filename: str,
    user_id: str,
    plant_id: str,
    measurements: Dict[str, any]
) -> Dict[str, any]:
    """Upload growth journal photo with measurements."""
    manager = await get_file_manager()
    return await manager.upload_files(
        files=[{
            'data': photo_data,
            'filename': filename,
            'metadata': {
                'type': 'growth_journal',
                'measurements': measurements,
                'timestamp': datetime.utcnow().isoformat()
            }
        }],
        category="growth",
        user_id=user_id,
        plant_id=plant_id
    )


async def upload_health_diagnosis_photos(
    photos: List[Dict[str, any]],
    user_id: str,
    plant_id: str,
    symptoms: List[str]
) -> Dict[str, any]:
    """Upload health diagnosis photos with symptom data."""
    manager = await get_file_manager()
    
    # Add symptom metadata to each photo
    for photo in photos:
        photo['metadata'] = {
            **photo.get('metadata', {}),
            'type': 'health_diagnosis',
            'symptoms': symptoms,
            'diagnosis_timestamp': datetime.utcnow().isoformat()
        }
    
    return await manager.upload_files(
        files=photos,
        category="health",
        user_id=user_id,
        plant_id=plant_id
    )