from celery import Celery

celery = Celery(
    "auralith",
    broker="amqp://guest:guest@rabbitmq:5672//",
    backend="redis://redis:6379/0",
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

celery.autodiscover_tasks(
    ["app.tasks"],
)