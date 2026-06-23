from celery import Celery
from config.settings import settings

# Initialize Celery application
celery_app = Celery(
    "alemeno_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.workers.tasks"]
)

# Configure Celery parameters
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
