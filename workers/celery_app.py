from celery import Celery
from backend.config import settings

cfg = settings()
celery = Celery("media", broker=cfg.redis_url, backend=cfg.redis_url, include=["workers.tasks", "workers.broadcast", "workers.monitor", "workers.channel"])
celery.conf.update(
    task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
    task_soft_time_limit=cfg.job_timeout, task_time_limit=cfg.job_timeout + 30,
    # "priority": the worker always takes Premium jobs (queue "priority", listed first in -Q) before the rest.
    broker_transport_options={"visibility_timeout": cfg.job_timeout + 120, "queue_order_strategy": "priority"},
    task_serializer="json", accept_content=["json"], result_serializer="json",
    result_expires=3600, task_ignore_result=True,
    beat_schedule={
        "reconcile": {"task": "workers.tasks.reconcile", "schedule": 60},
        "cleanup": {"task": "workers.tasks.cleanup", "schedule": 300},
        "monitor": {"task": "workers.monitor.check", "schedule": 300},
        "channel": {"task": "workers.channel.publish_due", "schedule": 30},  # scheduled posts of the public channel
    },
)

from backend.services import i18n, translations  # noqa: E402
from backend import observability  # noqa: E402
i18n.use_loader(translations.loader)  # texts and languages edited in the dashboard
observability.setup("worker")  # error tracking when SENTRY_DSN is set
