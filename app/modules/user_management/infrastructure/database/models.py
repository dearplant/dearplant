# 📄 File: app/modules/user_management/infrastructure/database/models.py
# 🧭 Purpose (Layman Explanation):
# This file defines how user information is stored in the database, including user accounts,
# profiles, and subscription details, following the exact structure needed for our plant care app.
#
# 🧪 Purpose (Technical Summary):
# SQLAlchemy ORM models implementing the database schema for user management entities,
# mapping domain models to PostgreSQL tables with proper relationships and constraints.
#
# 🔗 Dependencies:
# - SQLAlchemy ORM and async session support
# - app.shared.infrastructure.database.connection (base model and session)
# - UUID and datetime utilities for primary keys and timestamps
# - Core doc specifications for all field definitions
#
# 🔄 Connected Modules / Calls From:
# - user_repository_impl.py and profile_repository_impl.py (CRUD operations)
# - Database migration scripts (schema generation)
# - Application layer handlers (through repository implementations)

"""
SQLAlchemy Models for User Management

This module defines the database schema for user management entities,
implementing the exact field specifications from the core documentation.

Models:
- UserModel: Authentication and user account data (Core Doc 1.1)
- ProfileModel: User profile and preferences (Core Doc 1.2) 
- SubscriptionModel: Subscription and billing information (Core Doc 1.3)

All models use UUID primary keys and include proper timestamps,
foreign key relationships, and database constraints as specified
in the plant care app core documentation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, 
    Column, 
    DateTime, 
    ForeignKey, 
    Integer, 
    String, 
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# Use the shared base from the database configuration
from app.shared.infrastructure.database.connection import Base


# =============================================================================
# USER MODEL - Authentication Submodule (Core Doc 1.1)
# =============================================================================

class UserModel(Base):
    """
    SQLAlchemy model for user authentication and account management.
    
    Implements Core Doc 1.1 Authentication Submodule with all required fields:
    - User identification and authentication
    - Password security and reset functionality
    - Login attempt tracking and account protection
    - OAuth provider integration support
    - Email verification workflow
    """
    __tablename__ = "users"
    
    # Primary identification (Core Doc 1.1)
    user_id = Column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        nullable=False,
        comment="Unique identifier for each user"
    )
    
    # Authentication fields (Core Doc 1.1)
    email = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="User's email address (validated format)"
    )
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="Hashed password using bcrypt"
    )
    
    # Timestamps (Core Doc 1.1)
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        comment="Account creation date"
    )
    last_login = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Last login timestamp"
    )
    
    # Email verification (Core Doc 1.1)
    email_verified = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Email verification status"
    )
    
    # Password reset functionality (Core Doc 1.1)
    reset_token = Column(
        String(255), 
        nullable=True,
        comment="Password reset token (nullable)"
    )
    reset_token_expires = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Reset token expiration"
    )
    
    # Security and protection (Core Doc 1.1)
    login_attempts = Column(
        Integer, 
        nullable=False, 
        default=0,
        comment="Failed login attempt counter"
    )
    account_locked = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Account lock status"
    )
    
    # OAuth integration (Core Doc 1.1)
    provider = Column(
        String(50), 
        nullable=False, 
        default="email",
        comment="Authentication provider (email/google/apple)"
    )
    provider_id = Column(
        String(255), 
        nullable=True,
        comment="External provider ID"
    )
    
    # Relationships
    profile = relationship(
        "ProfileModel", 
        back_populates="user", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    subscription = relationship(
        "SubscriptionModel", 
        back_populates="user", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<UserModel(user_id={self.user_id}, email={self.email})>"


# =============================================================================
# PROFILE MODEL - Profile Management Submodule (Core Doc 1.2)
# =============================================================================

class ProfileModel(Base):
    """
    SQLAlchemy model for user profile and preferences management.
    
    Implements Core Doc 1.2 Profile Management Submodule with all required fields:
    - Display information and personalization
    - Location and weather integration
    - Language and theme preferences
    - Notification and privacy settings
    """
    __tablename__ = "profiles"
    
    # Primary identification (Core Doc 1.2)
    profile_id = Column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        nullable=False,
        comment="Unique profile identifier"
    )
    
    # Foreign key relationship (Core Doc 1.2)
    user_id = Column(
        PG_UUID(as_uuid=True), 
        ForeignKey("users.user_id", ondelete="CASCADE"), 
        nullable=False,
        unique=True,
        comment="Foreign key to authentication"
    )
    
    # Display information (Core Doc 1.2)
    display_name = Column(
        String(100), 
        nullable=False,
        comment="User's display name"
    )
    profile_photo = Column(
        String(500), 
        nullable=True,
        comment="Profile image URL in Supabase Storage"
    )
    bio = Column(
        Text, 
        nullable=True,
        comment="User biography (max 500 chars)"
    )
    
    # Location and weather integration (Core Doc 1.2)
    location = Column(
        String(255), 
        nullable=True,
        comment="User's location for weather data"
    )
    timezone = Column(
        String(50), 
        nullable=True,
        comment="User's timezone"
    )
    
    # Preferences (Core Doc 1.2)
    language = Column(
        String(10), 
        nullable=False, 
        default="auto",
        comment="Preferred language (default: auto-detect)"
    )
    theme = Column(
        String(20), 
        nullable=False, 
        default="auto",
        comment="UI theme preference (light/dark/auto)"
    )
    
    # Notification settings (Core Doc 1.2)
    notification_enabled = Column(
        Boolean, 
        nullable=False, 
        default=True,
        comment="Global notification toggle"
    )
    
    # Timestamps (Core Doc 1.2)
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        comment="Profile creation date"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(), 
        onupdate=func.now(),
        comment="Last profile update"
    )
    
    # Relationships
    user = relationship("UserModel", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<ProfileModel(profile_id={self.profile_id}, display_name={self.display_name})>"


# =============================================================================
# SUBSCRIPTION MODEL - Subscription Management Submodule (Core Doc 1.3)
# =============================================================================

class SubscriptionModel(Base):
    """
    SQLAlchemy model for subscription and billing management.
    
    Implements Core Doc 1.3 Subscription Management Submodule with all required fields:
    - Plan type and status tracking
    - Free trial management (7 days as specified)
    - Payment processing integration
    - Auto-renewal and cancellation logic
    """
    __tablename__ = "subscriptions"
    
    # Primary identification (Core Doc 1.3)
    subscription_id = Column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        nullable=False,
        comment="Unique subscription identifier"
    )
    
    # Foreign key relationship (Core Doc 1.3)
    user_id = Column(
        PG_UUID(as_uuid=True), 
        ForeignKey("users.user_id", ondelete="CASCADE"), 
        nullable=False,
        unique=True,
        comment="Foreign key to authentication"
    )
    
    # Plan and status (Core Doc 1.3)
    plan_type = Column(
        String(50), 
        nullable=False, 
        default="free",
        comment="free/premium_monthly/premium_yearly"
    )
    status = Column(
        String(20), 
        nullable=False, 
        default="active",
        comment="active/inactive/cancelled/expired"
    )
    
    # Free trial management (Core Doc 1.3 - 7 days specified)
    trial_active = Column(
        Boolean, 
        nullable=False, 
        default=True,
        comment="Free trial status"
    )
    trial_start_date = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Trial start date"
    )
    trial_end_date = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Trial end date"
    )
    
    # Subscription periods (Core Doc 1.3)
    subscription_start_date = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Paid subscription start"
    )
    subscription_end_date = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Paid subscription end"
    )
    
    # Payment integration (Core Doc 1.3)
    payment_method = Column(
        String(20), 
        nullable=True,
        comment="razorpay/stripe"
    )
    auto_renew = Column(
        Boolean, 
        nullable=False, 
        default=True,
        comment="Auto-renewal status"
    )
    
    # Timestamps (Core Doc 1.3)
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        comment="Subscription creation date"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(), 
        onupdate=func.now(),
        comment="Last subscription update"
    )
    
    # Relationships
    user = relationship("UserModel", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<SubscriptionModel(subscription_id={self.subscription_id}, plan_type={self.plan_type})>"


# =============================================================================
# MODEL REGISTRY AND METADATA
# =============================================================================

# Export all models for use in repository implementations
__all__ = [
    "UserModel",
    "ProfileModel", 
    "SubscriptionModel",
]


def get_user_management_models():
    """
    Get all user management models for migration and schema generation.
    
    Returns:
        list: List of SQLAlchemy model classes
    """
    return [UserModel, ProfileModel, SubscriptionModel]