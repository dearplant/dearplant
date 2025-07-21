# 📄 File: celery_config.py
#
# 🧭 Purpose (Layman Explanation):
# Configuration file for our background task system (Celery) that handles things like
# sending notifications, processing plant photos, and running scheduled maintenance tasks.
#
# 🧪 Purpose (Technical Summary):
# Celery configuration for distributed task processing, queue management, scheduling,
# and background job execution with Redis as message broker and result backend.
#
# 🔗 Dependencies:
# - celery Python package
# - Redis server (message broker)
# - app.shared.config.settings
#
# 🔄 Connected Modules / Calls From:
# - app/background_jobs/celery_app.py
# - Docker Compose services (celery workers)
# - Task scheduling and execution

import os
from datetime import timedelta
from typing import Any, Dict

from celery import Celery
from kombu import Queue

# =============================================================================
# CELERY CONFIGURATION CLASS
# =============================================================================


class CeleryConfig:
    """
    Celery configuration class for Plant Care Application.
    
    Defines all settings for task execution, routing, scheduling,
    and performance optimization.
    """

    # =========================================================================
    # BROKER AND BACKEND SETTINGS
    # =========================================================================
    
    # Redis configuration
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # Broker connection settings
    broker_connection_retry_on_startup = True
    broker_connection_retry = True
    broker_connection_max_retries = 10
    broker_heartbeat = 30
    broker_pool_limit = 10
    
    # Result backend settings
    result_backend_transport_options = {
        "master_name": "mymaster",
        "visibility_timeout": 3600,
        "retry_policy": {
            "timeout": 5.0
        }
    }
    result_expires = timedelta(hours=24)  # Results expire after 24 hours
    result_persistent = True
    
    # =========================================================================
    # TASK SETTINGS
    # =========================================================================
    
    # Task execution settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "UTC"
    enable_utc = True
    
    # Task routing and queues
    task_default_queue = "default"
    task_default_exchange = "default"
    task_default_exchange_type = "direct"
    task_default_routing_key = "default"
    
    # Task execution limits
    task_time_limit = 300  # 5 minutes hard limit
    task_soft_time_limit = 240  # 4 minutes soft limit
    task_acks_late = True
    worker_prefetch_multiplier = 1  # Prevent worker from prefetching too many tasks
    
    # Task retry settings
    task_reject_on_worker_lost = True
    task_ignore_result = False
    
    # =========================================================================
    # QUEUE DEFINITIONS
    # =========================================================================
    
    task_routes = {
        # High Priority Queue - Critical tasks that need immediate processing
        "app.background_jobs.tasks.care_reminders.send_urgent_care_reminder": {
            "queue": "high_priority"
        },
        "app.background_jobs.tasks.health_monitoring.process_critical_health_alert": {
            "queue": "high_priority"
        },
        "app.background_jobs.tasks.notification_sending.send_emergency_notification": {
            "queue": "high_priority"
        },
        "app.background_jobs.tasks.api_rotation.handle_api_failure": {
            "queue": "high_priority"
        },
        
        # Medium Priority Queue - Important but not critical tasks
        "app.background_jobs.tasks.care_reminders.send_daily_care_reminders": {
            "queue": "medium_priority"
        },
        "app.background_jobs.tasks.health_monitoring.process_health_assessment": {
            "queue": "medium_priority"
        },
        "app.background_jobs.tasks.weather_updates.update_weather_data": {
            "queue": "medium_priority"
        },
        "app.background_jobs.tasks.notification_sending.send_push_notification": {
            "queue": "medium_priority"
        },
        
        # Low Priority Queue - Background maintenance and analytics
        "app.background_jobs.tasks.analytics_processing.process_user_analytics": {
            "queue": "low_priority"
        },
        "app.background_jobs.tasks.data_cleanup.cleanup_old_data": {
            "queue": "low_priority"
        },
        "app.background_jobs.tasks.translation_sync.sync_translations": {
            "queue": "low_priority"
        },
        "app.background_jobs.tasks.multilingual_content.process_content_translation": {
            "queue": "low_priority"
        },
        
        # Notifications Queue - Dedicated for all notification types
        "app.background_jobs.tasks.notification_sending.*": {
            "queue": "notifications"
        },
        
        # API Queue - External API calls with rate limiting
        "app.background_jobs.tasks.api_rotation.*": {
            "queue": "api_calls"
        },
    }
    
    # Queue definitions with priority and routing
    task_queues = (
        Queue("high_priority", routing_key="high_priority", priority=10),
        Queue("medium_priority", routing_key="medium_priority", priority=5),
        Queue("low_priority", routing_key="low_priority", priority=1),
        Queue("notifications", routing_key="notifications", priority=7),
        Queue("api_calls", routing_key="api_calls", priority=6),
        Queue("default", routing_key="default", priority=3),
    )
    
    # =========================================================================
    # WORKER SETTINGS
    # =========================================================================
    
    # Worker configuration
    worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks
    worker_max_memory_per_child = 200000  # 200MB memory limit per worker
    worker_disable_rate_limits = False
    worker_enable_remote_control = True
    
    # Worker concurrency settings
    worker_concurrency = int(os.getenv("CELERY_WORKER_CONCURRENCY", 4))
    worker_pool = "prefork"  # Use prefork for better isolation
    
    # Worker logging
    worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
    
    # =========================================================================
    # BEAT SCHEDULER SETTINGS
    # =========================================================================
    
    # Scheduler configuration
    beat_schedule = {
        # Care reminder tasks
        "send-daily-care-reminders": {
            "task": "app.background_jobs.tasks.care_reminders.send_daily_care_reminders",
            "schedule": timedelta(hours=1),  # Check every hour
            "options": {"queue": "medium_priority"}
        },
        
        # Weather data updates
        "update-weather-data": {
            "task": "app.background_jobs.tasks.weather_updates.update_weather_data",
            "schedule": timedelta(hours=2),  # Update every 2 hours
            "options": {"queue": "medium_priority"}
        },
        
        # Health monitoring checks
        "check-plant-health-alerts": {
            "task": "app.background_jobs.tasks.health_monitoring.check_health_alerts",
            "schedule": timedelta(hours=6),  # Check every 6 hours
            "options": {"queue": "medium_priority"}
        },
        
        # Analytics processing
        "process-daily-analytics": {
            "task": "app.background_jobs.tasks.analytics_processing.process_daily_analytics",
            "schedule": timedelta(days=1),  # Daily at midnight UTC
            "options": {"queue": "low_priority"}
        },
        
        # Data cleanup tasks
        "cleanup-old-notifications": {
            "task": "app.background_jobs.tasks.data_cleanup.cleanup_old_notifications",
            "schedule": timedelta(days=7),  # Weekly cleanup
            "options": {"queue": "low_priority"}
        },
        
        "cleanup-expired-sessions": {
            "task": "app.background_jobs.tasks.data_cleanup.cleanup_expired_sessions",
            "schedule": timedelta(hours=12),  # Twice daily
            "options": {"queue": "low_priority"}
        },
        
        # API usage tracking and rotation
        "reset-api-rate-limits": {
            "task": "app.background_jobs.tasks.api_rotation.reset_daily_rate_limits",
            "schedule": timedelta(days=1),  # Daily reset
            "options": {"queue": "api_calls"}
        },
        
        # Translation synchronization
        "sync-pending-translations": {
            "task": "app.background_jobs.tasks.translation_sync.sync_pending_translations",
            "schedule": timedelta(hours=4),  # Every 4 hours
            "options": {"queue": "low_priority"}
        },
        
        # System health monitoring
        "system-health-check": {
            "task": "app.background_jobs.tasks.monitoring.system_health_check",
            "schedule": timedelta(minutes=15),  # Every 15 minutes
            "options": {"queue": "high_priority"}
        },
        
        # Cache maintenance
        "cleanup-cache": {
            "task": "app.background_jobs.tasks.data_cleanup.cleanup_expired_cache",
            "schedule": timedelta(hours=2),  # Every 2 hours
            "options": {"queue": "low_priority"}
        },
    }
    
    beat_scheduler = "celery.beat:PersistentScheduler"
    beat_schedule_filename = "celerybeat-schedule"
    
    # =========================================================================
    # MONITORING AND LOGGING
    # =========================================================================
    
    # Task monitoring
    task_send_sent_event = True
    task_track_started = True
    task_publish_retry = True
    task_publish_retry_policy = {
        "max_retries": 3,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.2,
    }
    
    # Worker monitoring
    worker_send_task_events = True
    worker_send_task_event_batch_size = 100
    worker_send_task_event_batch_timeout = 5
    
    # Event monitoring
    event_serializer = "json"
    
    # =========================================================================
    # SECURITY SETTINGS
    # =========================================================================
    
    # Security configuration
    security_key = os.getenv("CELERY_SECURITY_KEY")
    security_certificate = os.getenv("CELERY_SECURITY_CERT")
    security_cert_store = os.getenv("CELERY_CERT_STORE")
    
    # Worker security
    worker_hijack_root_logger = False
    worker_log_color = False if os.getenv("ENVIRONMENT") == "production" else True
    
    # =========================================================================
    # OPTIMIZATION SETTINGS
    # =========================================================================
    
    # Performance optimization
    broker_transport_options = {
        "visibility_timeout": 3600,  # 1 hour
        "fanout_prefix": True,
        "fanout_patterns": True,
        "priority_steps": list(range(10)),
        "sep": ":",
        "queue_order_strategy": "priority",
    }
    
    # Result backend optimization
    result_backend_transport_options = {
        "retry_policy": {
            "timeout": 5.0
        },
        "master_name": "mymaster",
    }
    
    # Task compression
    task_compression = "gzip"
    result_compression = "gzip"
    
    # Database settings for result backend (if using DB)
    database_short_lived_sessions = True
    database_table_schemas = {
        "task": "celery",
        "group": "celery",
    }


