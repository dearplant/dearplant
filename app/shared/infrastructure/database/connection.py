# 📄 File: app/shared/infrastructure/database/connection.py
#
# 🧭 Purpose (Layman Explanation):
# Manages the connection to our PostgreSQL database, like making sure we can talk to our data storage
# and handling multiple connections efficiently without overwhelming the database.
#
# 🧪 Purpose (Technical Summary):
# Implements async SQLAlchemy database connection management with connection pooling, health checks,
# and retry logic for robust database connectivity across all modules.
#
# 🔗 Dependencies:
# - sqlalchemy (async engine and sessions)
# - app/shared/config/settings.py (database configuration)
# - asyncpg (PostgreSQL async driver)
#
# 🔄 Connected Modules / Calls From:
# - app/shared/infrastructure/database/session.py (session management)
# - All module repository implementations (database access)
# - app/monitoring/health_checks.py (database health monitoring)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import event, text, pool
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
import asyncio
import logging
from typing import Optional, Dict, Any
from app.shared.config.settings import get_settings
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker] = None

class DatabaseConnectionManager:
    """
    Manages PostgreSQL database connections with connection pooling,
    health monitoring, and automatic retry logic.
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._connection_params = self._build_connection_params()
        self._health_check_query = text("SELECT 1")
        self._retry_attempts = 3
        self._retry_delay = 1.0
        
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build SQLAlchemy connection parameters from settings."""
        return {
            "url": settings.database_url,
            "echo": settings.debug,
            "echo_pool": settings.debug,
            "pool_pre_ping": True,  # Validate connections before use
            "pool_recycle": 3600,   # Recycle connections every hour
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_timeout": 30,
            "connect_args": {
                "server_settings": {
                    "application_name": "plant_care_backend",
                    "jit": "off"  # Disable JIT for better connection stability
                },
                "command_timeout": 60,
                "statement_cache_size": 0,  # Disable prepared statement cache
            }
        }
    
    async def initialize(self) -> None:
        """Initialize database engine with connection pooling."""
        if self._engine is not None:
            logger.warning("Database engine already initialized")
            return
            
        try:
            logger.info("Initializing database connection pool...")
            self._engine = create_async_engine(**self._connection_params)
            
            # Register connection event listeners
            self._register_connection_events()
            
            # Perform initial health check
            await self.health_check()
            
            logger.info(
                f"Database connection pool initialized successfully. "
                f"Pool size: {settings.database_pool_size}, "
                f"Max overflow: {settings.database_max_overflow}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def _register_connection_events(self) -> None:
        """Register SQLAlchemy connection event listeners."""
        if self._engine is None:
            return
            
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Configure connection-specific settings."""
            pass  # PostgreSQL doesn't need pragma settings
            
        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout for monitoring."""
            if settings.debug:
                logger.debug("Connection checked out from pool")
                
        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin for monitoring."""
            if settings.debug:
                logger.debug("Connection checked in to pool")
    
    async def health_check(self) -> dict:
        """
        Perform database health check and return structured status.
        """
        if self._engine is None:
            logger.error("Database engine not initialized")
            return {
                "status": "unhealthy",
                "error": "Database engine not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }

        for attempt in range(self._retry_attempts):
            try:
                async with self._engine.begin() as conn:
                    result = await conn.execute(self._health_check_query)
                    result.scalar()

                logger.debug("Database health check passed")
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logger.warning(
                    f"Database health check failed (attempt {attempt + 1}/{self._retry_attempts}): {e}"
                )
                if attempt < self._retry_attempts - 1:
                    await asyncio.sleep(self._retry_delay * (2 ** attempt))

        logger.error("Database health check failed after all retry attempts")
        return {
            "status": "unhealthy",
            "error": "Database health check failed after all retry attempts",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_connection_info(self) -> Dict[str, Any]:
        """
        Get current connection pool information for monitoring.
        
        Returns:
            Dict containing pool statistics
        """
        if self._engine is None or self._engine.pool is None:
            return {"status": "not_initialized"}
            
        pool = self._engine.pool
        return {
            "status": "initialized",
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a database connection with automatic cleanup.
        
        Yields:
            AsyncConnection: Database connection
        """
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
            
        async with self._engine.begin() as conn:
            try:
                yield conn
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise
    
    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Execute a raw SQL query with parameters.
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            Query result
        """
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
            
        async with self._engine.begin() as conn:
            result = await conn.execute(text(query), parameters or {})
            return result
    
    async def close(self) -> None:
        """Close database engine and all connections."""
        if self._engine is None:
            logger.warning("Database engine not initialized, nothing to close")
            return
            
        try:
            logger.info("Closing database connection pool...")
            await self._engine.dispose()
            self._engine = None
            logger.info("Database connection pool closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing database connection pool: {e}")
            raise
    
    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the SQLAlchemy async engine."""
        return self._engine
    
    @property
    def is_initialized(self) -> bool:
        """Check if database engine is initialized."""
        return self._engine is not None


# Global database connection manager instance
db_manager = DatabaseConnectionManager()


async def initialize_database() -> None:
    """Initialize the global database connection manager."""
    try:
        logger.info("Starting database initialization...")
        await db_manager.initialize()
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise


async def close_database() -> None:
    """Close the global database connection manager."""
    await db_manager.close()


async def get_database_engine() -> AsyncEngine:
    """
    Get the database engine instance.
    
    Returns:
        AsyncEngine: SQLAlchemy async engine
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if not db_manager.is_initialized:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    
    return db_manager.engine


async def database_health_check() -> dict:
    """
    Perform database health check.
    
    Returns:
        bool: True if database is healthy
    """
    return await db_manager.health_check()


async def get_connection_info() -> Dict[str, Any]:
    """
    Get database connection pool information.
    
    Returns:
        Dict containing pool statistics
    """
    return await db_manager.get_connection_info()

def _create_database_engine(settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        echo_pool=settings.debug,
        pool_pre_ping=True,
        pool_recycle=settings.database_pool_recycle,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        connect_args={
            "server_settings": {
                "application_name": "plant_care_backend",
                "jit": "off"
            },
            "command_timeout": 60,
            "statement_cache_size": 0,
        },
    )

async def init_database() -> bool:
    """
    Initialize database connection and verify connectivity
    
    Returns:
        True if initialization successful
        
    Raises:
        Exception: If database initialization fails
    """
    global _engine, _session_maker
    if _engine is not None:
        logger.warning("Database already initialized, skipping...")
        return True
    try:
        logger.info("Initializing database connection via init_database...")
        await initialize_database()  # Reuse db_manager.initialize()
        _engine = db_manager.engine
        _session_maker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        await _test_database_connection()
        logger.info("✅ Database connection initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        if _engine:
            await _engine.dispose()
            _engine = None
            _session_maker = None
        raise


async def close_database() -> None:
    """
    Close database connection and cleanup resources
    """
    global _engine, _session_maker
    
    if _engine is None:
        logger.warning("Database not initialized, nothing to close")
        return
    
    try:
        logger.info("Closing database connection...")
        
        # Dispose of engine (closes all connections)
        await _engine.dispose()
        
        # Clear global references
        _engine = None
        _session_maker = None
        
        logger.info("✅ Database connection closed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error closing database connection: {e}")
        raise


async def _test_database_connection() -> None:
    """Test database connection with a simple query"""
    if not _engine:
        raise RuntimeError("Database engine not initialized")
    
    try:
        async with _engine.begin() as conn:
            # Test basic connectivity
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value != 1:
                raise Exception("Database connectivity test failed")
            
            logger.info("Database connectivity test passed")
            
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise