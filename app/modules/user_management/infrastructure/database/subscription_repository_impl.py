# 📄 File: app/modules/user_management/infrastructure/database/subscription_repository_impl.py
# 🧭 Purpose (Layman Explanation): 
# This file handles all the actual database operations for subscriptions - creating them, updating them,
# checking if they're active, and managing subscription changes in the PostgreSQL database.
# 🧪 Purpose (Technical Summary): 
# SQLAlchemy-based implementation of subscription repository interface, providing concrete database
# operations for subscription management with Core Doc 1.3 compliance and proper error handling.
# 🔗 Dependencies: 
# SQLAlchemy, app.shared.infrastructure.database.session, app.shared.core.exceptions, logging, datetime
# 🔄 Connected Modules / Calls From: 
# Subscription services, application command/query handlers, subscription domain services

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, case
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from uuid import UUID, uuid4

from app.shared.core.exceptions import (
    SubscriptionError, 
    NotFoundError, 
    DatabaseError,
    ValidationError,
    DatabaseError
)
from app.modules.user_management.domain.repositories.subscription_repository import SubscriptionRepository
from app.modules.user_management.domain.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, PaymentMethod
from app.modules.user_management.infrastructure.database.models import SubscriptionModel, UserModel
from app.shared.infrastructure.database.session import get_db_session

logger = logging.getLogger(__name__)