# =============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATIONS
# =============================================================================

class DevelopmentCeleryConfig(CeleryConfig):
    """Development-specific Celery configuration."""
    
    # Enable more verbose logging in development
    worker_log_level = "DEBUG"
    beat_schedule = {
        **CeleryConfig.beat_schedule,
        # More frequent tasks for development
        "dev-health-check": {
            "task": "app.background_jobs.tasks.monitoring.system_health_check",
            "schedule": timedelta(minutes=5),
            "options": {"queue": "high_priority"}
        }
    }


class ProductionCeleryConfig(CeleryConfig):
    """Production-specific Celery configuration."""
    
    # Optimize for production
    worker_log_level = "INFO"
    worker_max_tasks_per_child = 5000  # Higher limit for production
    worker_max_memory_per_child = 500000  # 500MB for production
    
    # Production security settings
    broker_use_ssl = True
    redis_backend_use_ssl = True
    
    # Enhanced monitoring for production
    worker_send_task_events = True
    task_send_sent_event = True


# =============================================================================
# CONFIG FACTORY
# =============================================================================

def get_celery_config() -> CeleryConfig:
    """
    Factory function to get appropriate Celery configuration based on environment.
    
    Returns:
        CeleryConfig: Configuration instance for current environment
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    config_map = {
        "development": DevelopmentCeleryConfig,
        "staging": ProductionCeleryConfig,  # Use production config for staging
        "production": ProductionCeleryConfig,
    }
    
    config_class = config_map.get(environment, DevelopmentCeleryConfig)
    return config_class()


# =============================================================================
# CELERY APPLICATION INSTANCE
# =============================================================================

# Create Celery app with configuration
app = Celery("plant_care_backend")

# Load configuration
celery_config = get_celery_config()
app.config_from_object(celery_config)

# Auto-discover tasks from all modules
app.autodiscover_tasks([
    "app.background_jobs.tasks.care_reminders",
    "app.background_jobs.tasks.health_monitoring", 
    "app.background_jobs.tasks.weather_updates",
    "app.background_jobs.tasks.analytics_processing",
    "app.background_jobs.tasks.notification_sending",
    "app.background_jobs.tasks.api_rotation",
    "app.background_jobs.tasks.data_cleanup",
    "app.background_jobs.tasks.translation_sync",
    "app.background_jobs.tasks.multilingual_content",
    "app.background_jobs.tasks.monitoring",
])


# =============================================================================
# TASK ERROR HANDLING
# =============================================================================

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")


# Task failure handler
@app.task(bind=True)
def task_failure_handler(self, task_id, error, traceback):
    """
    Handle task failures with logging and alerting.
    
    Args:
        task_id: Failed task ID
        error: Error that occurred
        traceback: Error traceback
    """
    print(f"Task {task_id} failed: {error}")
    print(f"Traceback: {traceback}")
    
    # TODO: Send alert to monitoring system
    # TODO: Log to structured logging system
    # TODO: Notify admin if critical task fails


if __name__ == "__main__":
    # CLI for running Celery with this config
    app.start()