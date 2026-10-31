import logging

log = logging.getLogger(__name__)


PRIORITY_QUEUE = "priority"  # Premium jobs; workers always check it before the default queue
DEFAULT_QUEUE = "celery"


def enqueue(job_id: str, priority: bool = False) -> None:
    """Send a job to the Celery workers by task name (no worker code imported into the API).

    The job row is already committed as ``queued``; if the broker is down, the periodic
    ``reconcile`` task re-enqueues it, so a failure here is logged and not raised.
    """
    try:
        from workers.celery_app import celery
        celery.send_task("workers.tasks.process", args=[job_id], queue=PRIORITY_QUEUE if priority else DEFAULT_QUEUE)
    except Exception:
        log.warning('{"event":"enqueue_failed","job_id":"%s"}', job_id)


def task(name: str, *args, countdown: float = 0) -> None:
    """Start any background task by name (ad post sending and deleting). The beat `reconcile` restarts lost ones."""
    try:
        from workers.celery_app import celery
        celery.send_task(name, args=list(args), queue=DEFAULT_QUEUE, countdown=countdown or None)
    except Exception:
        log.warning('{"event":"task_enqueue_failed","task":"%s"}', name)
