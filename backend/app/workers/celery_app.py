from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery("tradinggpt", broker=settings.redis_url,
                    backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
