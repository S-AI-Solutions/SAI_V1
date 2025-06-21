"""Celery configuration for background task processing."""

from celery import Celery
from app.config import settings

# Create Celery instance
celery_app = Celery(
    "document_ai_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Optional: Configure routing
celery_app.conf.task_routes = {
    "app.tasks.process_document_task": {"queue": "document_processing"},
    "app.tasks.process_batch_task": {"queue": "batch_processing"},
}

if __name__ == "__main__":
    celery_app.start()
