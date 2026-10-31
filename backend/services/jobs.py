from datetime import timedelta
from pathlib import Path
from sqlalchemy import delete, select, func
from backend.config import settings
from backend.models import Bot, UploadedFile, User, Job, Usage, now, aware
from backend.services import limits, monetization, queue, users
from backend.services.limits import policy, rate_limit
from backend.services.platforms import canonical_url, platform_for, provider_policy
from backend.services.security import DomainError, normalize_url, safe_filename, ALLOWED_EXTENSIONS
from backend.services.users import register

METADATA_TTL = timedelta(hours=6)


def new_job(db, bot_id: str, user_id: int, username: str | None, request_key: str, **values) -> tuple[Job, bool]:
    """Idempotent job creation: the same (user, bot, request_key) always returns the same job."""
    register(db, bot_id, user_id, username)
    # Consistent lock order serializes per-bot and per-user daily limits across processes.
    bot = db.scalar(select(Bot).where(Bot.id == bot_id).with_for_update())
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    old = db.scalar(select(Job).where(Job.user_id == user.id, Job.bot_id == bot_id, Job.request_key == request_key))
    if old:
        db.commit()
        return old, False
    if user.banned or not bot.enabled:
        raise DomainError("disabled")
    # Daily limits count real downloads and uploads only: looking at a link's formats is free
    # (still protected by the per-minute rate limit) and failed jobs are refunded by the worker.
    counted = values.get("kind") != "metadata"
    tier = monetization.tier_of(db, user)
    premium = tier is not None and tier.priority  # paying users of a priority tier go before the free queue
    if counted:
        today = now().replace(hour=0, minute=0, second=0, microsecond=0)
        bot_used = db.scalar(select(func.count()).select_from(Usage).where(Usage.bot_id == bot_id, Usage.created_at >= today))
        # The bot-wide limit protects the server whatever the user's plan.
        if bot_used >= bot.daily_limit:
            raise DomainError("rate_limit")
        limit = users.daily_limit(db, user)  # the tier's limit for paying users (0 = unlimited), else the free one
        if limit and users.used_today(db, user.id) >= limit:
            if (user.credits or 0) > 0:
                user.credits -= 1  # a credit buys one download beyond the daily limit
            else:
                raise DomainError("premium_limit" if monetization.settings(db).sells_premium else "rate_limit")
    rate_limit(f"submit:{user.id}", 8, 60)
    job = Job(user_id=user.id, bot_id=bot_id, request_key=request_key, **values)
    db.add(job)
    db.flush()
    if counted:
        db.add(Usage(user_id=user.id, bot_id=bot_id, job_id=job.id))
    db.commit()
    queue.enqueue(job.id, priority=premium)
    return job, True


CANCEL_KEY = "cancel:{}"


def cancel(db, bot_id: str, user_id: int, job_id: str) -> Job:
    """The owner stops a queued or running download/upload: the worker sees the flag and stops."""
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id, Job.bot_id == bot_id))
    if not job:
        raise DomainError("not_found")
    if job.status in {"completed", "failed"}:
        return job
    limits.redis_client().set(CANCEL_KEY.format(job.id), "1", ex=3600)
    if job.status == "queued":  # not picked up yet: finish it here, the worker will skip it
        job.status, job.error, job.completed_at = "failed", "cancelled", now()
        db.execute(delete(Usage).where(Usage.job_id == job.id))
    db.commit()
    return job


def submit_metadata(db, bot_id: str, user_id: int, username: str | None, url: str, request_key: str):
    if bot_id == "files":
        raise DomainError("unsupported")
    url = canonical_url(normalize_url(url.strip()))
    platform = provider_policy(url)
    if bot_id == "video" and platform == "direct":
        raise DomainError("unsupported")  # the Video bot serves the free-licence libraries only
    check_platform(db, bot_id, user_id, platform)
    return new_job(db, bot_id, user_id, username, request_key, kind="metadata", source_url=url, platform=platform)


def check_platform(db, bot_id: str, user_id: int, platform: str) -> None:
    """The platform must be on for the whole platform (Settings), for this bot (Bots) and for the user's plan (Tiers)."""
    if platform not in policy(db).enabled_platforms:
        raise DomainError("disabled")
    bot = db.get(Bot, bot_id)
    if bot and bot.platforms and platform not in bot.platforms:
        raise DomainError("disabled")
    if not monetization.platform_allowed(db, db.get(User, user_id), platform):
        raise DomainError("premium_feature")


def owned_metadata(db, bot_id: str, user_id: int, metadata_id: str) -> Job:
    job = db.get(Job, metadata_id)
    if not job or job.user_id != user_id or job.bot_id != bot_id or job.kind != "metadata":
        raise DomainError("not_found")
    return job


def select_format(db, bot_id: str, user_id: int, username: str | None, metadata_id: str, index: int):
    metadata = owned_metadata(db, bot_id, user_id, metadata_id)
    if metadata.status != "completed":
        raise DomainError("not_found")
    if aware(metadata.created_at) < now() - METADATA_TTL:
        raise DomainError("expired")
    formats = metadata.result.get("formats", [])
    if index >= len(formats):
        raise DomainError("unsupported")
    chosen = formats[index]
    lock = monetization.format_lock(db, db.get(User, user_id), chosen)
    if lock:  # HD/4K and large files are Premium: the bot answers with the Premium offer
        raise DomainError(lock)
    return new_job(db, bot_id, user_id, username, f"download:{metadata.id}:{index}", kind="download",
                   source_url=metadata.source_url, platform=metadata.platform, selected_format=chosen["selector"],
                   payload={"merge": chosen.get("merge"), "kind": chosen.get("kind"), "label": chosen.get("label"),
                            "title": metadata.result.get("title"), "description": (metadata.result.get("description") or "")[:3000],
                            "channel": metadata.result.get("channel"), "license": metadata.result.get("license")})


def refresh_metadata(db, bot_id: str, user_id: int, username: str | None, metadata_id: str):
    metadata = owned_metadata(db, bot_id, user_id, metadata_id)
    # One refresh per minute per card; repeated presses inside the minute reuse the same job.
    key = f"refresh:{metadata_id}:{int(now().timestamp()) // 60}"
    return submit_metadata(db, bot_id, user_id, username, metadata.source_url, key)


def submit_upload(db, bot_id: str, user_id: int, username: str | None, request_key: str, file_id: str, name: str, size: int):
    if bot_id != "files":
        raise DomainError("unsupported")
    name = safe_filename(name)
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise DomainError("file_type")
    if size > min(policy(db).max_upload_bytes, settings().telegram_receive_bytes):
        raise DomainError("file_size")
    quota = monetization.storage_quota(db, db.get(User, user_id))
    if quota:  # storage quota of the user's plan
        kept = db.scalar(select(func.coalesce(func.sum(UploadedFile.size), 0)).where(UploadedFile.user_id == user_id,
                                                                                   UploadedFile.deleted.is_(False)))
        if kept + size > quota:
            raise DomainError("storage_quota")
    return new_job(db, bot_id, user_id, username, request_key, kind="upload", platform="telegram",
                   payload={"file_id": file_id, "name": name, "size": size})
