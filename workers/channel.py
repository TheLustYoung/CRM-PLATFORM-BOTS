"""Publishes the public channel's scheduled posts when their time comes (every 30 seconds via celery beat)."""
from backend.database import Session
from backend.services import channel, limits
from workers.celery_app import celery


@celery.task(name="workers.channel.publish_due", soft_time_limit=240, time_limit=270)
def publish_due() -> int:
    lock = limits.redis_client().lock("channel:publish", timeout=300, blocking=False)
    if not lock.acquire(blocking=False):
        return 0  # the previous run is still sending: never two copies of one post
    try:
        with Session() as db:
            return channel.publish_due(db)
    finally:
        try:
            lock.release()
        except Exception:
            pass
