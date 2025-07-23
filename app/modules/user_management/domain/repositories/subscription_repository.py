# 📄 File: app/modules/user_management/domain/repositories/subscription_repository.py
# 🧭 Purpose (Layman Explanation):
# Defines what subscription-related database operations our app can perform,
# like creating trials, managing billing, and tracking subscription status.
# 🧪 Purpose (Technical Summary):
# Abstract repository interface for subscription management operations including
# trial creation, plan management, billing tracking, and subscription lifecycle.
# 🔗 Dependencies:
# - abc (Abstract Base Classes)
# - UUID and datetime types
# - Subscription domain model
# - SQLAlchemy AsyncSession
# 🔄 Connected Modules / Calls From:
# - Subscription Service (business logic)
# - User Service (trial creation)
# - Payment Service (subscription updates)
# - Repository Implementation (concrete implementation)

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user_management.domain.models.subscription import Subscription


class SubscriptionRepository(ABC):
    """
    Abstract repository interface for subscription data access operations.
    
    Provides methods for managing subscription lifecycle, billing, trials,
    and subscription analytics according to core documentation specifications.
    """
    
    @abstractmethod
    async def create(self, session: AsyncSession, subscription_data: Dict[str, Any]) -> Subscription:
        """Create a new subscription."""
        pass
    
    @abstractmethod
    async def get_by_id(self, session: AsyncSession, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, session: AsyncSession, user_id: UUID) -> Optional[Subscription]:
        """Get subscription by user ID."""
        pass
    
    @abstractmethod
    async def update(self, session: AsyncSession, subscription_id: UUID, update_data: Dict[str, Any]) -> Optional[Subscription]:
        """Update subscription information."""
        pass
    
    @abstractmethod
    async def delete(self, session: AsyncSession, subscription_id: UUID) -> bool:
        """Delete subscription."""
        pass
    
    @abstractmethod
    async def get_active_subscriptions(
        self, 
        session: AsyncSession, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Subscription]:
        """Get all active subscriptions."""
        pass
    
    @abstractmethod
    async def get_expiring_trials(
        self, 
        session: AsyncSession, 
        days_ahead: int = 3
    ) -> List[Subscription]:
        """Get trials expiring within specified days."""
        pass
    
    @abstractmethod
    async def get_by_plan_type(
        self, 
        session: AsyncSession, 
        plan_type: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Subscription]:
        """Get subscriptions by plan type."""
        pass
    
    @abstractmethod
    async def get_by_status(
        self, 
        session: AsyncSession, 
        status: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Subscription]:
        """Get subscriptions by status."""
        pass
    
    @abstractmethod
    async def cancel_subscription(
        self, 
        session: AsyncSession, 
        subscription_id: UUID, 
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """Cancel a subscription."""
        pass
    
    @abstractmethod
    async def reactivate_subscription(
        self, 
        session: AsyncSession, 
        subscription_id: UUID
    ) -> Optional[Subscription]:
        """Reactivate a cancelled subscription."""
        pass
    
    @abstractmethod
    async def update_payment_method(
        self, 
        session: AsyncSession, 
        subscription_id: UUID, 
        payment_method: str, 
        payment_provider_id: Optional[str] = None
    ) -> Optional[Subscription]:
        """Update subscription payment method."""
        pass
    
    @abstractmethod
    async def extend_trial(
        self, 
        session: AsyncSession, 
        subscription_id: UUID, 
        additional_days: int
    ) -> Optional[Subscription]:
        """Extend trial period."""
        pass
    
    @abstractmethod
    async def upgrade_subscription(
        self, 
        session: AsyncSession, 
        subscription_id: UUID, 
        new_plan_type: str, 
        payment_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Subscription]:
        """Upgrade subscription to a higher plan."""
        pass
    
    @abstractmethod
    async def downgrade_subscription(
        self, 
        session: AsyncSession, 
        subscription_id: UUID, 
        new_plan_type: str, 
        effective_date: Optional[datetime] = None
    ) -> Optional[Subscription]:
        """Downgrade subscription to a lower plan."""
        pass
    
    @abstractmethod
    async def get_subscription_analytics(
        self, 
        session: AsyncSession, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get subscription analytics and metrics."""
        pass
    
    @abstractmethod
    async def get_revenue_metrics(
        self, 
        session: AsyncSession, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get revenue and billing metrics."""
        pass
    
    @abstractmethod
    async def get_churn_analysis(
        self, 
        session: AsyncSession, 
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get subscription churn analysis."""
        pass
    
    @abstractmethod
    async def get_trial_conversion_rate(
        self, 
        session: AsyncSession, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> float:
        """Get trial to paid conversion rate."""
        pass
    
    @abstractmethod
    async def bulk_update_billing_cycle(
        self, 
        session: AsyncSession, 
        subscription_ids: List[UUID], 
        new_billing_date: datetime
    ) -> int:
        """Update billing cycle for multiple subscriptions."""
        pass
    
    @abstractmethod
    async def get_subscriptions_for_renewal(
        self, 
        session: AsyncSession, 
        days_ahead: int = 7
    ) -> List[Subscription]:
        """Get subscriptions due for renewal."""
        pass
    
    @abstractmethod
    async def process_subscription_renewal(
        self, 
        session: AsyncSession, 
        subscription_id: UUID, 
        payment_successful: bool, 
        payment_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Subscription]:
        """Process subscription renewal."""
        pass
    
    @abstractmethod
    async def exists_by_user_id(self, session: AsyncSession, user_id: UUID) -> bool:
        """Check if subscription exists for user."""
        pass
    
    @abstractmethod
    async def count_by_plan_type(self, session: AsyncSession, plan_type: str) -> int:
        """Count subscriptions by plan type."""
        pass
    
    @abstractmethod
    async def count_by_status(self, session: AsyncSession, status: str) -> int:
        """Count subscriptions by status."""
        pass