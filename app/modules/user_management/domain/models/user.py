# 📄 File: app/modules/user_management/domain/models/user.py
# 🧭 Purpose (Layman Explanation): 
# Defines what a "user" is in our plant care app - their basic info like email, password, and account status that forms the core of user identity
# 🧪 Purpose (Technical Summary): 
# Domain model for User entity implementing business rules, validation, and user lifecycle management with role-based access control following core doc specifications
# 🔗 Dependencies: 
# pydantic, datetime, typing, uuid, app.shared.core.security
# 🔄 Connected Modules / Calls From: 
# user_service.py, auth_service.py, user_repository.py, authentication middleware

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr, validator, Field

from app.shared.core.security import get_password_hash, verify_password


class UserRole(str, Enum):
    """User role enumeration following core doc specifications"""
    USER = "user"
    PREMIUM = "premium"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User status enumeration following core doc specifications"""
    PENDING = "pending"           # Email not verified
    ACTIVE = "active"             # Normal active user
    INACTIVE = "inactive"         # Temporarily disabled
    SUSPENDED = "suspended"       # Suspended for violations
    DELETED = "deleted"           # Soft deleted account


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration following core doc specifications"""
    FREE = "free"
    PREMIUM_MONTHLY = "premium_monthly"
    PREMIUM_YEARLY = "premium_yearly"


