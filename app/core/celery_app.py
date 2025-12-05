"""Celery application configuration and task definitions."""

from celery import Celery
from celery.schedules import crontab

from ..core.config import settings

# Create Celery app
celery_app = Celery(
    "proposal_bot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.core.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    worker_disable_rate_limits=False,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_cache_max=10000,

    # Task routing
    task_routes={
        "app.core.tasks.process_rfp": {"queue": "rfp_processing"},
        "app.core.tasks.send_email": {"queue": "email"},
        "app.core.tasks.check_inbox": {"queue": "email"},
        "app.core.tasks.validate_resource": {"queue": "validation"},
        "app.core.tasks.update_knowledge_base": {"queue": "knowledge"},
        "app.core.tasks.generate_presentation": {"queue": "presentation"},
    },

    # Task time limits
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Retry settings
    task_default_retry_delay=60,  # 1 minute base delay
    task_max_retries=3,

    # Beat scheduler settings
    beat_schedule={
        "check-email-inbox": {
            "task": "app.core.tasks.check_inbox",
            "schedule": settings.email_check_interval,  # Every 60 seconds
        },
        "process-work-queue": {
            "task": "app.core.tasks.process_work_queue",
            "schedule": 120.0,  # Every 2 minutes
        },
        "cleanup-expired-locks": {
            "task": "app.core.tasks.cleanup_expired_locks",
            "schedule": 300.0,  # Every 5 minutes
        },
        "update-resource-availability": {
            "task": "app.core.tasks.update_resource_availability",
            "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM
        },
        "generate-daily-metrics": {
            "task": "app.core.tasks.generate_daily_metrics",
            "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
        },
    },
)

# Error handling
@celery_app.task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **other_kwargs):
    """Handle task failures."""
    import logging
    logger = logging.getLogger(__name__)

    logger.error(
        f"Task {sender.name} (ID: {task_id}) failed: {exception}",
        extra={
            "task_id": task_id,
            "task_name": sender.name,
            "args": args,
            "kwargs": kwargs,
            "exception": str(exception),
        },
        exc_info=einfo
    )


@celery_app.task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Handle task successes."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Task {sender.name} completed successfully")


# Import tasks to register them
from . import tasks
