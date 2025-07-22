# 📄 File: app/shared/config/settings.py
#
# 🧭 Purpose (Layman Explanation):
# The main configuration center that reads all settings from environment variables
# and provides them to the rest of our Plant Care app in a organized way.
#
# 🧪 Purpose (Technical Summary):
# Pydantic-based settings management with environment variable loading,
# validation, and type safety for all application configuration parameters.
#
# 🔗 Dependencies:
# - pydantic-settings for configuration management
# - python-dotenv for .env file loading
# - typing for type hints
#
# 🔄 Connected Modules / Calls From:
# - app.main (application startup)
# - Database connection modules
# - External API clients
# - All modules requiring configuration

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic for validation and type safety. Settings are loaded
    from environment variables with fallback to .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    
    APP_NAME: str = Field(default="Plant Care API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    APP_DESCRIPTION: str = Field(
        default="AI-Powered Plant Care Management System",
        description="Application description"
    )
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # =========================================================================
    # SERVER CONFIGURATION
    # =========================================================================
    
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=True, description="Auto-reload on changes")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    
    # =========================================================================
    # DATABASE CONFIGURATION
    # =========================================================================
    
    # Supabase PostgreSQL
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")
    
    # Direct PostgreSQL connection (alternative)
    DATABASE_URL: Optional[str] = Field(None, description="PostgreSQL connection URL")
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_NAME: str = Field(default="plantcare_db", description="Database name")
    DB_USER: str = Field(default="postgres", description="Database user")
    DB_PASSWORD: str = Field(default="", description="Database password")
    
    # Connection Pool Settings
    DB_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database pool overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Database pool recycle time")
    
    # =========================================================================
    # REDIS CONFIGURATION
    # =========================================================================
    
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis password")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, description="Redis connection pool size")
    
    # Cache Settings
    CACHE_DEFAULT_TTL: int = Field(default=3600, description="Default cache TTL (seconds)")
    CACHE_PLANT_LIBRARY_TTL: int = Field(default=86400, description="Plant library cache TTL")
    CACHE_WEATHER_TTL: int = Field(default=3600, description="Weather cache TTL")
    CACHE_API_RESPONSE_TTL: int = Field(default=300, description="API response cache TTL")
    
    # =========================================================================
    # SECURITY SETTINGS
    # =========================================================================
    
    SECRET_KEY: str = Field(..., description="Application secret key")
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, 
        description="JWT access token expiry"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, 
        description="JWT refresh token expiry"
    )
    BCRYPT_ROUNDS: int = Field(default=12, description="BCrypt hash rounds")
    
    # API Keys Encryption
    API_ENCRYPTION_KEY: str = Field(..., description="API encryption key")
    
    # CORS Settings
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="CORS allowed origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS allow credentials")
    
    # =========================================================================
    # SUPABASE SERVICES
    # =========================================================================
    
    # Authentication
    SUPABASE_AUTH_URL: Optional[str] = Field(None, description="Supabase auth URL")
    
    # Storage
    SUPABASE_STORAGE_URL: Optional[str] = Field(None, description="Supabase storage URL")
    SUPABASE_STORAGE_BUCKET: str = Field(
        default="plant-photos", 
        description="Supabase storage bucket"
    )
    
    # =========================================================================
    # CELERY / BACKGROUND JOBS
    # =========================================================================
    
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", 
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )
    
    # =========================================================================
    # PLANT IDENTIFICATION APIs
    # =========================================================================
    
    # PlantNet API
    PLANTNET_API_KEY: Optional[str] = Field(None, description="PlantNet API key")
    PLANTNET_API_URL: str = Field(
        default="https://my-api.plantnet.org/v2/identify",
        description="PlantNet API URL"
    )
    PLANTNET_FREE_LIMIT: int = Field(default=5, description="PlantNet free tier limit")
    PLANTNET_PREMIUM_LIMIT: int = Field(default=50, description="PlantNet premium limit")
    
    # Trefle API
    TREFLE_API_KEY: Optional[str] = Field(None, description="Trefle API key")
    TREFLE_API_URL: str = Field(default="https://trefle.io/api/v1", description="Trefle API URL")
    TREFLE_FREE_LIMIT: int = Field(default=10, description="Trefle free tier limit")
    TREFLE_PREMIUM_LIMIT: int = Field(default=100, description="Trefle premium limit")
    
    # Plant.id API
    PLANT_ID_API_KEY: Optional[str] = Field(None, description="Plant.id API key")
    PLANT_ID_API_URL: str = Field(
        default="https://api.plant.id/v3/identification",
        description="Plant.id API URL"
    )
    PLANT_ID_FREE_LIMIT: int = Field(default=3, description="Plant.id free tier limit")
    PLANT_ID_PREMIUM_LIMIT: int = Field(default=30, description="Plant.id premium limit")
    
    # Kindwise API
    KINDWISE_API_KEY: Optional[str] = Field(None, description="Kindwise API key")
    KINDWISE_API_URL: str = Field(
        default="https://plant.kindwise.com/api/v1/identification",
        description="Kindwise API URL"
    )
    KINDWISE_FREE_LIMIT: int = Field(default=5, description="Kindwise free tier limit")
    KINDWISE_PREMIUM_LIMIT: int = Field(default=50, description="Kindwise premium limit")
    
    # =========================================================================
    # WEATHER APIs
    # =========================================================================
    
    # OpenWeatherMap
    OPENWEATHER_API_KEY: Optional[str] = Field(None, description="OpenWeather API key")
    OPENWEATHER_API_URL: str = Field(
        default="https://api.openweathermap.org/data/2.5",
        description="OpenWeather API URL"
    )
    OPENWEATHER_FREE_LIMIT: int = Field(default=1000, description="OpenWeather free limit")
    OPENWEATHER_PREMIUM_LIMIT: int = Field(default=10000, description="OpenWeather premium limit")
    
    # Tomorrow.io
    TOMORROW_IO_API_KEY: Optional[str] = Field(None, description="Tomorrow.io API key")
    TOMORROW_IO_API_URL: str = Field(
        default="https://api.tomorrow.io/v4",
        description="Tomorrow.io API URL"
    )
    TOMORROW_IO_FREE_LIMIT: int = Field(default=100, description="Tomorrow.io free limit")
    TOMORROW_IO_PREMIUM_LIMIT: int = Field(default=1000, description="Tomorrow.io premium limit")
    
    # =========================================================================
    # AI / LLM APIs
    # =========================================================================
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model")
    OPENAI_MAX_TOKENS: int = Field(default=4000, description="OpenAI max tokens")
    
    # Google Gemini
    GOOGLE_GEMINI_API_KEY: Optional[str] = Field(None, description="Google Gemini API key")
    GOOGLE_GEMINI_MODEL: str = Field(default="gemini-pro", description="Gemini model")
    
    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = Field(None, description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-sonnet-20240229", 
        description="Anthropic model"
    )
    
    # =========================================================================
    # PAYMENT GATEWAYS
    # =========================================================================
    
    # Razorpay (India)
    RAZORPAY_KEY_ID: Optional[str] = Field(None, description="Razorpay key ID")
    RAZORPAY_KEY_SECRET: Optional[str] = Field(None, description="Razorpay key secret")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(None, description="Razorpay webhook secret")
    
    # Stripe (Global)
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(None, description="Stripe publishable key")
    STRIPE_SECRET_KEY: Optional[str] = Field(None, description="Stripe secret key")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(None, description="Stripe webhook secret")
    
    # =========================================================================
    # NOTIFICATION SERVICES
    # =========================================================================
    
    # Firebase Cloud Messaging
    FCM_SERVER_KEY: Optional[str] = Field(None, description="FCM server key")
    FCM_SENDER_ID: Optional[str] = Field(None, description="FCM sender ID")
    
    # SendGrid Email
    SENDGRID_API_KEY: Optional[str] = Field(None, description="SendGrid API key")
    SENDGRID_FROM_EMAIL: str = Field(
        default="noreply@plantcare.app", 
        description="SendGrid from email"
    )
    SENDGRID_FROM_NAME: str = Field(
        default="Plant Care App", 
        description="SendGrid from name"
    )
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(None, description="Telegram bot token")
    
    # =========================================================================
    # FILE STORAGE & CDN
    # =========================================================================
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE: int = Field(default=10485760, description="Max file size (10MB)")
    MAX_IMAGE_SIZE: int = Field(default=5242880, description="Max image size (5MB)")
    
    # Image processing settings
    IMAGE_QUALITY: int = Field(default=80, description="Image compression quality")
    THUMBNAIL_SIZE: int = Field(default=200, description="Thumbnail size in pixels")
    
    # CDN Settings
    CDN_URL: Optional[str] = Field(None, description="CDN base URL")
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    
    # Global rate limits (requests per period)
    GLOBAL_RATE_LIMIT: str = Field(default="1000/minute", description="Global rate limit in '<limit>/<period>' format")
    PREMIUM_RATE_LIMIT: str = Field(default="5000/minute", description="Premium rate limit in '<limit>/<period>' format")
    ADMIN_RATE_LIMIT: str = Field(default="10000/minute", description="Admin rate limit in '<limit>/<period>' format")
    
    # API specific limits
    PLANT_ID_RATE_LIMIT: int = Field(default=50, description="Plant ID rate limit")
    WEATHER_RATE_LIMIT: int = Field(default=100, description="Weather rate limit")
    AI_CHAT_RATE_LIMIT: int = Field(default=20, description="AI chat rate limit")
    
    # =========================================================================
    # ADMIN SETTINGS
    # =========================================================================
    
    ADMIN_EMAIL: str = Field(default="admin@plantcare.app", description="Admin email")
    ADMIN_PASSWORD: str = Field(default="", description="Admin password")
    ADMIN_SECRET_KEY: str = Field(default="", description="Admin secret key")
    
    # =========================================================================
    # DEVELOPMENT TOOLS
    # =========================================================================
    
    # Enable/disable debug features
    ENABLE_SWAGGER_UI: bool = Field(default=True, description="Enable Swagger UI")
    ENABLE_REDOC: bool = Field(default=True, description="Enable ReDoc")
    ENABLE_DEBUG_TOOLBAR: bool = Field(default=False, description="Enable debug toolbar")
    
    # Testing settings
    TEST_DATABASE_URL: Optional[str] = Field(None, description="Test database URL")
    TEST_REDIS_URL: str = Field(
        default="redis://localhost:6379/15", 
        description="Test Redis URL"
    )
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed_environments = ["development", "staging", "production", "test"]
        if v.lower() not in allowed_environments:
            raise ValueError(f"Environment must be one of {allowed_environments}")
        return v.lower()
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()
    
    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"JWT algorithm must be one of {allowed_algorithms}")
        return v
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate CORS origins format."""
        origins = [origin.strip() for origin in v.split(",")]
        for origin in origins:
            if not origin.startswith(("http://", "https://", "*")):
                raise ValueError(f"Invalid CORS origin format: {origin}")
        return v
    
    @field_validator("API_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate encryption key length."""
        if len(v) < 32:
            raise ValueError("API encryption key must be at least 32 characters long")
        return v
    
    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================
    
    @property
    def database_url(self) -> str:
        """Get the database URL, preferring explicit DATABASE_URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def redis_url(self) -> str:
        """Get the Redis URL with optional password."""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT == "test"
    
    @property
    def supabase_auth_url(self) -> str:
        """Get Supabase Auth URL."""
        if self.SUPABASE_AUTH_URL:
            return self.SUPABASE_AUTH_URL
        return f"{self.SUPABASE_URL}/auth/v1"
    
    @property
    def supabase_storage_url(self) -> str:
        """Get Supabase Storage URL."""
        if self.SUPABASE_STORAGE_URL:
            return self.SUPABASE_STORAGE_URL
        return f"{self.SUPABASE_URL}/storage/v1"
    
    # =========================================================================
    # API PROVIDER CONFIGURATIONS
    # =========================================================================
    
    def get_plant_api_config(self) -> dict:
        """Get plant identification API configuration."""
        return {
            "plantnet": {
                "api_key": self.PLANTNET_API_KEY,
                "api_url": self.PLANTNET_API_URL,
                "free_limit": self.PLANTNET_FREE_LIMIT,
                "premium_limit": self.PLANTNET_PREMIUM_LIMIT,
                "priority": 1,
            },
            "trefle": {
                "api_key": self.TREFLE_API_KEY,
                "api_url": self.TREFLE_API_URL,
                "free_limit": self.TREFLE_FREE_LIMIT,
                "premium_limit": self.TREFLE_PREMIUM_LIMIT,
                "priority": 2,
            },
            "plant_id": {
                "api_key": self.PLANT_ID_API_KEY,
                "api_url": self.PLANT_ID_API_URL,
                "free_limit": self.PLANT_ID_FREE_LIMIT,
                "premium_limit": self.PLANT_ID_PREMIUM_LIMIT,
                "priority": 3,
            },
            "kindwise": {
                "api_key": self.KINDWISE_API_KEY,
                "api_url": self.KINDWISE_API_URL,
                "free_limit": self.KINDWISE_FREE_LIMIT,
                "premium_limit": self.KINDWISE_PREMIUM_LIMIT,
                "priority": 4,
            },
        }
    
    def get_weather_api_config(self) -> dict:
        """Get weather API configuration."""
        return {
            "openweather": {
                "api_key": self.OPENWEATHER_API_KEY,
                "api_url": self.OPENWEATHER_API_URL,
                "free_limit": self.OPENWEATHER_FREE_LIMIT,
                "premium_limit": self.OPENWEATHER_PREMIUM_LIMIT,
                "priority": 1,
            },
            "tomorrow_io": {
                "api_key": self.TOMORROW_IO_API_KEY,
                "api_url": self.TOMORROW_IO_API_URL,
                "free_limit": self.TOMORROW_IO_FREE_LIMIT,
                "premium_limit": self.TOMORROW_IO_PREMIUM_LIMIT,
                "priority": 2,
            },
        }
    
    def get_ai_api_config(self) -> dict:
        """Get AI/LLM API configuration."""
        return {
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "max_tokens": self.OPENAI_MAX_TOKENS,
                "priority": 1,
            },
            "gemini": {
                "api_key": self.GOOGLE_GEMINI_API_KEY,
                "model": self.GOOGLE_GEMINI_MODEL,
                "priority": 2,
            },
            "claude": {
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL,
                "priority": 3,
            },
        }


    @property
    def debug(self) -> bool:
        """Alias for DEBUG to allow access as settings.debug"""
        return self.DEBUG
    
    @property
    def database_pool_size(self) -> int:
        return self.DB_POOL_SIZE

    @property
    def database_max_overflow(self) -> int:
        return self.DB_MAX_OVERFLOW

    @property
    def database_pool_timeout(self) -> int:
        return self.DB_POOL_TIMEOUT

    @property
    def database_pool_recycle(self) -> int:
        return self.DB_POOL_RECYCLE
# ============================================================================
# SETTINGS FACTORY
# ============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Uses lru_cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()
