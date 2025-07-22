# 📄 File: app/modules/user_management/application/commands/delete_user.py
# 🧭 Purpose (Layman Explanation):
# This file defines the "delete user" command that contains all the information needed
# to safely remove a user account and all related data from our plant care app.
#
# 🧪 Purpose (Technical Summary):
# CQRS command implementation for user account deletion following Core Doc 1.1 Authentication
# specifications with cascade deletion, data cleanup, and security confirmation requirements.
#
# 🔗 Dependencies:
# - pydantic for command validation and serialization
# - app.modules.user_management.domain.models.user (User domain entity)
# - Core doc 1.1 specifications for user deletion and data cleanup
#
# 🔄 Connected Modules / Calls From:
# - app.modules.user_management.application.handlers.command_handlers (DeleteUserCommandHandler)
# - app.modules.user_management.presentation.api.v1.users (user deletion endpoint)
# - app.modules.user_management.presentation.api.schemas.user_schemas (API schema conversion)

"""
Delete User Command

This module implements the CQRS command for user account deletion,
following the exact specifications from Core Doc 1.1 (Authentication)
and ensuring proper data cleanup and security measures.

Command Fields:
- user_id: UUID of the user to delete (required)
- confirmation_token: Security token for deletion confirmation
- password_confirmation: Current password for security verification
- reason: Optional reason for account deletion (for analytics)
- hard_delete: Whether to permanently delete or soft delete (default: soft)

Security Requirements (Core Doc 1.1):
- Password confirmation required for security
- Confirmation token validation
- Account lockout check before deletion
- Audit logging for deletion events
- Cascade deletion of related entities (profile, subscription)

Data Cleanup Operations:
- User entity deletion (users table)
- Profile entity deletion (profiles table) 
- Subscription entity deletion (subscriptions table)
- Session revocation and token cleanup
- External service cleanup (Supabase auth)
- File cleanup (profile photos in Supabase Storage)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class DeletionReason(str, Enum):
    """Enumeration of possible account deletion reasons."""
    USER_REQUEST = "user_request"
    PRIVACY_CONCERNS = "privacy_concerns"
    NOT_USING_APP = "not_using_app"
    FOUND_ALTERNATIVE = "found_alternative"
    TOO_COMPLICATED = "too_complicated"
    PERFORMANCE_ISSUES = "performance_issues"
    ADMIN_DELETION = "admin_deletion"
    SPAM_VIOLATION = "spam_violation"
    TERMS_VIOLATION = "terms_violation"
    OTHER = "other"


class DeleteUserCommand(BaseModel):
    """
    Command for deleting a user account and all related data.
    
    This command encapsulates user deletion data following
    Core Doc 1.1 (Authentication) specifications with proper
    security measures and data cleanup requirements.
    """
    
    # Required identifier
    user_id: UUID = Field(
        ...,
        description="UUID of the user to delete",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    
    # Security confirmation fields (Core Doc 1.1)
    confirmation_token: str = Field(
        ...,
        min_length=32,
        max_length=128,
        description="Security token for deletion confirmation",
        example="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
    )
    password_confirmation: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password for security verification",
        example="CurrentPassword123!"
    )
    
    # Deletion metadata
    reason: Optional[DeletionReason] = Field(
        default=DeletionReason.USER_REQUEST,
        description="Reason for account deletion (for analytics)",
        example=DeletionReason.USER_REQUEST
    )
    reason_details: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional details about deletion reason",
        example="Moving to a different platform for plant care tracking"
    )
    
    # Deletion behavior
    hard_delete: bool = Field(
        default=False,
        description="Whether to permanently delete or soft delete (default: soft)",
        example=False
    )
    immediate_deletion: bool = Field(
        default=False,
        description="Skip grace period and delete immediately",
        example=False
    )
    
    # Cleanup options
    delete_user_data: bool = Field(
        default=True,
        description="Delete user profile and personal data",
        example=True
    )
    delete_subscription_data: bool = Field(
        default=True,
        description="Cancel and delete subscription information",
        example=True
    )
    delete_uploaded_files: bool = Field(
        default=True,
        description="Delete profile photos and uploaded files",
        example=True
    )
    revoke_all_sessions: bool = Field(
        default=True,
        description="Revoke all active sessions and tokens",
        example=True
    )
    
    # Admin fields (when deletion is performed by admin)
    admin_user_id: Optional[UUID] = Field(
        default=None,
        description="UUID of admin performing the deletion (if applicable)",
        example="987fcdeb-51a2-43d1-9876-ba0987654321"
    )
    admin_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Admin reason for deletion (if applicable)",
        example="Account violated terms of service"
    )
    
    # Request metadata
    ip_address: Optional[str] = Field(
        default=None,
        description="IP address for security logging",
        example="192.168.1.100"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="User agent for request tracking",
        example="Mozilla/5.0..."
    )
    
    class Config:
        """Pydantic configuration."""
        # Allow arbitrary types for complex validations
        arbitrary_types_allowed = True
        # Use enum values in schema
        use_enum_values = True
        # Example for API documentation
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "confirmation_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                "password_confirmation": "CurrentPassword123!",
                "reason": "not_using_app",
                "reason_details": "Switching to manual plant care tracking",
                "hard_delete": False,
                "immediate_deletion": False,
                "delete_user_data": True,
                "delete_subscription_data": True,
                "delete_uploaded_files": True,
                "revoke_all_sessions": True,
                "ip_address": "192.168.1.100"
            }
        }
    
    @validator('confirmation_token')
    def validate_confirmation_token(cls, v):
        """
        Validate confirmation token format.
        
        Args:
            v: Confirmation token to validate
            
        Returns:
            str: Validated token
            
        Raises:
            ValueError: If token format is invalid
        """
        # Token should be alphanumeric for security
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Confirmation token must contain only alphanumeric characters, hyphens, and underscores")
        
        return v
    
    @validator('reason_details')
    def validate_reason_details(cls, v):
        """
        Validate reason details length and content.
        
        Args:
            v: Reason details to validate
            
        Returns:
            Optional[str]: Validated reason details
            
        Raises:
            ValueError: If details are too long or contain inappropriate content
        """
        if v is not None:
            # Trim whitespace
            v = v.strip()
            
            # Check length
            if len(v) > 1000:
                raise ValueError("Reason details must not exceed 1000 characters")
            
            # Basic content validation (no malicious content)
            forbidden_chars = ['<', '>', '{', '}', '[', ']']
            if any(char in v for char in forbidden_chars):
                raise ValueError("Reason details contain forbidden characters")
        
        return v
    
    @validator('admin_reason')
    def validate_admin_reason(cls, v):
        """
        Validate admin reason length and content.
        
        Args:
            v: Admin reason to validate
            
        Returns:
            Optional[str]: Validated admin reason
            
        Raises:
            ValueError: If reason is too long
        """
        if v is not None:
            v = v.strip()
            if len(v) > 500:
                raise ValueError("Admin reason must not exceed 500 characters")
        
        return v
    
    def is_admin_deletion(self) -> bool:
        """
        Check if this is an admin-initiated deletion.
        
        Returns:
            bool: True if deletion is performed by admin
        """
        return self.admin_user_id is not None
    
    def requires_password_verification(self) -> bool:
        """
        Check if password verification is required.
        
        Returns:
            bool: True if password verification is needed
        """
        # Admin deletions might skip password verification
        # User-initiated deletions always require password
        return not self.is_admin_deletion()
    
    def get_cleanup_operations(self) -> dict:
        """
        Get the cleanup operations to perform.
        
        Returns:
            dict: Dictionary of cleanup operations and their flags
        """
        return {
            "delete_user_data": self.delete_user_data,
            "delete_subscription_data": self.delete_subscription_data,
            "delete_uploaded_files": self.delete_uploaded_files,
            "revoke_all_sessions": self.revoke_all_sessions,
            "hard_delete": self.hard_delete,
            "immediate_deletion": self.immediate_deletion,
        }
    
    def get_audit_data(self) -> dict:
        """
        Get audit data for deletion logging.
        
        Returns:
            dict: Audit information for security logging
        """
        audit_data = {
            "user_id": str(self.user_id),
            "deletion_type": "hard" if self.hard_delete else "soft",
            "reason": self.reason.value if self.reason else None,
            "reason_details": self.reason_details,
            "immediate": self.immediate_deletion,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add admin information if applicable
        if self.is_admin_deletion():
            audit_data.update({
                "admin_user_id": str(self.admin_user_id),
                "admin_reason": self.admin_reason,
                "deletion_initiated_by": "admin"
            })
        else:
            audit_data["deletion_initiated_by"] = "user"
        
        return audit_data
    
    def to_domain_deletion_data(self) -> dict:
        """
        Convert command to domain deletion data.
        
        Returns:
            dict: Deletion data formatted for domain service
        """
        return {
            "user_id": self.user_id,
            "confirmation_token": self.confirmation_token,
            "password_confirmation": self.password_confirmation,
            "cleanup_operations": self.get_cleanup_operations(),
            "audit_data": self.get_audit_data(),
            "requires_password_verification": self.requires_password_verification(),
        }