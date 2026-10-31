"""Background delivery and removal of ad posts, in short batches.

Each run handles one batch and queues the next one, so a post to 100 000 people never hits the task time
limit, a crash loses at most one message, and a redelivered task cannot send twice: every delivery is a
row keyed by (post, user), written right after Telegram accepts the message.
"""
import logging
import time
import httpx
from sqlalchemy import select
from backend.database import Session
from backend.models import Broadcast, BroadcastMessage, now
from backend.services import broadcasts, limits, queue
from backend.services.security import DomainError
from workers.celery_app import celery
from workers.telegram import Telegram, TelegramError, TelegramRetry

log = logging.getLogger(__name__)
BATCH = 200
PAUSE = 0.04  # about 25 messages a second: under Telegram's ~30 per second limit for bots
SEND_TASK, DELETE_TASK = "workers.broadcast.send", "workers.broadcast.delete"


ALIVE_SECONDS = 180


def locked(broadcast_id: str):
    """One worker per post at a time; sending and deleting share the lock, so they never overlap."""
    return limits.redis_client().lock(f"broadcast:{broadcast_id}", timeout=600, blocking=False)


def alive(broadcast_id: str) -> None:
    """Heartbeat of a running chain of batches; `resume` only restarts posts whose heartbeat stopped."""
    try:
        limits.redis_client().set(f"broadcast:alive:{broadcast_id}", "1", ex=ALIVE_SECONDS)
    except Exception:
        pass


def telegram_call(action, attempts: int = 4):
    """Run one Bot API call; waits out flood limits, returns None when Telegram refuses for good."""
    for attempt in range(attempts):
        try:
            return action()
        except TelegramRetry as exc:
            time.sleep(min(exc.retry_after or 2 ** attempt, 30))
        except TelegramError:
            return None  # the user blocked the bot, deleted the chat, the message is too old…
        except (httpx.HTTPError, DomainError):
            time.sleep(2 ** attempt)
    return None


def deliver(b: Broadcast, telegram: Telegram, user_id: int, bot_id: str) -> int | None:
    markup = broadcasts.markup(b)
    if not b.photo:
        result = telegram_call(lambda: telegram.call("sendMessage", {"chat_id": user_id, "text": b.text, "parse_mode": "HTML",
                                                                     "link_preview_options": {"is_disabled": True}, "reply_markup": markup}))
        return result and result["message_id"]
    data = {"chat_id": user_id, "caption": b.text, "parse_mode": "HTML", "reply_markup": markup}
    if b.photo_ids.get(bot_id):  # uploaded once per bot, then reused by its file_id
        result = telegram_call(lambda: telegram.call("sendPhoto", {**data, "photo": b.photo_ids[bot_id]}))
    else:
        result = telegram_call(lambda: telegram.call("sendPhoto", data, files={"photo": ("post.jpg", b.photo, "image/jpeg")}))
        if result and result.get("photo"):
            b.photo_ids = {**b.photo_ids, bot_id: result["photo"][-1]["file_id"]}
    return result and result["message_id"]


@celery.task(name=SEND_TASK, soft_time_limit=900, time_limit=960)
def send(broadcast_id: str):
    lock = locked(broadcast_id)
    if not lock.acquire(blocking=False):
        return
    more = False
    clients: dict[str, Telegram] = {}
    try:
        with Session() as db:
            b = db.get(Broadcast, broadcast_id)
            if not b or b.status != "sending":
                return
            batch = broadcasts.next_batch(db, b, BATCH)
            if not batch:
                b.status, b.finished_at = "sent", now()
                db.commit()
                log.info('{"event":"broadcast_sent","id":"%s"}', b.id)
                return
            for user_id, bot_id in batch:
                if db.scalar(select(Broadcast.status).where(Broadcast.id == b.id)) != "sending":
                    return  # the administrator deleted the post meanwhile: stop at once
                alive(b.id)
                telegram = clients.setdefault(bot_id, Telegram(bot_id))
                message_id = deliver(b, telegram, user_id, bot_id)
                db.add(BroadcastMessage(broadcast_id=b.id, user_id=user_id, bot_id=bot_id, message_id=message_id))
                db.commit()
                time.sleep(PAUSE)
            more = True
    finally:
        for client in clients.values():
            client.close()
        try:
            lock.release()
        except Exception:
            pass
        if more:
            queue.task(SEND_TASK, broadcast_id)


@celery.task(name=DELETE_TASK, soft_time_limit=900, time_limit=960)
def delete(broadcast_id: str):
    lock = locked(broadcast_id)
    if not lock.acquire(blocking=False):
        return
    more = False
    clients: dict[str, Telegram] = {}
    try:
        with Session() as db:
            b = db.get(Broadcast, broadcast_id)
            if not b or b.status != "deleting":
                return
            rows = list(db.scalars(select(BroadcastMessage).where(
                BroadcastMessage.broadcast_id == b.id, BroadcastMessage.message_id.is_not(None),
                BroadcastMessage.deleted.is_(False), BroadcastMessage.delete_failed.is_(False)).limit(BATCH)))
            if not rows:
                b.status, b.deleted_at = "deleted", now()
                db.commit()
                log.info('{"event":"broadcast_deleted","id":"%s"}', b.id)
                return
            for row in rows:
                alive(b.id)
                telegram = clients.setdefault(row.bot_id, Telegram(row.bot_id))
                ok = telegram_call(lambda: telegram.delete(row.user_id, row.message_id))
                row.deleted, row.delete_failed = bool(ok), not ok
                db.commit()
                time.sleep(PAUSE)
            more = True
    finally:
        for client in clients.values():
            client.close()
        try:
            lock.release()
        except Exception:
            pass
        if more:
            queue.task(DELETE_TASK, broadcast_id)


def resume(db):
    """Called by the periodic reconcile: restarts posts whose chain of batches was lost (worker restart)."""
    for b in db.scalars(select(Broadcast).where(Broadcast.status.in_(["sending", "deleting"]))):
        if not limits.redis_client().exists(f"broadcast:alive:{b.id}"):
            alive(b.id)  # one restart per silence window, never a second parallel chain
            queue.task(SEND_TASK if b.status == "sending" else DELETE_TASK, b.id)
