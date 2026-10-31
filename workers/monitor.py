"""Monitoring and alerting: every 5 minutes the platform checks itself and tells the administrators in
Telegram when something needs attention.

Checks: free disk space for downloads and stored files, the share of failed downloads in the last 15 minutes, bots
that stopped sending their heartbeat, jobs waiting in the queue for too long. The result is shown on the dashboard
(Settings → Monitoring). An alert about the same problem is sent at most once an hour.
"""
import logging
import shutil
from datetime import timedelta
from pathlib import Path
from sqlalchemy import func, select
from backend.config import settings
from backend.database import Session
from backend.models import Bot, Job, SystemSetting, UploadedFile, aware, now
from backend.services import limits
from workers.celery_app import celery

log = logging.getLogger(__name__)
STATUS_KEY, SETTINGS_KEY = "monitor_status", "monitoring"
DEFAULTS = {"chat_id": "", "disk_min_gb": 5, "error_rate": 50, "queue_minutes": 15, "bot_silent_minutes": 5,
            # E-mail alerts go through an HTTPS e-mail API (the server only lets HTTPS out, so plain SMTP cannot be used):
            "email_to": "", "email_from": "", "email_provider": "", "email_key": ""}
EMAIL_PROVIDERS = {"sendgrid": "https://api.sendgrid.com/v3/mail/send", "resend": "https://api.resend.com/emails"}


def options(db) -> dict:
    row = db.get(SystemSetting, SETTINGS_KEY)
    return {**DEFAULTS, **(row.value if row else {})}


def public_options(db) -> dict:
    """Settings for the dashboard: the e-mail API key is never shown."""
    values = options(db)
    return {**{k: v for k, v in values.items() if k != "email_key"}, "email_key_set": bool(values.get("email_key"))}


def send_email(o: dict, subject: str, text: str) -> bool:
    """One alert e-mail through SendGrid or Resend; False when e-mail alerts are not configured."""
    import httpx
    from backend.services.security import decrypt
    recipients = [a.strip() for a in (o.get("email_to") or "").split(",") if a.strip()]
    key = decrypt(o.get("email_key")) if o.get("email_key") else None
    provider = o.get("email_provider")
    if not recipients or not key or provider not in EMAIL_PROVIDERS or not o.get("email_from"):
        return False
    if provider == "sendgrid":
        body = {"personalizations": [{"to": [{"email": r} for r in recipients]}], "from": {"email": o["email_from"]},
                "subject": subject, "content": [{"type": "text/plain", "value": text}]}
    else:
        body = {"from": o["email_from"], "to": recipients, "subject": subject, "text": text}
    with httpx.Client(proxy=settings().egress_proxy or None, timeout=20) as http:
        response = http.post(EMAIL_PROVIDERS[provider], json=body, headers={"Authorization": f"Bearer {key}"})
    if response.status_code >= 300:
        raise RuntimeError(f"{provider} answered {response.status_code}")
    return True


def disk(path: str) -> dict:
    target = Path(path)
    while not target.exists() and target != target.parent:
        target = target.parent
    usage = shutil.disk_usage(target)
    return {"total": usage.total, "free": usage.free, "used": usage.used}


def measure(db) -> dict:
    o, moment = options(db), now()
    recent = moment - timedelta(minutes=15)
    finished = db.execute(select(Job.status, func.count()).where(Job.kind != "metadata", Job.completed_at >= recent)
                          .group_by(Job.status)).all()
    counts = dict(finished)
    done = counts.get("completed", 0) + counts.get("failed", 0)
    stuck = db.scalar(select(func.count()).select_from(Job).where(Job.status == "queued",
                                                                   Job.created_at < moment - timedelta(minutes=o["queue_minutes"])))
    silent = [b.id for b in db.scalars(select(Bot).where(Bot.enabled.is_(True)))
              if settings().bot_token(b.id) and (not b.last_seen or aware(b.last_seen) < moment - timedelta(minutes=o["bot_silent_minutes"]))]
    space = disk(settings().storage_dir if settings().storage_backend == "local" else settings().temp_root)
    stored = db.scalar(select(func.coalesce(func.sum(UploadedFile.size), 0)).where(UploadedFile.deleted.is_(False)))
    problems = []
    if space["free"] < o["disk_min_gb"] * 1_000_000_000:
        problems.append(("disk", f"Low disk space: {space['free'] / 1e9:.1f} GB free"))
    if done >= 5 and 100 * counts.get("failed", 0) / done >= o["error_rate"]:
        problems.append(("errors", f"{counts.get('failed', 0)} of {done} downloads failed in the last 15 minutes"))
    if silent:
        problems.append(("bots", "No heartbeat from: " + ", ".join(silent)))
    if stuck:
        problems.append(("queue", f"{stuck} jobs waiting longer than {o['queue_minutes']} minutes"))
    return {"checked_at": moment.isoformat(), "problems": [{"kind": k, "text": t} for k, t in problems],
            "disk": space, "stored_bytes": int(stored or 0), "jobs_15m": {"completed": counts.get("completed", 0), "failed": counts.get("failed", 0)},
            "queued_too_long": stuck, "silent_bots": silent}


def alert(db, text: str, chat_id: str | None = None) -> bool:
    """Sends an alert to the Telegram chat (through the first connected bot) and by e-mail, where configured;
    False when neither is configured."""
    from workers.telegram import Telegram
    o = options(db)
    chat = chat_id or o["chat_id"]
    bot = next((b.id for b in db.scalars(select(Bot).order_by(Bot.id)) if settings().bot_token(b.id)), None)
    sent = False
    if chat and bot:
        with Telegram(bot) as telegram:
            telegram.message(chat, f"⚠️ <b>Media platform</b>\n{text}")
        sent = True
    try:
        sent = send_email(o, "Media platform alert", text) or sent
    except Exception as error:
        log.warning('{"event":"alert_email_failed","error":"%s"}', str(error)[:120])
    return sent


@celery.task(name="workers.monitor.check")
def check():
    with Session() as db:
        status = measure(db)
        db.merge(SystemSetting(key=STATUS_KEY, value=status))
        db.commit()
        redis = limits.redis_client()
        for problem in status["problems"]:
            if redis.set(f"monitor:alerted:{problem['kind']}", "1", nx=True, ex=3600):
                try:
                    alert(db, problem["text"])
                except Exception:
                    log.warning('{"event":"alert_failed","kind":"%s"}', problem["kind"])
        return status
