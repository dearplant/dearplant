# 📄 File: app/modules/user_management/domain/repositories/user_repository.py
# 🧭 Purpose (Layman Explanation): 
# Defines the contract for how to save, find, update, and delete user information in the database without specifying the actual database technology
# 🧪 Purpose (Technical Summary): 
# Repository interface defining data access operations for User entities following Repository pattern and dependency inversion principle
# 🔗 Dependencies: 
# Domain models (User, UserStatus, SubscriptionTier), typing, abc
# 🔄 Connected Modules / Calls From: 
# Domain services, infrastructure implementations, application handlers

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from ..models.user import User, UserStatus, SubscriptionTier


class UserRepository(ABC):
    """
    Repository interface for User entity data access operations.
    
    Defines the contract for User data persistence following the Repository pattern.
    This interface abstracts data access from business logic, enabling:
    - Dependency inversion (domain doesn't depend on infrastructure)
    - Easy testing with mock implementations  
    - Support for multiple storage backends
    - Consistent data access patterns
    
    Implementation Notes:
    - Concrete implementations are in infrastructure layer
    - Methods return domain entities (User), not database models
    - All operations are async for non-blocking I/O
    - Repository handles entity-to-model mapping
    """
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user.
        
        Args:
            user: User entity to create
            
        Returns:
            Created User entity with generated fields populated
            
        Raises:
            ValueError: If user with email already exists
            RepositoryError: If database operation fails
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID to find
            
        Returns:
            User entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: Email address to find
            
        Returns:
            User entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_provider_id(self, provider: str, provider_id: str) -> Optional[User]:
        """
        Get user by OAuth provider ID.
        
        Supports OAuth integration from core doc Authentication functionality.
        
        Args:
            provider: OAuth provider (google/apple)
            provider_id: Provider-specific user ID
            
        Returns:
            User entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Update existing user.
        
        Args:
            user: User entity with updated data
            
        Returns:
            Updated User entity
            
        Raises:
            ValueError: If user not found
            RepositoryError: If database operation fails
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """
        Hard delete user by ID.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        pass
    
    @abstractmethod
    async def get_by_status(
        self, 
        status: UserStatus, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[User]:
        """
        Get users by status with pagination.
        
        Args:
            status: User status to filter by
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities matching status
        """
        pass
    
    @abstractmethod
    async def get_by_subscription_tiers(
        self, 
        tiers: List[SubscriptionTier], 
        limit: int = 100, 
        offset: int = 0
    ) -> List[User]:
        """
        Get users by subscription tiers with pagination.
        
        Args:
            tiers: List of subscription tiers to filter by
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities with matching subscription tiers
        """
        pass
    
    @abstractmethod
    async def get_users_with_failed_logins(
        self, 
        min_attempts: int = 3,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Get users with failed login attempts.
        
        Supports security monitoring and account lockout from core doc.
        
        Args:
            min_attempts: Minimum failed attempts to include
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities with failed login attempts
        """
        pass
    
    @abstractmethod
    async def get_locked_accounts(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Get locked user accounts.
        
        Supports account lockout management from core doc.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of locked User entities
        """
        pass
    
    @abstractmethod
    async def get_unverified_users(
        self,
        days_since_creation: int = 7,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Get users with unverified emails.
        
        Supports email verification follow-up from core doc.
        
        Args:
            days_since_creation: Days since account creation
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities with unverified emails
        """
        pass
    
    @abstractmethod
    async def search_users(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[User]:
        """
        Search users by email or display name.
        
        Args:
            query: Search query string
            filters: Additional filters (status, role, etc.)
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities matching search criteria
        """
        pass
    
    @abstractmethod
    async def count_by_status(self, status: UserStatus) -> int:
        """
        Count users by status.
        
        Args:
            status: User status to count
            
        Returns:
            Number of users with given status
        """
        pass
    
    @abstractmethod
    async def count_by_subscription_tier(self, tier: SubscriptionTier) -> int:
        """
        Count users by subscription tier.
        
        Args:
            tier: Subscription tier to count
            
        Returns:
            Number of users with given subscription tier
        """
        pass
    
    @abstractmethod
    async def get_user_registration_stats(
        self,
        days: int = 30
    ) -> Dict[str, int]:
        """
        Get user registration statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with registration statistics
        """
        pass
    
    @abstractmethod
    async def bulk_update_status(
        self,
        user_ids: List[str],
        status: UserStatus
    ) -> int:
        """
        Bulk update user status.
        
        Args:
            user_ids: List of user IDs to update
            status: New status to set
            
        Returns:
            Number of users updated
        """
        pass
    
    @abstractmethod
    async def get_users_by_last_login(
        self,
        days_inactive: int = 30,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Get users by last login date.
        
        Supports user engagement analysis and retention campaigns.
        
        Args:
            days_inactive: Days since last login
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User entities matching criteria
        """
        pass
    
    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email.
        
        Args:
            email: Email address to check
            
        Returns:
            True if user exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists_by_id(self, user_id: str) -> bool:
        """
        Check if user exists by ID.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user exists, False otherwise
        """
        pass