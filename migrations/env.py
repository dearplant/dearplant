# 📄 File: migrations/env.py
# 🧭 Purpose (Layman Explanation):
# Configuration file that tells Alembic how to connect to the database and
# run migrations safely, handling different environments like development and production.
# 🧪 Purpose (Technical Summary):
# Alembic environment configuration for database migrations, handling async connections,
# model imports, and environment-specific settings for the Plant Care application.
# 🔗 Dependencies:
# - alembic (migration tool)
# - SQLAlchemy (ORM)
# - asyncpg (PostgreSQL async driver)
# - python-dotenv (environment variables)
# 🔄 Connected Modules / Calls From:
# - alembic CLI commands (upgrade, downgrade, revision)
# - Database migration scripts
# - Development and production deployment

import asyncio
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import the database base class
from app.shared.config.database import DatabaseBase

# Import all module models to ensure they're included in autogenerate
from app.modules.user_management.infrastructure.database.models import (
    UserModel,
    ProfileModel, 
    SubscriptionModel
)

# Future module imports (will be added as modules are implemented)
# from app.modules.plant_management.infrastructure.database.models import *
# from app.modules.care_management.infrastructure.database.models import *
# from app.modules.health_monitoring.infrastructure.database.models import *
# from app.modules.growth_tracking.infrastructure.database.models import *
# from app.modules.community_social.infrastructure.database.models import *
# from app.modules.ai_smart_features.infrastructure.database.models import *
# from app.modules.weather_environmental.infrastructure.database.models import *
# from app.modules.analytics_insights.infrastructure.database.models import *
# from app.modules.notification_communication.infrastructure.database.models import *
# from app.modules.payment_subscription.infrastructure.database.models import *
# from app.modules.content_management.infrastructure.database.models import *
# from app.modules.admin_management.infrastructure.database.models import *

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = DatabaseBase.metadata

# Other values from the config, defined by the needs of env.py
exclude_tables = config.get_main_option("exclude_tables", "")


def get_database_url() -> str:
    """
    Get database URL from environment variables.
    
    Returns:
        str: Database connection URL
    """
    # Try to get from environment variable first
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Convert asyncpg URL to psycopg2 for Alembic compatibility
        if "postgresql+asyncpg://" in database_url:
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        return database_url
    
    # Fallback to building URL from components
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_name = os.getenv("DB_NAME", "plantcare_db")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """
    Run migrations with the given connection.
    
    Args:
        connection: Database connection object
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        render_as_batch=False,
        # Include table filtering if needed
        include_object=include_object,
        # Custom naming convention for constraints
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects to include in migrations.
    
    Args:
        object: SQLAlchemy object
        name: Object name
        type_: Object type
        reflected: Whether object is reflected from database
        compare_to: Comparison object
        
    Returns:
        bool: Whether to include object in migration
    """
    # Exclude Supabase system schemas
    if hasattr(object, 'schema'):
        if object.schema in ['auth', 'storage', 'realtime', 'vault', 'extensions']:
            return False
    
    # Exclude certain tables if specified
    if type_ == "table" and name in exclude_tables.split(","):
        return False
    
    # Exclude Supabase tables even in public schema
    supabase_tables = [
        'users', 'identities', 'sessions', 'refresh_tokens', 
        'audit_log_entries', 'flow_state', 'saml_providers',
        'saml_relay_states', 'sso_providers', 'sso_domains',
        'mfa_factors', 'mfa_challenges', 'mfa_amr_claims',
        'one_time_tokens', 'schema_migrations', 'instances',
        'buckets', 'objects', 's3_multipart_uploads', 
        's3_multipart_uploads_parts', 'migrations', 'secrets',
        'subscription', 'messages'
    ]
    
    if type_ == "table" and reflected and name in supabase_tables:
        return False
    
    # Include all other objects
    return True


def render_item(type_, obj, autogen_context):
    """
    Custom rendering for migration items.
    
    Args:
        type_: Item type
        obj: SQLAlchemy object
        autogen_context: Autogeneration context
        
    Returns:
        str or None: Custom rendering or None for default
    """
    # Custom rendering for specific types if needed
    if type_ == "type" and obj.__class__.__name__ == "UUID":
        # Ensure UUID imports are included
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        return "postgresql.UUID(as_uuid=True)"
    
    # Return None for default rendering
    return None


async def run_async_migrations() -> None:
    """
    Run migrations in async mode for async database connections.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = AsyncEngine(
        engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    # Check if we're running in async mode
    if os.getenv("ALEMBIC_ASYNC", "false").lower() == "true":
        asyncio.run(run_async_migrations())
    else:
        # Synchronous mode
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = get_database_url()
        
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)


# Determine which mode to run migrations in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()