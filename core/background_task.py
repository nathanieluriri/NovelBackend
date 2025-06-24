from celery import Celery

celery = Celery(
    "worker",
    broker="redis://localhost:6379/0",  # EC2-host Redis
    backend="redis://localhost:6379/0"
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)
