# 📄 File: app/shared/config/database.py
#
# 🧭 Purpose (Layman Explanation):
# Configuration for connecting to our Plant Care database, managing connections efficiently,
# and ensuring our app can handle multiple users accessing plant data simultaneously.
#
# 🧪 Purpose (Technical Summary):
# SQLAlchemy async database configuration with connection pooling, session management,
# and environment-specific database settings for PostgreSQL via Supabase.
#
# 🔗 Dependencies:
# - SQLAlchemy async engine and session
# - app.shared.config.settings
# - PostgreSQL driver (asyncpg)
#
# 🔄 Connected Modules / Calls From:
# - app.shared.infrastructure.database.connection
# - Database repository implementations
# - Migration and initialization scripts

from typing import Any, Dict

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .settings import get_settings

settings = get_settings()


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

class DatabaseConfig:
    """Database configuration class with environment-specific settings."""
    
    def __init__(self):
        self.settings = settings
        self._async_engine: AsyncEngine | None = None
        self._async_session_factory: sessionmaker[AsyncSession] | None = None
    
    @property
    def database_url(self) -> str:
        """Get the database URL for async connections."""
        return self.settings.database_url
    
    @property
    def engine_kwargs(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration based on environment."""
        
        base_config = {
            "echo": self.settings.DEBUG and self.settings.is_development,
            "future": True,
            "connect_args": {
                "server_settings": {
                    "application_name": f"{self.settings.APP_NAME}_{self.settings.ENVIRONMENT}",
                    "jit": "off",  # Disable JIT for better connection times
                }
            },
        }
        
        # Environment-specific configurations
        if self.settings.is_testing:
            # Use NullPool for testing to avoid connection issues
            base_config.update({
                "poolclass": NullPool,
                "isolation_level": "AUTOCOMMIT",
            })
        else:
            # Production and development pool configuration
            base_config.update({
                "poolclass": QueuePool,
                "pool_size": self.settings.DB_POOL_SIZE,
                "max_overflow": self.settings.DB_MAX_OVERFLOW,
                "pool_timeout": self.settings.DB_POOL_TIMEOUT,
                "pool_recycle": self.settings.DB_POOL_RECYCLE,
                "pool_pre_ping": True,  # Verify connections before use
            })
            
            # Additional production optimizations
            if self.settings.is_production:
                base_config["connect_args"].update({
                    "command_timeout": 30,
                    "server_settings": {
                        **base_config["connect_args"]["server_settings"],
                        "timezone": "UTC",
                        "statement_timeout": "300000",  # 5 minutes
                        "idle_in_transaction_session_timeout": "300000",
                    }
                })
        
        return base_config
    
    def create_async_engine(self) -> AsyncEngine:
        """Create and configure async database engine."""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.database_url,
                **self.engine_kwargs
            )
        return self._async_engine
    
    def create_async_session_factory(self) -> sessionmaker[AsyncSession]:
        """Create async session factory."""
        if self._async_session_factory is None:
            engine = self.create_async_engine()
            self._async_session_factory = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,  # Manual flush control for better performance
                autocommit=False,
            )
        return self._async_session_factory
    
    async def close_async_engine(self):
        """Close the async database engine."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_factory = None


# =============================================================================
# DATABASE MODELS BASE CLASS
# =============================================================================

# Naming convention for database constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


class DatabaseBase(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Provides common functionality and metadata configuration
    for all database models in the Plant Care application.
    """
    metadata = metadata
    
    # Common table configuration
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }


# =============================================================================
# GLOBAL DATABASE CONFIGURATION INSTANCE
# =============================================================================

# Global database configuration instance
db_config = DatabaseConfig()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_async_engine() -> AsyncEngine:
    """Get the async database engine."""
    return db_config.create_async_engine()


def get_async_session_factory() -> sessionmaker[AsyncSession]:
    """Get the async session factory."""
    return db_config.create_async_session_factory()


async def get_async_session() -> AsyncSession:
    """
    Get an async database session.
    
    This function should be used with dependency injection
    in FastAPI routes and services.
    """
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# DATABASE HEALTH CHECK
# =============================================================================

async def check_database_health() -> Dict[str, Any]:
    """
    Check database connectivity and performance.
    
    Returns:
        Dict containing database health status and metrics
    """
    try:
        engine = get_async_engine()
        
        # Test basic connectivity
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1 as test, NOW() as timestamp")
            row = result.fetchone()
            
            # Get connection pool status
            pool = engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "invalid": pool.invalid(),
                "overflow": pool.overflow(),
            }
            
            return {
                "status": "healthy",
                "test_query": row.test if row else None,
                "timestamp": row.timestamp.isoformat() if row else None,
                "pool_status": pool_status,
                "database_url": engine.url.render_as_string(hide_password=True),
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "type": type(e).__name__,
        }


# =============================================================================
# TESTING UTILITIES
# =============================================================================

async def create_test_database():
    """Create test database tables (for testing)."""
    if not settings.is_testing:
        raise RuntimeError("Test database creation only allowed in test environment")
    
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(DatabaseBase.metadata.create_all)


async def drop_test_database():
    """Drop test database tables (for testing)."""
    if not settings.is_testing:
        raise RuntimeError("Test database dropping only allowed in test environment")
    
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(DatabaseBase.metadata.drop_all)