class User(BaseModel):
    """
    User domain model representing a plant care application user.
    
    Implements core doc fields from Authentication Submodule (1.1):
    - user_id (UUID): Unique identifier for each user
    - email (String): User's email address (validated format)
    - password_hash (String): Hashed password using bcrypt
    - created_at (Timestamp): Account creation date
    - last_login_at (Timestamp): Last login timestamp
    - email_verified (Boolean): Email verification status
    - reset_token (String): Password reset token (nullable)
    - reset_token_expires (Timestamp): Reset token expiration
    - failed_login_attempts (Integer): Failed login attempt counter
    - account_locked (Boolean): Account lock status
    - provider (String): Authentication provider (email/google/apple)
    - provider_id (String): External provider ID
    
    Contains core user identity, authentication, and authorization data.
    Implements business rules and validation for user management.
    """
    
    # Identity - following core doc Authentication Submodule
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="id")
    email: EmailStr
    password_hash: str
    
    # Authentication fields from core doc
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None
    email_verified: bool = False
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked: bool = False
    provider: str = "email"  # email/google/apple
    provider_id: Optional[str] = None
    
    # Authorization and subscription
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    
    # Basic profile data (detailed profile in separate model)
    display_name: Optional[str] = None
    profile_photo: Optional[str] = None
    
    # User preferences from core doc Profile Management
    language: str = "en"  # auto-detect default
    timezone: str = "UTC"
    theme: str = "auto"  # light/dark/auto
    notification_enabled: bool = True
    
    # Tracking and metadata
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    login_count: int = 0
    last_active_at: Optional[datetime] = None
    registration_ip: Optional[str] = None
    account_locked_at: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        populate_by_name = True
        
    @validator('email')
    def validate_email(cls, v):
        """Validate email format and domain following core doc requirements"""
        if not v:
            raise ValueError('Email is required')
        
        # Convert to lowercase for consistency
        email = v.lower().strip()
        
        # Length validation
        if len(email) > 254:
            raise ValueError('Email too long')
            
        return email
    
    @validator('password_hash')
    def validate_password_hash(cls, v):
        """Validate password hash exists"""
        if not v:
            raise ValueError('Password hash is required')
        return v
    
    @validator('provider')
    def validate_provider(cls, v):
        """Validate authentication provider"""
        allowed_providers = ["email", "google", "apple"]
        if v not in allowed_providers:
            raise ValueError(f'Provider must be one of: {allowed_providers}')
        return v
    
    @validator('theme')
    def validate_theme(cls, v):
        """Validate theme preference"""
        allowed_themes = ["light", "dark", "auto"]
        if v not in allowed_themes:
            raise ValueError(f'Theme must be one of: {allowed_themes}')
        return v
    
    # Business Logic Methods following core doc Authentication functionality
    
    @classmethod
    def create_new_user(
        cls,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        provider: str = "email",
        provider_id: Optional[str] = None,
        registration_ip: Optional[str] = None
    ) -> "User":
        """
        Create a new user with validation and proper defaults.
        Implements user registration from core doc Authentication functionality.
        
        Args:
            email: User email address
            password: Plain text password (will be hashed)
            display_name: Optional display name
            provider: Authentication provider (email/google/apple)
            provider_id: External provider ID
            registration_ip: IP address of registration
            
        Returns:
            New User instance
        """
        # Hash password using bcrypt (core doc Security Standards)
        password_hash = get_password_hash(password)
        
        # Generate reset token for email verification
        reset_token = str(uuid.uuid4())
        
        return cls(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            provider=provider,
            provider_id=provider_id,
            reset_token=reset_token,
            registration_ip=registration_ip,
            last_active_at=datetime.now(timezone.utc)
        )
    
    def verify_password(self, password: str) -> bool:
        """
        Verify user password using bcrypt.
        Implements login validation from core doc Authentication functionality.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches
        """
        return verify_password(password, self.password_hash)
    
    def update_password(self, new_password: str) -> None:
        """
        Update user password with proper hashing.
        Implements password reset from core doc Authentication functionality.
        
        Args:
            new_password: New plain text password
        """
        self.password_hash = get_password_hash(new_password)
        self.reset_token = None
        self.reset_token_expires = None
        self.updated_at = datetime.now(timezone.utc)
        
        # Reset security counters
        self.failed_login_attempts = 0
        self.account_locked = False
    
    def verify_email(self) -> None:
        """
        Mark email as verified and activate account.
        Implements email verification from core doc Authentication functionality.
        """
        self.email_verified = True
        self.reset_token = None
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def generate_password_reset_token(self, expires_in_hours: int = 24) -> str:
        """
        Generate password reset token.
        Implements password reset via email from core doc Authentication functionality.
        
        Args:
            expires_in_hours: Token expiration time in hours
            
        Returns:
            Password reset token
        """
        self.reset_token = str(uuid.uuid4())
        self.reset_token_expires = datetime.now(timezone.utc).replace(
            hour=datetime.now(timezone.utc).hour + expires_in_hours
        )
        self.updated_at = datetime.now(timezone.utc)
        
        return self.reset_token
    
    def record_login_success(self, login_ip: Optional[str] = None) -> None:
        """
        Record successful login.
        Implements session management from core doc Authentication functionality.
        
        Args:
            login_ip: IP address of login attempt
        """
        self.last_login_at = datetime.now(timezone.utc)
        self.last_active_at = datetime.now(timezone.utc)
        self.login_count += 1
        self.failed_login_attempts = 0
        self.account_locked = False
        self.updated_at = datetime.now(timezone.utc)
    
    def record_login_failure(self, max_attempts: int = 5) -> None:
        """
        Record failed login attempt and apply lockout if necessary.
        Implements rate limiting (max 5 attempts) from core doc Authentication functionality.
        
        Args:
            max_attempts: Maximum failed attempts before lockout (default 5 per core doc)
        """
        self.failed_login_attempts += 1
        self.updated_at = datetime.now(timezone.utc)
        
        # Account lockout protection from core doc
        if self.failed_login_attempts >= max_attempts:
            self.account_locked_at = Optional[datetime]
            self.account_locked = True

    
    def unlock_account(self) -> None:
        """
        Unlock user account and reset failed attempts.
        Implements account lockout protection from core doc Authentication functionality.
        """
        self.failed_login_attempts = 0
        self.account_locked = False
        self.updated_at = None
    
    def update_activity(self) -> None:
        """Update last activity timestamp for session management."""
        self.last_active_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.status = UserStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate user account."""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def suspend(self) -> None:
        """Suspend user account."""
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self) -> None:
        """Soft delete user account."""
        self.status = UserStatus.DELETED
        self.updated_at = datetime.now(timezone.utc)
    
    def upgrade_subscription(self, tier: SubscriptionTier) -> None:
        """
        Upgrade user subscription tier.
        Connects to Subscription Management submodule from core doc.
        
        Args:
            tier: New subscription tier
        """
        self.subscription_tier = tier
        if tier in [SubscriptionTier.PREMIUM_MONTHLY, SubscriptionTier.PREMIUM_YEARLY]:
            self.role = UserRole.PREMIUM
        self.updated_at = datetime.now(timezone.utc)
    
    def downgrade_to_free(self) -> None:
        """
        Downgrade user to free subscription.
        Connects to Subscription Management submodule from core doc.
        """
        self.subscription_tier = SubscriptionTier.FREE
        if self.role == UserRole.PREMIUM:
            self.role = UserRole.USER
        self.updated_at = datetime.now(timezone.utc)
    
    def is_active(self) -> bool:
        """
        Check if user account is active and can access the system.
        
        Returns:
            True if user can access the system
        """
        return (
            self.status == UserStatus.ACTIVE and
            not self.account_locked and
            self.email_verified
        )
    
    def can_login(self) -> bool:
        """
        Check if user can attempt login.
        
        Returns:
            True if login attempt is allowed
        """
        return (
            self.status in [UserStatus.ACTIVE, UserStatus.PENDING] and
            not self.account_locked
        )
    
    def is_premium_user(self) -> bool:
        """
        Check if user has premium subscription.
        
        Returns:
            True if user has premium access
        """
        return self.subscription_tier in [
            SubscriptionTier.PREMIUM_MONTHLY,
            SubscriptionTier.PREMIUM_YEARLY
        ]
    
    def get_display_name(self) -> str:
        """
        Get user's display name with fallback.
        
        Returns:
            User's display name or email prefix
        """
        if self.display_name:
            return self.display_name
        else:
            return self.email.split('@')[0]
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert user to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive data
            
        Returns:
            User data as dictionary
        """
        data = self.dict(by_alias=True)
        
        if not include_sensitive:
            # Remove sensitive fields
            sensitive_fields = [
                'password_hash',
                'reset_token',
                'reset_token_expires',
                'failed_login_attempts',
                'account_locked',
                'registration_ip',
                'provider_id'
            ]
            
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data