# 📄 File: app/modules/user_management/domain/models/subscription.py
# 🧭 Purpose (Layman Explanation): 
# Defines subscription and billing information for users - tracks if they have free or premium plans, payment methods, and subscription status
# 🧪 Purpose (Technical Summary): 
# Domain model for Subscription entity implementing billing, payment processing, and subscription lifecycle management following core doc Subscription Management Submodule specifications
# 🔗 Dependencies: 
# pydantic, datetime, typing, uuid, enum
# 🔄 Connected Modules / Calls From: 
# subscription_service.py, payment processing, feature access control, analytics

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, validator, Field


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration following core doc specifications"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"  # Payment processing
    TRIAL = "trial"      # Free trial period


class PlanType(str, Enum):
    """Plan type enumeration following core doc specifications"""
    FREE = "free"
    PREMIUM_MONTHLY = "premium_monthly"
    PREMIUM_YEARLY = "premium_yearly"


class PaymentMethod(str, Enum):
    """Payment method enumeration following core doc specifications"""
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    NONE = "none"  # For free plans


class Subscription(BaseModel):
    """
    Subscription domain model representing user subscription and billing information.
    
    Implements core doc fields from Subscription Management Submodule (1.3):
    - subscription_id (UUID): Unique subscription identifier
    - user_id (UUID): Foreign key to authentication
    - plan_type (String): free/premium_monthly/premium_yearly
    - status (String): active/inactive/cancelled/expired
    - trial_active (Boolean): Free trial status
    - trial_start_date (Timestamp): Trial start date
    - trial_end_date (Timestamp): Trial end date
    - subscription_start_date (Timestamp): Paid subscription start
    - subscription_end_date (Timestamp): Paid subscription end
    - payment_method (String): razorpay/stripe
    - auto_renew (Boolean): Auto-renewal status
    - created_at (Timestamp): Subscription creation date
    - updated_at (Timestamp): Last subscription update
    
    Implements subscription management functionality from core doc.
    """
    
    # Identity - following core doc Subscription Management Submodule
    subscription_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Foreign key to User
    
    # Plan and status from core doc
    plan_type: PlanType = PlanType.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    
    # Trial management from core doc (7 days per specification)
    trial_active: bool = False
    trial_start_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    
    # Subscription period from core doc
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    
    # Payment processing from core doc
    payment_method: PaymentMethod = PaymentMethod.NONE
    auto_renew: bool = True  # Auto-renewal per core doc
    
    # Billing information
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    
    # Payment tracking
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    failed_payment_attempts: int = 0
    
    # External payment provider data
    external_subscription_id: Optional[str] = None  # Razorpay/Stripe subscription ID
    external_customer_id: Optional[str] = None     # Razorpay/Stripe customer ID
    
    # Cancellation tracking
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    cancelled_by_user: bool = False
    
    # Metadata following core doc timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
    
    @validator('trial_end_date', always=True)
    def validate_trial_end_date(cls, v, values):
        """Validate trial end date is after trial start date"""
        if v and values.get('trial_start_date'):
            if v <= values['trial_start_date']:
                raise ValueError('Trial end date must be after trial start date')
        return v
    
    @validator('subscription_end_date', always=True)
    def validate_subscription_end_date(cls, v, values):
        """Validate subscription end date is after start date"""
        if v and values.get('subscription_start_date'):
            if v <= values['subscription_start_date']:
                raise ValueError('Subscription end date must be after start date')
        return v
    
    @validator('last_payment_amount')
    def validate_payment_amount(cls, v):
        """Validate payment amount is positive"""
        if v is not None and v <= 0:
            raise ValueError('Payment amount must be positive')
        return v
    
    # Business Logic Methods following core doc Subscription Management functionality
    
    @classmethod
    def create_free_subscription(cls, user_id: str) -> "Subscription":
        """
        Create a new free subscription.
        Implements free plan setup from core doc Subscription Management functionality.
        
        Args:
            user_id: Associated user ID
            
        Returns:
            New free Subscription instance
        """
        return cls(
            user_id=user_id,
            plan_type=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            payment_method=PaymentMethod.NONE
        )
    
    def start_free_trial(self, trial_duration_days: int = 7) -> None:
        """
        Start free trial period.
        Implements free trial activation (7 days) from core doc Subscription Management functionality.
        
        Args:
            trial_duration_days: Trial duration in days (default 7 per core doc)
        """
        if self.trial_active:
            raise ValueError("Trial is already active")
        
        if self.has_had_trial():
            raise ValueError("User has already used their free trial")
        
        now = datetime.now(timezone.utc)
        
        self.trial_active = True
        self.trial_start_date = now
        self.trial_end_date = now + timedelta(days=trial_duration_days)
        self.status = SubscriptionStatus.TRIAL
        self.updated_at = now
    
    def end_trial(self) -> None:
        """
        End the free trial period.
        
        If no paid subscription is set up, reverts to free plan.
        """
        if not self.trial_active:
            return
        
        self.trial_active = False
        
        # If no paid subscription, revert to free
        if self.plan_type == PlanType.FREE:
            self.status = SubscriptionStatus.ACTIVE
        else:
            # Check if paid subscription should be active
            if self.is_subscription_period_active():
                self.status = SubscriptionStatus.ACTIVE
            else:
                self.status = SubscriptionStatus.EXPIRED
                self.plan_type = PlanType.FREE
        
        self.updated_at = datetime.now(timezone.utc)
    
    def upgrade_to_premium(
        self,
        plan_type: PlanType,
        payment_method: PaymentMethod,
        external_subscription_id: Optional[str] = None,
        external_customer_id: Optional[str] = None
    ) -> None:
        """
        Upgrade to premium subscription.
        Implements plan upgrade from core doc Subscription Management functionality.
        
        Args:
            plan_type: Premium plan type (monthly/yearly)
            payment_method: Payment method (razorpay/stripe)
            external_subscription_id: External payment provider subscription ID
            external_customer_id: External payment provider customer ID
        """
        if plan_type == PlanType.FREE:
            raise ValueError("Cannot upgrade to free plan")
        
        now = datetime.now(timezone.utc)
        
        self.plan_type = plan_type
        self.payment_method = payment_method
        self.external_subscription_id = external_subscription_id
        self.external_customer_id = external_customer_id
        self.subscription_start_date = now
        
        # Set subscription period based on plan
        if plan_type == PlanType.PREMIUM_MONTHLY:
            self.subscription_end_date = now + timedelta(days=30)
            self.next_billing_date = now + timedelta(days=30)
        else:  # PREMIUM_YEARLY
            self.subscription_end_date = now + timedelta(days=365)
            self.next_billing_date = now + timedelta(days=365)
        
        self.current_period_start = now
        self.current_period_end = self.subscription_end_date
        self.status = SubscriptionStatus.ACTIVE
        
        # End trial if active
        if self.trial_active:
            self.trial_active = False
        
        self.updated_at = now
    
    def downgrade_to_free(self, cancellation_reason: Optional[str] = None) -> None:
        """
        Downgrade to free subscription.
        Implements plan downgrade from core doc Subscription Management functionality.
        
        Args:
            cancellation_reason: Reason for cancellation
        """
        now = datetime.now(timezone.utc)
        
        self.plan_type = PlanType.FREE
        self.status = SubscriptionStatus.ACTIVE
        self.payment_method = PaymentMethod.NONE
        self.auto_renew = True
        
        # Clear paid subscription data
        self.subscription_end_date = None
        self.next_billing_date = None
        self.current_period_start = None
        self.current_period_end = None
        self.external_subscription_id = None
        
        # Record cancellation
        self.cancelled_at = now
        self.cancellation_reason = cancellation_reason
        self.cancelled_by_user = True
        
        self.updated_at = now
    
    def cancel_subscription(
        self,
        cancellation_reason: Optional[str] = None,
        immediate: bool = False
    ) -> None:
        """
        Cancel subscription.
        Implements subscription cancellation from core doc Subscription Management functionality.
        
        Args:
            cancellation_reason: Reason for cancellation
            immediate: Whether to cancel immediately or at period end
        """
        now = datetime.now(timezone.utc)
        
        self.auto_renew = False
        self.cancelled_at = now
        self.cancellation_reason = cancellation_reason
        self.cancelled_by_user = True
        
        if immediate:
            self.status = SubscriptionStatus.CANCELLED
            self.subscription_end_date = now
        else:
            self.status = SubscriptionStatus.CANCELLED
            # Keep current period end date for access until then
        
        self.updated_at = now
    
    def reactivate_subscription(self) -> None:
        """
        Reactivate a cancelled subscription.
        """
        if self.status != SubscriptionStatus.CANCELLED:
            raise ValueError("Can only reactivate cancelled subscriptions")
        
        if self.is_subscription_period_active():
            self.status = SubscriptionStatus.ACTIVE
            self.auto_renew = True
            self.cancelled_at = None
            self.cancellation_reason = None
            self.cancelled_by_user = False
            self.updated_at = datetime.now(timezone.utc)
        else:
            raise ValueError("Subscription period has expired")
    
    def process_successful_payment(self, amount: float) -> None:
        """
        Process successful payment and extend subscription.
        Implements payment processing integration from core doc Subscription Management functionality.
        
        Args:
            amount: Payment amount processed
        """
        now = datetime.now(timezone.utc)
        
        self.last_payment_date = now
        self.last_payment_amount = amount
        self.failed_payment_attempts = 0
        self.status = SubscriptionStatus.ACTIVE
        
        # Extend subscription period
        if self.plan_type == PlanType.PREMIUM_MONTHLY:
            new_end_date = (self.subscription_end_date or now) + timedelta(days=30)
            self.next_billing_date = new_end_date
        else:  # PREMIUM_YEARLY
            new_end_date = (self.subscription_end_date or now) + timedelta(days=365)
            self.next_billing_date = new_end_date
        
        self.subscription_end_date = new_end_date
        self.current_period_start = now
        self.current_period_end = new_end_date
        
        self.updated_at = now
    
    def process_failed_payment(self) -> None:
        """
        Process failed payment attempt.
        Implements auto-renewal failure handling.
        """
        self.failed_payment_attempts += 1
        
        # After 3 failed attempts, suspend subscription
        if self.failed_payment_attempts >= 3:
            self.status = SubscriptionStatus.INACTIVE
        
        self.updated_at = datetime.now(timezone.utc)
    
    def expire_subscription(self) -> None:
        """
        Mark subscription as expired.
        Called when subscription period ends without renewal.
        """
        self.status = SubscriptionStatus.EXPIRED
        self.plan_type = PlanType.FREE
        self.payment_method = PaymentMethod.NONE
        self.updated_at = datetime.now(timezone.utc)
    
    # Query Methods
    
    def is_active(self) -> bool:
        """
        Check if subscription provides active access.
        
        Returns:
            True if user has active subscription access
        """
        return (
            self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL] and
            (self.is_trial_active() or self.is_subscription_period_active() or self.plan_type == PlanType.FREE)
        )
    
    def is_premium(self) -> bool:
        """
        Check if user has premium access.
        
        Returns:
            True if user has premium features access
        """
        return (
            self.is_active() and
            (self.plan_type in [PlanType.PREMIUM_MONTHLY, PlanType.PREMIUM_YEARLY] or self.is_trial_active())
        )
    
    def is_trial_active(self) -> bool:
        """
        Check if free trial is currently active.
        
        Returns:
            True if trial is active and not expired
        """
        if not self.trial_active or not self.trial_end_date:
            return False
        
        return datetime.now(timezone.utc) < self.trial_end_date
    
    def is_subscription_period_active(self) -> bool:
        """
        Check if paid subscription period is active.
        
        Returns:
            True if within paid subscription period
        """
        if not self.subscription_end_date:
            return False
        
        return datetime.now(timezone.utc) < self.subscription_end_date
    
    def has_had_trial(self) -> bool:
        """
        Check if user has previously used their free trial.
        
        Returns:
            True if trial has been used before
        """
        return self.trial_start_date is not None
    
    def days_until_expiry(self) -> Optional[int]:
        """
        Calculate days until subscription expires.
        
        Returns:
            Number of days until expiry, None if no expiry date
        """
        if self.is_trial_active() and self.trial_end_date:
            delta = self.trial_end_date - datetime.now(timezone.utc)
            return max(0, delta.days)
        elif self.subscription_end_date:
            delta = self.subscription_end_date - datetime.now(timezone.utc)
            return max(0, delta.days)
        
        return None
    
    def needs_payment_retry(self) -> bool:
        """
        Check if payment retry is needed.
        
        Returns:
            True if failed payments need retry
        """
        return (
            self.failed_payment_attempts > 0 and
            self.failed_payment_attempts < 3 and
            self.status != SubscriptionStatus.CANCELLED
        )
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert subscription to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive payment data
            
        Returns:
            Subscription data as dictionary
        """
        data = self.dict()
        
        if not include_sensitive:
            # Remove sensitive payment information
            sensitive_fields = [
                'external_subscription_id',
                'external_customer_id',
                'last_payment_amount',
                'failed_payment_attempts'
            ]
            
            for field in sensitive_fields:
                data.pop(field, None)
        
        return data