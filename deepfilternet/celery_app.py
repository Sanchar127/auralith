from __future__ import annotations

from celery import Celery

from config import settings


celery = Celery(
    "auralith_deepfilter",
    broker=settings.RABBITMQ_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    timezone="UTC",
    enable_utc=True,

    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    task_default_queue=settings.CELERY_QUEUE,

    task_routes={
        "deepfilternet.enhance_audio": {
            "queue": settings.CELERY_QUEUE,
        },
    },

    task_ignore_result=True,

    imports=(
    "tasks.audio",
    ),
)