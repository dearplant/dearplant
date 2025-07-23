# 📄 File: app/shared/infrastructure/database/session.py
#
# 🧭 Purpose (Layman Explanation):
# Manages database sessions (like conversations with the database) ensuring each request
# gets its own clean session and properly handles database transactions and rollbacks.
#
# 🧪 Purpose (Technical Summary):
# Implements async SQLAlchemy session management with dependency injection for FastAPI,
# transaction handling, and session lifecycle management across all database operations.
#
# 🔗 Dependencies:
# - sqlalchemy.ext.asyncio (AsyncSession, sessionmaker)
# - app/shared/infrastructure/database/connection.py (database engine)
# - fastapi (for dependency injection)
#
# 🔄 Connected Modules / Calls From:
# - app/shared/core/dependencies.py (FastAPI dependencies)
# - All module repository implementations (database sessions)
# - Background job tasks (database access)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy import exc
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any, Dict
import logging
from fastapi import HTTPException, status

from app.shared.infrastructure.database.connection import get_database_engine, db_manager
from app.shared.core.exceptions import DatabaseError, TransactionError

logger = logging.getLogger(__name__)

class DatabaseSessionManager:
    """
    Manages database sessions with transaction handling and automatic cleanup.
    """
    
    def __init__(self):
        self._session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the session factory with database engine."""
        try:
            engine = await get_database_engine()
            
            self._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Keep objects accessible after commit
                autoflush=True,          # Auto-flush before queries
                autocommit=False,        # Manual transaction control
            )
            
            self._initialized = True
            logger.info("Database session factory initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database session factory: {e}")
            raise DatabaseError(f"Session initialization failed: {e}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with automatic transaction management.
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            DatabaseError: If session creation fails
            TransactionError: If transaction management fails
        """
        logging.info(f"self._initialized {self._initialized} self._session_factory {self._session_factory}")
        if not self._initialized or self._session_factory is None:
            raise DatabaseError("Session manager not initialized")
        
        session: AsyncSession = self._session_factory()
        
        try:
            logger.debug("Database session created")
            yield session
            
            # Commit the transaction if no exceptions occurred
            await session.commit()
            logger.debug("Database transaction committed successfully")
            
        except exc.SQLAlchemyError as e:
            # Rollback on SQLAlchemy errors
            await session.rollback()
            logger.error(f"Database error occurred, transaction rolled back: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
            
        except Exception as e:
            # Rollback on any other exceptions
            await session.rollback()
            logger.error(f"Unexpected error occurred, transaction rolled back: {e}")
            raise TransactionError(f"Transaction failed: {e}")
            
        finally:
            # Always close the session
            await session.close()
            logger.debug("Database session closed")
    
    @asynccontextmanager
    async def get_read_only_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a read-only database session (no automatic commit).
        
        Yields:
            AsyncSession: Read-only database session
        """
        if not self._initialized or self._session_factory is None:
            raise DatabaseError("Session manager not initialized")
        
        session: AsyncSession = self._session_factory()
        
        try:
            logger.debug("Read-only database session created")
            yield session
            
        except Exception as e:
            logger.error(f"Read-only session error: {e}")
            raise DatabaseError(f"Read operation failed: {e}")
            
        finally:
            await session.close()
            logger.debug("Read-only database session closed")
    
    async def execute_in_transaction(self, operation, *args, **kwargs) -> Any:
        """
        Execute an operation within a managed transaction.
        
        Args:
            operation: Callable that takes session as first argument
            *args: Additional arguments for the operation
            **kwargs: Additional keyword arguments for the operation
            
        Returns:
            Result of the operation
        """
        async with self.get_session() as session:
            try:
                result = await operation(session, *args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Transaction operation failed: {e}")
                raise
    
    async def bulk_operation(self, operations: list) -> list:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of (operation, args, kwargs) tuples
            
        Returns:
            List of operation results
        """
        results = []
        
        async with self.get_session() as session:
            try:
                for operation, args, kwargs in operations:
                    result = await operation(session, *args, **kwargs)
                    results.append(result)
                
                logger.info(f"Bulk operation completed successfully ({len(operations)} operations)")
                return results
                
            except Exception as e:
                logger.error(f"Bulk operation failed: {e}")
                raise TransactionError(f"Bulk operation failed: {e}")
    
    def is_initialized(self) -> bool:
        """Check if session manager is initialized."""
        return self._initialized


# Global session manager instance
session_manager = DatabaseSessionManager()


async def initialize_sessions() -> None:
    """Initialize the global database session manager."""
    print("🔥 initialize_sessions() called")
    await session_manager.initialize()


# FastAPI dependency for getting database sessions
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides database sessions.
    
    This function is used as a dependency in FastAPI route handlers
    to automatically inject database sessions.
    
    Usage:
        @router.post("/users/")
        async def create_user(
            user_data: UserCreate,
            db: AsyncSession = Depends(get_db_session)
        ):
            # Use db session here
    
    Yields:
        AsyncSession: Database session
    """
    async with session_manager.get_session() as session:
        try:
            yield session
        except HTTPException:
            # Re-raise HTTP exceptions without wrapping
            raise
        except DatabaseError:
            # Re-raise database errors without wrapping
            raise
        except Exception as e:
            # Convert unexpected errors to HTTP 500
            logger.error(f"Unexpected error in database session dependency: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal database error: {str(e)}"
            )


async def get_read_only_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides read-only database sessions.
    
    Use this dependency for read-only operations like GET requests
    to avoid unnecessary transaction overhead.
    
    Yields:
        AsyncSession: Read-only database session
    """
    async with session_manager.get_read_only_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Error in read-only database session dependency: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database read error"
            )


# Context manager for manual session management
@asynccontextmanager
async def database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for manual database session management.
    
    Use this when you need manual control over database sessions
    outside of FastAPI route handlers.
    
    Example:
        async with database_session() as db:
            # Perform database operations
            user = await user_repository.get_by_id(db, user_id)
    
    Yields:
        AsyncSession: Database session
    """
    async with session_manager.get_session() as session:
        yield session


@asynccontextmanager
async def read_only_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for read-only database session management.
    
    Yields:
        AsyncSession: Read-only database session
    """
    async with session_manager.get_read_only_session() as session:
        yield session


# Utility functions for transaction management
async def execute_in_transaction(operation, *args, **kwargs) -> Any:
    """
    Execute an operation within a managed transaction.
    
    Args:
        operation: Async function that takes session as first argument
        *args: Additional arguments for the operation
        **kwargs: Additional keyword arguments for the operation
        
    Returns:
        Result of the operation
    """
    return await session_manager.execute_in_transaction(operation, *args, **kwargs)


async def execute_bulk_operations(operations: list) -> list:
    """
    Execute multiple operations in a single transaction.
    
    Args:
        operations: List of (operation, args, kwargs) tuples
        
    Returns:
        List of operation results
    """
    return await session_manager.bulk_operation(operations)


# Session health check
async def session_health_check() -> Dict[str, Any]:
    """
    Perform session health check by creating and closing a session.
    
    Returns:
        Dict containing session health information
    """
    try:
        async with session_manager.get_read_only_session() as session:
            # Simple query to test session
            result = await session.execute("SELECT 1")
            await result.fetchone()
            
        return {
            "status": "healthy",
            "initialized": session_manager.is_initialized(),
            "message": "Session factory working correctly"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "initialized": session_manager.is_initialized(),
            "error": str(e),
            "message": "Session factory error"
        }