class SubscriptionRepositoryImpl(SubscriptionRepository):
    """
    SQLAlchemy implementation of subscription repository.
    Handles all subscription database operations with proper error handling.
    """

    def __init__(self, session: AsyncSession = Depends(get_db_session)):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        result = await self.get_subscription_by_id(subscription_id)
        if result:
            return Subscription(**result)
        return None
    
    async def create(self, subscription_data: Dict[str, Any]) -> Subscription:
        """
        Create a new subscription with provided data.
        
        Args:
            subscription_data: Dictionary containing subscription data
            
        Returns:
            Subscription: Created subscription domain model
        """
        try:
            user_id = subscription_data.get("user_id")
            # Ensure plan_type is an enum instance or valid string
            plan_type = subscription_data.get("plan_type", SubscriptionPlan.FREE.value)
            if isinstance(plan_type, str):
                plan_type = SubscriptionPlan(plan_type)
            elif not isinstance(plan_type, SubscriptionPlan):
                logger.error(f"Invalid plan_type: {plan_type}")
                raise ValueError(f"Invalid plan_type: {plan_type}")

            status = subscription_data.get("status", SubscriptionStatus.ACTIVE.value)
            if isinstance(status, str):
                status = SubscriptionStatus(status)

            payment_method = subscription_data.get("payment_method", PaymentMethod.NONE.value)
            if isinstance(payment_method, str):
                payment_method = PaymentMethod(payment_method)

            auto_renew = subscription_data.get("auto_renew", False)
            trial_active = subscription_data.get("trial_active", False)

            # Use existing create_subscription method
            subscription_dict = await self.create_subscription(
                user_id=user_id,
                plan_type=plan_type,
                payment_method=payment_method,
                auto_renew=auto_renew,
                trial_active=trial_active
            )

            # Ensure subscription_id and user_id are strings
            subscription_dict["subscription_id"] = str(subscription_dict["subscription_id"])
            subscription_dict["user_id"] = str(subscription_dict["user_id"])
            subscription_dict["plan_type"] = plan_type.value if isinstance(plan_type, SubscriptionPlan) else plan_type

            # Convert to domain model
            return Subscription(**subscription_dict)
        except Exception as e:
            logger.error(f"Error creating subscription with data {subscription_data}: {e}")
            raise SubscriptionError(f"Failed to create subscription: {e}")


    async def create_subscription(
        self,
        user_id: UUID,
        plan_type: SubscriptionPlan = SubscriptionPlan.FREE,
        payment_method: Optional[PaymentMethod] = None,
        auto_renew: bool = False,
        trial_active: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new subscription for a user.
        
        Args:
            user_id: User identifier
            plan_type: Subscription plan type
            payment_method: Payment method for subscription
            auto_renew: Auto-renewal setting
            trial_active: Whether trial is active
            
        Returns:
            Dict containing created subscription data
        """
        try:
            # Check if user already has a subscription
            existing_query = select(SubscriptionModel).where(
                SubscriptionModel.user_id == user_id
            )
            existing_result = await self.session.execute(existing_query)
            existing_subscription = existing_result.scalar_one_or_none()

            if existing_subscription:
                logger.warning(f"User {user_id} already has subscription {existing_subscription.subscription_id}")
                raise SubscriptionError(
                    "User already has an active subscription",
                    user_id=str(user_id)
                )

            # Verify user exists
            user_query = select(UserModel).where(UserModel.user_id == user_id)
            user_result = await self.session.execute(user_query)
            user = user_result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found for subscription creation")
                raise NotFoundError(
                    "User not found",
                    resource_type="user",
                    resource_id=str(user_id)
                )

            # Set trial dates if trial is active
            trial_start_date = None
            trial_end_date = None
            if trial_active and plan_type != SubscriptionPlan.FREE:
                trial_start_date = datetime.utcnow()
                trial_end_date = trial_start_date + timedelta(days=7)

            # Set subscription dates
            subscription_start_date = datetime.utcnow()
            subscription_end_date = None
            
            if plan_type == SubscriptionPlan.PREMIUM_MONTHLY:
                subscription_end_date = subscription_start_date + timedelta(days=30)
            elif plan_type == SubscriptionPlan.PREMIUM_YEARLY:
                subscription_end_date = subscription_start_date + timedelta(days=365)

            # Create new subscription
            new_subscription = SubscriptionModel(
                subscription_id=uuid4(),
                user_id=user_id,
                plan_type=plan_type.value,
                status=SubscriptionStatus.ACTIVE.value,
                trial_active=trial_active,
                trial_start_date=trial_start_date,
                trial_end_date=trial_end_date,
                subscription_start_date=subscription_start_date,
                subscription_end_date=subscription_end_date,
                payment_method=payment_method.value if payment_method else PaymentMethod.NONE.value,
                auto_renew=auto_renew
            )

            self.session.add(new_subscription)
            await self.session.flush()  # To get the generated ID

            logger.info(f"Created subscription {new_subscription.subscription_id} for user {user_id}")

            return {
                "subscription_id": str(new_subscription.subscription_id),  # Convert to string
                "user_id": str(new_subscription.user_id),
                "plan_type": new_subscription.plan_type,
                "status": new_subscription.status,
                "trial_active": new_subscription.trial_active,
                "trial_start_date": new_subscription.trial_start_date,
                "trial_end_date": new_subscription.trial_end_date,
                "subscription_start_date": new_subscription.subscription_start_date,
                "subscription_end_date": new_subscription.subscription_end_date,
                "payment_method": new_subscription.payment_method,
                "auto_renew": new_subscription.auto_renew,
                "created_at": new_subscription.created_at,
                "updated_at": new_subscription.updated_at
            }

        except IntegrityError as e:
            logger.error(f"Integrity error creating subscription for user {user_id}: {e}")
            raise SubscriptionError(
                "Failed to create subscription due to data constraint violation",
                user_id=str(user_id)
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error creating subscription for user {user_id}: {e}")
            raise DatabaseError(f"Failed to create subscription: {e}")

    async def get_subscription_by_id(self, subscription_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get subscription by subscription ID.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Optional dictionary containing subscription data
        """
        try:
            logger.info(f"step1")
            query = select(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            )
            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                return None

            return self._subscription_to_dict(subscription)

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to fetch subscription: {e}")

    async def get_by_user_id(self, user_id: UUID) -> Optional[Subscription]:
        """
        Get subscription by user ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional[Subscription]: Subscription domain model or None if not found
        """
        result = await self.get_subscription_by_user_id(user_id)
        if result:
            return Subscription(**result)
        return None

    async def get_subscription_by_user_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get subscription by user ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            Optional dictionary containing subscription data
        """
        logger.info(f"step2")
        try:
            query = select(SubscriptionModel).where(
                SubscriptionModel.user_id == user_id
            )
            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                return None

            return self._subscription_to_dict(subscription)

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscription for user {user_id}: {e}")
            raise DatabaseError(f"Failed to fetch subscription: {e}")

    async def update(self, subscription_id: UUID, update_data: Dict[str, Any]) -> Optional[Subscription]:
        """
        Update subscription with provided data.
        
        Args:
            subscription_id: Subscription identifier
            update_data: Dictionary containing fields to update
            
        Returns:
            Optional[Subscription]: Updated subscription domain model or None if not found
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            if "plan_type" in update_data and isinstance(update_data["plan_type"], str):
                update_data["plan_type"] = SubscriptionPlan(update_data["plan_type"])
            if "status" in update_data and isinstance(update_data["status"], str):
                update_data["status"] = SubscriptionStatus(update_data["status"])
            if "payment_method" in update_data and isinstance(update_data["payment_method"], str):
                update_data["payment_method"] = PaymentMethod(update_data["payment_method"])

            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(**update_data)
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for update")
                return None

            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Updated subscription {subscription_id}")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error updating subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to update subscription: {e}")

    async def delete(self, subscription_id: UUID) -> bool:
        """
        Hard delete a subscription (permanent removal).
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            query = delete(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            )

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for hard deletion")
                return False

            logger.info(f"Hard deleted subscription {subscription_id}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error hard deleting subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to hard delete subscription: {e}")

    async def get_active_subscriptions(self, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """
        Get all active subscriptions.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Subscription]: List of active subscription domain models
        """
        try:
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    or_(
                        SubscriptionModel.subscription_end_date.is_(None),
                        SubscriptionModel.subscription_end_date > datetime.utcnow()
                    )
                )
            ).order_by(SubscriptionModel.created_at.desc())
            if limit:
                query = query.limit(limit)
            if skip:
                query = query.offset(skip)

            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [Subscription(**self._subscription_to_dict(sub)) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching active subscriptions: {e}")
            raise DatabaseError(f"Failed to fetch active subscriptions: {e}")

    async def get_expiring_trials(self, days_ahead: int = 3) -> List[Subscription]:
        """
        Get trials expiring within specified days.
        
        Args:
            days_ahead: Number of days to look ahead for trial expiration
            
        Returns:
            List[Subscription]: List of subscription domain models with expiring trials
        """
        try:
            expiry_date = datetime.utcnow() + timedelta(days=days_ahead)
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.trial_active == True,
                    SubscriptionModel.trial_end_date <= expiry_date,
                    SubscriptionModel.trial_end_date > datetime.utcnow()
                )
            )
            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [Subscription(**self._subscription_to_dict(sub)) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching expiring trials: {e}")
            raise DatabaseError(f"Failed to fetch expiring trials: {e}")

    async def get_by_plan_type(self, plan_type: str, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """
        Get subscriptions by plan type.
        
        Args:
            plan_type: Subscription plan type
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Subscription]: List of subscription domain models
        """
        try:
            plan_enum = SubscriptionPlan(plan_type)
            query = select(SubscriptionModel).where(
                SubscriptionModel.plan_type == plan_enum
            ).order_by(SubscriptionModel.created_at.desc())
            if limit:
                query = query.limit(limit)
            if skip:
                query = query.offset(skip)

            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [Subscription(**self._subscription_to_dict(sub)) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscriptions by plan type {plan_type}: {e}")
            raise DatabaseError(f"Failed to fetch subscriptions by plan type: {e}")

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """
        Get subscriptions by status.
        
        Args:
            status: Subscription status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Subscription]: List of subscription domain models
        """
        try:
            status_enum = SubscriptionStatus(status)
            query = select(SubscriptionModel).where(
                SubscriptionModel.status == status_enum
            ).order_by(SubscriptionModel.created_at.desc())
            if limit:
                query = query.limit(limit)
            if skip:
                query = query.offset(skip)

            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [Subscription(**self._subscription_to_dict(sub)) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscriptions by status {status}: {e}")
            raise DatabaseError(f"Failed to fetch subscriptions by status: {e}")

    async def cancel_subscription(self, subscription_id: UUID, cancellation_reason: Optional[str] = None) -> bool:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription identifier
            cancellation_reason: Optional reason for cancellation
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        try:
            update_values = {
                "status": SubscriptionStatus.CANCELLED,
                "auto_renew": False,
                "updated_at": datetime.utcnow()
            }
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(**update_values)
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for cancellation")
                return False

            logger.info(f"Cancelled subscription {subscription_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error cancelling subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to cancel subscription: {e}")

    async def reactivate_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """
        Reactivate a cancelled or expired subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Optional[Subscription]: Reactivated subscription domain model or None if not found
        """
        try:
            new_end_date = datetime.utcnow() + timedelta(days=30)
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                status=SubscriptionStatus.ACTIVE.value,
                subscription_end_date=new_end_date,
                updated_at=datetime.utcnow()
            )
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for reactivation")
                return None

            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Reactivated subscription {subscription_id}")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error reactivating subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to reactivate subscription: {e}")

    async def update_payment_method(self, subscription_id: UUID, payment_method: str, payment_provider_id: Optional[str] = None) -> Optional[Subscription]:
        """
        Update payment method for subscription.
        
        Args:
            subscription_id: Subscription identifier
            payment_method: New payment method
            payment_provider_id: Optional payment provider identifier
            
        Returns:
            Optional[Subscription]: Updated subscription domain model or None if not found
        """
        try:
            payment_enum = PaymentMethod(payment_method)
            update_values = {
                "payment_method": payment_enum,
                "updated_at": datetime.utcnow()
            }
            if payment_provider_id is not None:
                update_values["payment_provider_id"] = payment_provider_id

            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(**update_values)
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for payment method update")
                return None

            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Updated payment method for subscription {subscription_id} to {payment_enum.value}")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error updating payment method for subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to update payment method: {e}")

    async def extend_trial(self, subscription_id: UUID, additional_days: int) -> Optional[Subscription]:
        """
        Extend trial period by additional days.
        
        Args:
            subscription_id: Subscription identifier
            additional_days: Number of days to extend trial
            
        Returns:
            Optional[Subscription]: Updated subscription domain model or None if not found
        """
        try:
            query = select(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            )
            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.warning(f"No subscription found with ID {subscription_id} for trial extension")
                return None

            if not subscription.trial_active:
                logger.warning(f"Subscription {subscription_id} does not have an active trial")
                return None

            current_end = subscription.trial_end_date or datetime.utcnow()
            new_trial_end = current_end + timedelta(days=additional_days)

            update_query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                trial_end_date=new_trial_end,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(update_query)
            
            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Extended trial for subscription {subscription_id} by {additional_days} days")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error extending trial for subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to extend trial: {e}")

    async def upgrade_subscription(self, subscription_id: UUID, new_plan_type: str, payment_data: Optional[Dict[str, Any]] = None) -> Optional[Subscription]:
        """
        Upgrade subscription to a higher plan.
        
        Args:
            subscription_id: Subscription identifier
            new_plan_type: New (higher) subscription plan
            payment_data: Optional payment data for new plan
            
        Returns:
            Optional[Subscription]: Updated subscription domain model or None if not found
        """
        try:
            effective_date = datetime.utcnow()
            plan_enum = SubscriptionPlan(new_plan_type)
            payment_method = None
            if payment_data and "payment_method" in payment_data:
                payment_method = PaymentMethod(payment_data["payment_method"])

            if plan_enum == SubscriptionPlan.PREMIUM_MONTHLY:
                new_end_date = effective_date + timedelta(days=30)
            elif plan_enum == SubscriptionPlan.PREMIUM_YEARLY:
                new_end_date = effective_date + timedelta(days=365)
            else:
                new_end_date = None

            update_values = {
                "plan_type": plan_enum,
                "subscription_end_date": new_end_date,
                "status": SubscriptionStatus.ACTIVE,
                "auto_renew": True,
                "updated_at": datetime.utcnow()
            }
            if payment_method is not None:
                update_values["payment_method"] = payment_method
            if payment_data and "payment_provider_id" in payment_data:
                update_values["payment_provider_id"] = payment_data["payment_provider_id"]

            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(**update_values)
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for upgrade")
                return None

            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Upgraded subscription {subscription_id} to {plan_enum.value}")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error upgrading subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to upgrade subscription: {e}")

    async def downgrade_subscription(self, subscription_id: UUID, new_plan_type: str, effective_date: Optional[datetime] = None) -> Optional[Subscription]:
        """
        Downgrade subscription to a lower plan.
        
        Args:
            subscription_id: Subscription identifier
            new_plan_type: New (lower) subscription plan
            effective_date: When the downgrade takes effect
            
        Returns:
            Optional[Subscription]: Updated subscription domain model or None if not found
        """
        try:
            if not effective_date:
                effective_date = datetime.utcnow()

            plan_enum = SubscriptionPlan(new_plan_type)
            update_values = {
                "plan_type": plan_enum,
                "updated_at": datetime.utcnow()
            }

            if plan_enum == SubscriptionPlan.FREE:
                update_values["subscription_end_date"] = None
                update_values["payment_method"] = None
                update_values["auto_renew"] = False

            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(**update_values)
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for downgrade")
                return None

            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Downgraded subscription {subscription_id} to {plan_enum.value}")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error downgrading subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to downgrade subscription: {e}")

    async def get_subscription_analytics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get subscription analytics data.
        
        Args:
            start_date: Analysis start date
            end_date: Analysis end date
            
        Returns:
            Dict containing subscription analytics data
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()

            status_query = select(
                SubscriptionModel.status,
                func.count(SubscriptionModel.subscription_id).label('count')
            ).where(
                SubscriptionModel.created_at >= start_date
            ).group_by(SubscriptionModel.status)
            status_result = await self.session.execute(status_query)
            status_counts = {row.status.value: row.count for row in status_result}

            plan_query = select(
                SubscriptionModel.plan_type,
                func.count(SubscriptionModel.subscription_id).label('count')
            ).where(
                SubscriptionModel.created_at >= start_date
            ).group_by(SubscriptionModel.plan_type)
            plan_result = await self.session.execute(plan_query)
            plan_counts = {row.plan_type.value: row.count for row in plan_result}

            trial_query = select(
                func.count(SubscriptionModel.subscription_id).label('count')
            ).where(
                and_(
                    SubscriptionModel.trial_active == True,
                    SubscriptionModel.trial_end_date > datetime.utcnow()
                )
            )
            trial_result = await self.session.execute(trial_query)
            active_trials = trial_result.scalar() or 0

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "status_breakdown": status_counts,
                "plan_breakdown": plan_counts,
                "active_trials": active_trials,
                "total_subscriptions": sum(status_counts.values())
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscription analytics: {e}")
            raise DatabaseError(f"Failed to fetch subscription analytics: {e}")

    async def get_revenue_metrics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get revenue metrics for subscriptions.
        
        Args:
            start_date: Metrics start date
            end_date: Metrics end date
            
        Returns:
            Dict containing revenue metrics
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()

            monthly_revenue_query = select(
                func.count(
                    case(
                        (SubscriptionModel.plan_type == SubscriptionPlan.PREMIUM_MONTHLY, 1)
                    )
                ).label('monthly_subs'),
                func.count(
                    case(
                        (SubscriptionModel.plan_type == SubscriptionPlan.PREMIUM_YEARLY, 1)
                    )
                ).label('yearly_subs')
            ).where(
                and_(
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    SubscriptionModel.created_at >= start_date,
                    SubscriptionModel.created_at <= end_date
                )
            )

            result = await self.session.execute(monthly_revenue_query)
            revenue_data = result.first()

            monthly_price = 9.99  # Example price
            yearly_price = 99.99  # Example price

            estimated_monthly_revenue = (revenue_data.monthly_subs * monthly_price) + \
                                      (revenue_data.yearly_subs * yearly_price / 12)

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "monthly_subscriptions": revenue_data.monthly_subs,
                "yearly_subscriptions": revenue_data.yearly_subs,
                "estimated_monthly_revenue": round(estimated_monthly_revenue, 2),
                "total_premium_subscriptions": revenue_data.monthly_subs + revenue_data.yearly_subs
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching revenue metrics: {e}")
            raise DatabaseError(f"Failed to fetch revenue metrics: {e}")

    async def get_churn_analysis(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Get churn analysis data.
        
        Args:
            period_days: Number of days for analysis period
            
        Returns:
            Dict containing churn analysis data
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days)

            cancelled_query = select(func.count(SubscriptionModel.subscription_id)).where(
                and_(
                    SubscriptionModel.status == SubscriptionStatus.CANCELLED,
                    SubscriptionModel.updated_at >= start_date,
                    SubscriptionModel.updated_at <= end_date
                )
            )

            cancelled_result = await self.session.execute(cancelled_query)
            cancelled_count = cancelled_result.scalar() or 0

            active_query = select(func.count(SubscriptionModel.subscription_id)).where(
                and_(
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    SubscriptionModel.created_at < start_date
                )
            )

            active_result = await self.session.execute(active_query)
            active_count = active_result.scalar() or 0

            churn_rate = (cancelled_count / active_count * 100) if active_count > 0 else 0

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "cancelled_subscriptions": cancelled_count,
                "active_subscriptions_start": active_count,
                "churn_rate_percentage": round(churn_rate, 2)
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching churn analysis: {e}")
            raise DatabaseError(f"Failed to fetch churn analysis: {e}")

    async def get_trial_conversion_rate(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> float:
        """
        Get trial to paid subscription conversion rate.
        
        Args:
            start_date: Analysis start date
            end_date: Analysis end date
            
        Returns:
            float: Conversion rate percentage
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()

            trials_query = select(func.count(SubscriptionModel.subscription_id)).where(
                and_(
                    SubscriptionModel.trial_start_date >= start_date,
                    SubscriptionModel.trial_start_date <= end_date
                )
            )
            trials_result = await self.session.execute(trials_query)
            total_trials = trials_result.scalar() or 0

            converted_query = select(func.count(SubscriptionModel.subscription_id)).where(
                and_(
                    SubscriptionModel.trial_start_date >= start_date,
                    SubscriptionModel.trial_start_date <= end_date,
                    SubscriptionModel.trial_active == False,
                    SubscriptionModel.plan_type.in_([
                        SubscriptionPlan.PREMIUM_MONTHLY,
                        SubscriptionPlan.PREMIUM_YEARLY
                    ]),
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE
                )
            )
            converted_result = await self.session.execute(converted_query)
            converted_trials = converted_result.scalar() or 0

            conversion_rate = (converted_trials / total_trials * 100) if total_trials > 0 else 0
            return round(conversion_rate, 2)
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching trial conversion rate: {e}")
            raise DatabaseError(f"Failed to fetch trial conversion rate: {e}")

    async def bulk_update_billing_cycle(self, subscription_ids: List[UUID], new_billing_date: datetime) -> int:
        """
        Bulk update billing cycle for multiple subscriptions.
        
        Args:
            subscription_ids: List of subscription IDs to update
            new_billing_date: New billing date
            
        Returns:
            int: Number of subscriptions updated
        """
        try:
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id.in_(subscription_ids)
            ).values(
                subscription_end_date=new_billing_date,
                updated_at=datetime.utcnow()
            )
            result = await self.session.execute(query)
            updated_count = result.rowcount

            logger.info(f"Bulk updated billing cycle for {updated_count} subscriptions")
            return updated_count
        except SQLAlchemyError as e:
            logger.error(f"Database error in bulk billing cycle update: {e}")
            raise DatabaseError(f"Failed to bulk update billing cycles: {e}")

    async def get_subscriptions_for_renewal(self, days_ahead: int = 7) -> List[Subscription]:
        """
        Get subscriptions due for renewal within specified days.
        
        Args:
            days_ahead: Number of days to look ahead for renewal
            
        Returns:
            List[Subscription]: List of subscription domain models due for renewal
        """
        try:
            renewal_date = datetime.utcnow() + timedelta(days=days_ahead)
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    SubscriptionModel.auto_renew == True,
                    SubscriptionModel.subscription_end_date <= renewal_date,
                    SubscriptionModel.subscription_end_date > datetime.utcnow()
                )
            )
            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [Subscription(**self._subscription_to_dict(sub)) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscriptions for renewal: {e}")
            raise DatabaseError(f"Failed to fetch subscriptions for renewal: {e}")

    async def process_subscription_renewal(self, subscription_id: UUID, payment_successful: bool, payment_data: Optional[Dict[str, Any]] = None) -> Optional[Subscription]:
        """
        Process subscription renewal.
        
        Args:
            subscription_id: Subscription identifier
            payment_successful: Whether payment was successful
            payment_data: Optional payment data
            
        Returns:
            Optional[Subscription]: Renewed subscription domain model or None if not found
        """
        try:
            query = select(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            )
            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.warning(f"No subscription found with ID {subscription_id} for renewal")
                return None

            if not subscription.auto_renew:
                logger.warning(f"Subscription {subscription_id} does not have auto-renew enabled")
                return None

            if not payment_successful:
                logger.warning(f"Payment for subscription {subscription_id} renewal failed")
                return None

            plan_type = subscription.plan_type
            if plan_type == SubscriptionPlan.PREMIUM_MONTHLY:
                renewal_period_days = 30
            elif plan_type == SubscriptionPlan.PREMIUM_YEARLY:
                renewal_period_days = 365
            else:
                renewal_period_days = 30
            current_end = subscription.subscription_end_date or datetime.utcnow()
            new_end_date = current_end + timedelta(days=renewal_period_days)

            update_query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                subscription_end_date=new_end_date,
                status=SubscriptionStatus.ACTIVE.value,
                updated_at=datetime.utcnow()
            )
            await self.session.execute(update_query)
            
            updated_subscription = await self.get_by_id(subscription_id)
            logger.info(f"Renewed subscription {subscription_id} for {renewal_period_days} days")
            return updated_subscription
        except SQLAlchemyError as e:
            logger.error(f"Database error processing renewal for subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to process subscription renewal: {e}")

    async def exists_by_user_id(self, user_id: UUID) -> bool:
        """
        Check if a subscription exists for the given user.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if subscription exists, False otherwise
        """
        try:
            query = select(func.count(SubscriptionModel.subscription_id)).where(
                SubscriptionModel.user_id == user_id
            )
            result = await self.session.execute(query)
            count = result.scalar() or 0
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Database error checking subscription existence for user {user_id}: {e}")
            raise DatabaseError(f"Failed to check subscription existence: {e}")

    async def count_by_plan_type(self, plan_type: str) -> int:
        """
        Count subscriptions by plan type.
        
        Args:
            plan_type: Subscription plan type
            
        Returns:
            int: Count of subscriptions with the specified plan type
        """
        try:
            plan_enum = SubscriptionPlan(plan_type)
            query = select(func.count(SubscriptionModel.subscription_id)).where(
                SubscriptionModel.plan_type == plan_enum
            )
            result = await self.session.execute(query)
            count = result.scalar() or 0
            return count
        except SQLAlchemyError as e:
            logger.error(f"Database error counting subscriptions by plan type {plan_type}: {e}")
            raise DatabaseError(f"Failed to count subscriptions by plan type: {e}")

    async def count_by_status(self, status: str) -> int:
        """
        Count subscriptions by status.
        
        Args:
            status: Subscription status
            
        Returns:
            int: Count of subscriptions with the specified status
        """
        try:
            status_enum = SubscriptionStatus(status)
            query = select(func.count(SubscriptionModel.subscription_id)).where(
                SubscriptionModel.status == status_enum
            )
            result = await self.session.execute(query)
            count = result.scalar() or 0
            return count
        except SQLAlchemyError as e:
            logger.error(f"Database error counting subscriptions by status {status}: {e}")
            raise DatabaseError(f"Failed to count subscriptions by status: {e}")

    async def update_subscription_status(
        self,
        subscription_id: UUID,
        status: SubscriptionStatus,
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Update subscription status.
        
        Args:
            subscription_id: Subscription identifier
            status: New subscription status
            updated_by: Optional identifier of updater
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                status=status,
                updated_at=datetime.utcnow()
            )

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for status update")
                return False

            logger.info(f"Updated subscription {subscription_id} status to {status.value}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error updating subscription {subscription_id} status: {e}")
            raise DatabaseError(f"Failed to update subscription status: {e}")

    async def update_subscription_plan(
        self,
        subscription_id: UUID,
        plan_type: SubscriptionPlan,
        payment_method: Optional[PaymentMethod] = None,
        auto_renew: Optional[bool] = None
    ) -> bool:
        """
        Update subscription plan and related settings.
        
        Args:
            subscription_id: Subscription identifier
            plan_type: New subscription plan
            payment_method: Optional new payment method
            auto_renew: Optional auto-renew setting
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            update_values = {
                "plan_type": plan_type,
                "updated_at": datetime.utcnow()
            }

            if payment_method is not None:
                update_values["payment_method"] = payment_method
            
            if auto_renew is not None:
                update_values["auto_renew"] = auto_renew

            if plan_type == SubscriptionPlan.PREMIUM_MONTHLY:
                update_values["subscription_end_date"] = datetime.utcnow() + timedelta(days=30)
            elif plan_type == SubscriptionPlan.PREMIUM_YEARLY:
                update_values["subscription_end_date"] = datetime.utcnow() + timedelta(days=365)
            elif plan_type == SubscriptionPlan.FREE:
                update_values["subscription_end_date"] = None

            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(**update_values)

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for plan update")
                return False

            logger.info(f"Updated subscription {subscription_id} plan to {plan_type.value}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error updating subscription {subscription_id} plan: {e}")
            raise DatabaseError(f"Failed to update subscription plan: {e}")

    async def activate_trial(
        self,
        subscription_id: UUID,
        trial_days: int = 7
    ) -> bool:
        """
        Activate free trial for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            trial_days: Number of trial days
            
        Returns:
            bool: True if trial activation successful, False otherwise
        """
        try:
            trial_start = datetime.utcnow()
            trial_end = trial_start + timedelta(days=trial_days)

            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                trial_active=True,
                trial_start_date=trial_start,
                trial_end_date=trial_end,
                updated_at=datetime.utcnow()
            )

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for trial activation")
                return False

            logger.info(f"Activated {trial_days}-day trial for subscription {subscription_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error activating trial for subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to activate trial: {e}")

    async def end_trial(self, subscription_id: UUID) -> bool:
        """
        End free trial for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            bool: True if trial end successful, False otherwise
        """
        try:
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                trial_active=False,
                trial_end_date=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for trial end")
                return False

            logger.info(f"Ended trial for subscription {subscription_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error ending trial for subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to end trial: {e}")

    async def extend_subscription(
        self,
        subscription_id: UUID,
        extend_days: int
    ) -> bool:
        """
        Extend subscription end date.
        
        Args:
            subscription_id: Subscription identifier
            extend_days: Number of days to extend
            
        Returns:
            bool: True if extension successful, False otherwise
        """
        try:
            query = select(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            )
            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.warning(f"No subscription found with ID {subscription_id} for extension")
                return False

            current_end = subscription.subscription_end_date or datetime.utcnow()
            new_end_date = current_end + timedelta(days=extend_days)

            update_query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                subscription_end_date=new_end_date,
                updated_at=datetime.utcnow()
            )

            await self.session.execute(update_query)
            
            logger.info(f"Extended subscription {subscription_id} by {extend_days} days")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error extending subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to extend subscription: {e}")

    async def get_expiring_subscriptions(
        self,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get subscriptions expiring within specified days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of dictionaries containing expiring subscription data
        """
        try:
            expiry_date = datetime.utcnow() + timedelta(days=days_ahead)
            
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.subscription_end_date <= expiry_date,
                    SubscriptionModel.subscription_end_date > datetime.utcnow(),
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE
                )
            )

            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [self._subscription_to_dict(sub) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching expiring subscriptions: {e}")
            raise DatabaseError(f"Failed to fetch expiring subscriptions: {e}")

    async def get_expired_subscriptions(
        self,
        days_past: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get expired subscriptions.
        
        Args:
            days_past: Number of days in the past to consider
            
        Returns:
            List of dictionaries containing expired subscription data
        """
        try:
            logger.info(f"step3")
            cutoff_date = datetime.utcnow() - timedelta(days=days_past)
            
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.subscription_end_date < datetime.utcnow(),
                    SubscriptionModel.subscription_end_date >= cutoff_date,
                    SubscriptionModel.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED])
                )
            )

            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [self._subscription_to_dict(sub) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching expired subscriptions: {e}")
            raise DatabaseError(f"Failed to fetch expired subscriptions: {e}")

    async def is_subscription_active(self, user_id: UUID) -> bool:
        """
        Check if user has an active subscription.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if user has active subscription, False otherwise
        """
        try:
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    or_(
                        SubscriptionModel.subscription_end_date.is_(None),
                        SubscriptionModel.subscription_end_date > datetime.utcnow()
                    )
                )
            )

            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            return subscription is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking active subscription for user {user_id}: {e}")
            raise DatabaseError(f"Failed to check subscription status: {e}")

    async def is_premium_user(self, user_id: UUID) -> bool:
        """
        Check if user has premium subscription.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if user has premium subscription, False otherwise
        """
        try:
            query = select(SubscriptionModel).where(
                and_(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    SubscriptionModel.plan_type.in_([
                        SubscriptionPlan.PREMIUM_MONTHLY,
                        SubscriptionPlan.PREMIUM_YEARLY
                    ]),
                    or_(
                        SubscriptionModel.subscription_end_date.is_(None),
                        SubscriptionModel.subscription_end_date > datetime.utcnow()
                    )
                )
            )

            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()

            return subscription is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking premium status for user {user_id}: {e}")
            raise DatabaseError(f"Failed to check premium status: {e}")

    async def get_subscription_history(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get subscription history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing subscription history data
        """
        try:
            logger.info(f"step4")
            query = select(SubscriptionModel).where(
                SubscriptionModel.user_id == user_id
            ).order_by(
                SubscriptionModel.created_at.desc()
            ).limit(limit)

            result = await self.session.execute(query)
            subscriptions = result.scalars().all()

            return [self._subscription_to_dict(sub) for sub in subscriptions]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching subscription history for user {user_id}: {e}")
            raise DatabaseError(f"Failed to fetch subscription history: {e}")

    async def update_auto_renew(
        self,
        subscription_id: UUID,
        auto_renew: bool
    ) -> bool:
        """
        Update auto-renewal setting for subscription.
        
        Args:
            subscription_id: Subscription identifier
            auto_renew: New auto-renew setting
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                auto_renew=auto_renew,
                updated_at=datetime.utcnow()
            )

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for auto-renew update")
                return False

            logger.info(f"Updated auto-renew setting for subscription {subscription_id} to {auto_renew}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error updating auto-renew for subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to update auto-renew setting: {e}")

    async def delete_subscription(self, subscription_id: UUID) -> bool:
        """
        Soft delete a subscription (for GDPR compliance).
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            query = update(SubscriptionModel).where(
                SubscriptionModel.subscription_id == subscription_id
            ).values(
                status=SubscriptionStatus.CANCELLED,
                auto_renew=False,
                subscription_end_date=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"No subscription found with ID {subscription_id} for deletion")
                return False

            logger.info(f"Soft deleted subscription {subscription_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting subscription {subscription_id}: {e}")
            raise DatabaseError(f"Failed to delete subscription: {e}")

    def _subscription_to_dict(self, subscription: SubscriptionModel) -> Dict[str, Any]:
        """
        Convert subscription model to dictionary.
        
        Args:
            subscription: SubscriptionModel model instance
            
        Returns:
            Dict containing subscription data
        """
        return {
            "subscription_id": str(subscription.subscription_id),
            "user_id": str(subscription.user_id),
            "plan_type": subscription.plan_type.value,
            "status": subscription.status.value,
            "trial_active": subscription.trial_active,
            "trial_start_date": subscription.trial_start_date,
            "trial_end_date": subscription.trial_end_date,
            "subscription_start_date": subscription.subscription_start_date,
            "subscription_end_date": subscription.subscription_end_date,
            "payment_method": subscription.payment_method.value if subscription.payment_method else PaymentMethod.NONE.value,
            "auto_renew": subscription.auto_renew,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at
        }
