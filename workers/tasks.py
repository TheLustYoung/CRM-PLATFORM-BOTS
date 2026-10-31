"""Background jobs: metadata extraction, downloads, Telegram file uploads, delivery and cleanup."""
import html
import logging
import shutil
import tempfile
import time
from datetime import timedelta
from pathlib import Path
import httpx
from sqlalchemy import delete, select
from yt_dlp.utils import DownloadError
from backend.config import settings
from backend.database import Session
from backend.models import Job, User, Bot, UploadedFile, Usage, now, aware
from backend.services import monetization, users
from backend.services.i18n import tr, raw
from backend.services.jobs import CANCEL_KEY
from backend.services.queue import DEFAULT_QUEUE, PRIORITY_QUEUE
from backend.services.limits import policy, redis_client
from backend.services.security import DomainError
from workers.adapters import MediaAdapter
from workers.cards import card, signed, signature, human_size
from workers.celery_app import celery
from workers.telegram import Telegram, kind_of
import storage

cfg = settings()
log = logging.getLogger(__name__)
TEMPORARY = (httpx.TransportError, ConnectionError, TimeoutError)
MAX_ATTEMPTS = 3
# Stages the user can stop with the Cancel button (sending to Telegram is too late to interrupt cleanly).
CANCELLABLE = {"status_downloading", "status_progress", "status_progress_unknown", "status_uploading"}


def stop_checker(job_id: str):
    """Cheap cancellation check for download loops: asks Redis at most once a second."""
    state = {"at": 0.0, "stop": False}

    def should_stop() -> bool:
        if not state["stop"] and time.monotonic() - state["at"] >= 1:
            state["at"] = time.monotonic()
            state["stop"] = cancel_requested(job_id)
        return state["stop"]
    return should_stop


def cancel_requested(job_id: str) -> bool:
    try:
        return bool(redis_client().exists(CANCEL_KEY.format(job_id)))
    except Exception:
        return False  # Redis hiccup: keep working rather than fail the job


class Temporary(Exception):
    pass


def allowed(db, job):
    user, bot = db.get(User, job.user_id), db.get(Bot, job.bot_id)
    if not user or user.banned:
        raise DomainError("banned")
    if not bot or not bot.enabled:
        raise DomainError("disabled")
    p = policy(db)
    if job.kind != "upload" and job.platform not in p.enabled_platforms:
        raise DomainError("disabled")
    return p


class Status:
    """One status message per job, edited through the stages and removed at the end."""

    PROGRESS_INTERVAL = 3.0  # seconds between edits: stays far below Telegram's edit rate limits

    def __init__(self, db, job, telegram, lang, username, ad: dict | None = None):
        self.db, self.job, self.telegram, self.lang, self.username, self.ad = db, job, telegram, lang, username, ad
        self.last_edit, self.last_text = 0.0, None

    def progress(self, done: int, total: int | None):
        """Download progress (called from the yt-dlp hook), throttled and deduplicated."""
        if time.monotonic() - self.last_edit < self.PROGRESS_INTERVAL:
            return
        if total:
            self.set("status_progress", percent=min(99, int(done * 100 / total)), done=human_size(done), total=human_size(total))
        else:
            self.set("status_progress_unknown", done=human_size(done) or "0 B")

    def set(self, key: str, **values):
        text = signed(self.lang, key, self.username, **values)
        if text == self.last_text:
            return
        self.last_edit, self.last_text = time.monotonic(), text
        message_id = (self.job.payload or {}).get("status_message")
        buttons = [[{"text": raw(self.lang, "btn_cancel"), "callback_data": f"cx:{self.job.id}"}]] if key in CANCELLABLE else None
        if self.ad:  # sponsored message: lives under the status message and disappears with it
            text += f"\n\n<i>{html.escape(raw(self.lang, 'ad_label'))}</i>\n{html.escape(self.ad['text'])}"
            if self.ad.get("url"):
                buttons = [*(buttons or []), [{"text": self.ad.get("button") or raw(self.lang, "btn_ad_open"), "url": self.ad["url"]}]]
        try:
            if message_id:
                self.telegram.edit(self.job.user_id, message_id, text, buttons)
            else:
                sent = self.telegram.message(self.job.user_id, text, buttons)
                self.job.payload = {**(self.job.payload or {}), "status_message": sent["message_id"]}
                self.db.commit()
        except (DomainError, httpx.HTTPError) as exc:
            # Best-effort, but logged: a silent failure here looks like "the bot ignores links".
            log.warning('{"event":"status_send_failed","job_id":"%s","error":"%s"}', self.job.id, type(exc).__name__)

    def clear(self):
        message_id = (self.job.payload or {}).get("status_message")
        if message_id:
            try:
                self.telegram.delete(self.job.user_id, message_id)
            except (DomainError, httpx.HTTPError):
                pass


def bot_username(db, job, telegram) -> str | None:
    bot = db.get(Bot, job.bot_id)
    if bot and bot.username:
        return bot.username
    try:
        return telegram.get_me().get("username")
    except (DomainError, httpx.HTTPError):
        return None


def send_card(telegram, job, lang, username, locked: set[int] | None = None):
    info = job.result
    text, buttons = card(info, job.id, lang, username, locked)
    if info.get("thumbnail"):
        try:
            if len(text) <= 1024:
                telegram.photo_url(job.user_id, info["thumbnail"], text, buttons)
                return
            telegram.photo_url(job.user_id, info["thumbnail"])
        except (DomainError, httpx.HTTPError):
            pass  # the card is still useful without a thumbnail
    telegram.message(job.user_id, text, buttons)


def produce_files(db, job, telegram, status, root: Path, p) -> list[UploadedFile]:
    existing = list(db.scalars(select(UploadedFile).where(UploadedFile.job_id == job.id).order_by(UploadedFile.object_key)))
    # Stored results are reused on retry: a delivery failure never triggers a second download.
    if job.result.get("stored"):
        return existing
    status.set("status_downloading")
    should_stop = stop_checker(job.id)
    limit = monetization.download_limit(db, db.get(User, job.user_id), p)  # free tier or Premium
    if job.kind == "upload":
        paths = [root / job.payload["name"]]
        telegram.download_file(job.payload["file_id"], paths[0], min(p.max_upload_bytes, cfg.telegram_receive_bytes), should_stop)
    else:
        paths = MediaAdapter().download(job.source_url, job.selected_format, root, limit,
                                        (job.payload or {}).get("merge"), on_progress=status.progress, should_stop=should_stop)
    if cancel_requested(job.id):
        raise DomainError("cancelled")  # pressed while the last bytes or the merge were finishing
    status.set("status_uploading")
    days = p.retention_days if job.kind == "upload" else p.media_retention_days
    files = [storage.put_file(db, job, path, days) for path in paths]
    job.result = {"stored": True, "delivered": []}
    job.output_file_id = files[0].id
    usage = db.scalar(select(Usage).where(Usage.job_id == job.id))
    if usage:
        usage.bytes = sum(f.size for f in files)
    db.commit()
    return files


def local_copy(file: UploadedFile, root: Path) -> Path:
    path = root / file.name
    if not path.exists():
        try:
            storage.download_to(file.object_key, path)
        except storage.ObjectMissing:
            raise DomainError("expired") from None
    return path


CAPTION_LIMIT = 1024


def link_word(lang: str, url: str | None) -> str:
    """The file's page as a short "⬇ Download" link instead of a long address."""
    return f'<a href="{html.escape(url)}">⬇ {html.escape(raw(lang, "page_download"))}</a>' if url else ""


def hide_link(text: str, lang: str, url: str | None) -> str:
    return text.replace(html.escape(url, quote=False), link_word(lang, url), 1) if url else text


MESSAGE_PIECE = 3500  # escaped characters per message, under Telegram's 4096 with room for the details


def post_messages(job, username, details: str = "") -> list[str]:
    """The text that follows the media, as its own clean message: the post's text, its author, then the file details
    (name, size, hidden download link, expiry) and the bot's name. A very long post continues in the next messages."""
    payload = job.payload or {}
    text = (payload.get("description") or payload.get("title") or "").strip()
    tail = "\n\n".join(p for p in (details.strip(), signature(username).strip()) if p)
    pieces, current = [], ""
    for char in text:  # escaped character by character: a piece never splits an entity or outgrows a message
        escaped = html.escape(char, quote=False)
        if len(current) + len(escaped) > MESSAGE_PIECE:
            pieces.append(current)
            current = ""
        current += escaped
    if current:
        pieces.append(current)
    if not pieces:
        return [tail] if tail else []
    if len(pieces[-1]) + len(tail) + 2 <= 4096:
        pieces[-1] = f"{pieces[-1]}\n\n{tail}".strip()
    elif tail:
        pieces.append(tail)
    return pieces


def send_post_text(telegram, chat_id, messages: list[str]):
    for text in messages:
        telegram.message(chat_id, text)


def link_message(db, job) -> int | None:
    """The user's own message with the link (its id is part of the card's request key: msg:<chat>:<message>)."""
    key = job.request_key or ""
    if key.startswith("download:"):
        card = db.get(Job, key.split(":")[1])
        key = card.request_key if card else ""
    parts = key.split(":")
    return int(parts[2]) if len(parts) == 3 and parts[0] == "msg" and parts[2].isdigit() else None


def react_done(db, job, telegram):
    """🫡 on the link once its media is delivered (the bot put 👀 there when it took the link)."""
    message_id = link_message(db, job)
    if message_id:
        try:
            telegram.call("setMessageReaction", {"chat_id": job.user_id, "message_id": message_id,
                                                 "reaction": [{"type": "emoji", "emoji": "🫡"}]})
        except Exception:
            pass  # a reaction is decoration: never fail a delivered job over it


def deliver(db, job, telegram, files, root: Path, lang, username):
    delivered = set(job.result.get("delivered", []))
    pending = [f for f in files if f.id not in delivered]
    for file in pending:
        if file.deleted or aware(file.expires_at) <= now():
            raise DomainError("expired")
    if job.kind == "download" and len(files) > 1:
        # Albums (collections of several files): original order, caption once on the first item.
        if pending:
            sendable = [f for f in pending if f.size <= cfg.telegram_send_bytes]
            telegram.media_group(job.user_id, [local_copy(f, root) for f in sendable], "")  # clean album, the text follows
            send_post_text(telegram, job.user_id, post_messages(job, username))
            for f in pending:
                if f.size > cfg.telegram_send_bytes:
                    link = storage.public_url(db, f)
                    telegram.message(job.user_id, hide_link(signed(lang, "done_download", username, name=f.name, size=human_size(f.size),
                                                                   url=link, expires=aware(f.expires_at).date().isoformat()), lang, link))
            job.result = {**job.result, "delivered": [f.id for f in files]}
            db.commit()
        return
    for file in pending:
        url = storage.public_url(db, file) or "—"
        expires = aware(file.expires_at).date().isoformat()
        if job.kind == "upload":
            text = signed(lang, "done_file", username, name=file.name, size=human_size(file.size), mime=file.mime,
                          date=aware(file.created_at).date().isoformat(), expires=expires, url=url)
            text = hide_link(text, lang, storage.public_url(db, file))
            telegram.message(job.user_id, text, [[{"text": raw(lang, "btn_revoke"), "callback_data": f"rv:{file.id}"},
                                                  {"text": raw(lang, "btn_delete"), "callback_data": f"rm:{file.id}"}]])
        else:
            if file.size <= cfg.telegram_send_bytes:
                # Like popular downloader bots: the clean video, the same file as a document, then the post's text
                # with its author, the file details (hidden download link) and the bot's name.
                link = storage.public_url(db, file)
                details = hide_link(tr(lang, "done_download", name=file.name, size=human_size(file.size), url=link or "—",
                                       expires=expires), lang, link)
                path = local_copy(file, root)
                telegram.media(job.user_id, path, "")
                if kind_of(path) in ("video", "photo"):
                    telegram.document(job.user_id, path)
                send_post_text(telegram, job.user_id, post_messages(job, username, details))
            else:  # too big for Telegram: public link only
                telegram.message(job.user_id, hide_link(signed(lang, "done_download", username, name=file.name, size=human_size(file.size),
                                                               url=url, expires=expires), lang, storage.public_url(db, file)))
        job.result = {**job.result, "delivered": [*job.result.get("delivered", []), file.id]}
        db.commit()


@celery.task(bind=True, max_retries=MAX_ATTEMPTS)
def process(self, job_id: str):
    try:
        run(job_id)
    except Temporary as exc:
        raise self.retry(exc=exc, countdown=30 * int(str(exc) or 1))


def run(job_id: str):
    lock = redis_client().lock(f"job:{job_id}", timeout=cfg.job_timeout + 90, blocking=False)
    if not lock.acquire(blocking=False):
        return  # another worker is already processing this job
    telegram = None
    try:
        with Session() as db:
            job = db.get(Job, job_id)
            if not job or job.status in {"completed", "failed"}:
                return
            lang = users.language(db, job.user_id)
            status = username = None
            try:
                p = allowed(db, job)
                if job.kind != "metadata" and cancel_requested(job.id):
                    raise DomainError("cancelled")
                job.status, job.started_at = "processing", now()
                job.attempts += 1
                db.commit()
                telegram = Telegram(job.bot_id)
                username = bot_username(db, job, telegram)
                owner = db.get(User, job.user_id)
                status = Status(db, job, telegram, lang, username, None if job.kind == "metadata" else job_ad(db, job, owner, lang))
                if job.kind == "metadata":
                    status.set("status_metadata")
                    if not job.result:
                        job.result = MediaAdapter().extract(job.source_url)
                        db.commit()
                    status.clear()
                    send_card(telegram, job, lang, username, monetization.locked_formats(db, owner, job.result.get("formats", [])))
                else:
                    Path(cfg.temp_root).mkdir(parents=True, exist_ok=True)
                    if shutil.disk_usage(cfg.temp_root).free < cfg.min_free_disk_bytes:
                        raise DomainError("disk_space")
                    # Cleanup errors (a file still locked on Windows) must not fail an already delivered job;
                    # leftovers are removed by the periodic cleanup task.
                    with tempfile.TemporaryDirectory(prefix=f"job-{job.id}-", dir=cfg.temp_root, ignore_cleanup_errors=True) as temp:
                        root = Path(temp)
                        files = produce_files(db, job, telegram, status, root, p)
                        status.set("status_sending")
                        allowed(db, job)
                        deliver(db, job, telegram, files, root, lang, username)
                    status.clear()
                job.status, job.completed_at, job.error = "completed", now(), None
                db.commit()
                if job.kind != "metadata":
                    react_done(db, job, telegram)
                    reward_referrer(db, job, telegram, username)
            except TEMPORARY:
                db.rollback()
                job = db.get(Job, job_id)
                if job.attempts < MAX_ATTEMPTS:
                    job.status, job.error = "queued", "temporary_network_error"
                    db.commit()
                    raise Temporary(str(job.attempts))
                fail(db, job, "unavailable", telegram, lang, status, username)
            except Exception as exc:
                db.rollback()
                job = db.get(Job, job_id)
                code = str(exc) if isinstance(exc, DomainError) else download_error_code(exc) if isinstance(exc, DownloadError) else "failed"
                if job.kind != "metadata" and cancel_requested(job_id):
                    code = "cancelled"  # yt-dlp may wrap our stop signal in its own error
                if code == "failed":
                    log.exception('{"event":"job_error","job_id":"%s"}', job_id)
                fail(db, job, code, telegram, lang, status, username)
    finally:
        if telegram:
            telegram.close()
        try:
            lock.release()
        except Exception:
            pass


def job_ad(db, job, user, lang: str | None = None) -> dict | None:
    """Sponsored message for this job, chosen once and kept for retries (Premium users see none)."""
    payload = job.payload or {}
    if "ad" not in payload:
        job.payload = {**payload, "ad": monetization.pick_ad(db, user, job.id, job.bot_id, lang)}
        db.commit()
    return job.payload["ad"]


def reward_referrer(db, job, telegram, username):
    """The invited user's first successful result counts the invite; the inviter hears about it."""
    try:
        result = monetization.count_referral(db, job.user_id)
        if not result:
            return
        lang = users.language(db, result["referrer"])
        if result["rewarded"]:
            text = signed(lang, "referral_reward", username, count=result["count"], days=result["days"], date=result["until"][:10])
        else:
            text = signed(lang, "referral_joined", username, count=result["count"] % result["needed"], needed=result["needed"])
        telegram.message(result["referrer"], text)
    except Exception:
        # The download is already delivered; a missed notice must never turn it into an error.
        log.warning('{"event":"referral_notice_failed","job_id":"%s"}', job.id)


def download_error_code(exc: Exception) -> str:
    """Map yt-dlp errors to an honest user message without exposing provider output."""
    text = str(exc).lower()
    if "unsupported url" in text:
        return "unsupported"
    # Restricted items are never fetched with an account: the user is told the item is not public.
    if any(marker in text for marker in ("registered users", "login required", "log in", "private", "restricted")):
        return "login_required"
    if "no video formats" in text or "there is no video" in text:
        return "no_media"
    return "unavailable"


def fail(db, job, code, telegram, lang, status, username):
    # Only a controlled error code is stored: provider errors may contain URLs or tokens.
    job.status, job.error, job.completed_at = "failed", code, now()
    db.execute(delete(Usage).where(Usage.job_id == job.id))  # a failed job does not use up the daily limit
    db.commit()
    log.warning('{"event":"job_failed","job_id":"%s","code":"%s"}', job.id, code)
    if status:
        status.clear()
    if telegram:
        try:
            p, owner = policy(db), db.get(User, job.user_id)
            limit = max(p.max_upload_bytes if job.kind == "upload" else monetization.download_limit(db, owner, p), 1) // 1_000_000
            if code == "file_size" and job.kind != "upload" and limit < p.max_download_bytes // 1_000_000:
                code = "premium_size"  # bigger files come with Premium
            telegram.message(job.user_id, signed(lang, code, username, limit=limit))
        except Exception:
            log.exception('{"event":"failure_message_not_sent","job_id":"%s"}', job.id)


@celery.task
def reconcile():
    """Recover jobs lost by a broker or worker crash."""
    with Session() as db:
        stale = now() - timedelta(seconds=cfg.job_timeout + 150)
        for job in db.scalars(select(Job).where(Job.status == "processing", Job.started_at < stale)):
            job.status = "queued" if job.attempts < MAX_ATTEMPTS else "failed"
            if job.status == "failed":
                job.error, job.completed_at = "worker_timeout", now()
        db.commit()
        queued_before = now() - timedelta(seconds=60)
        stuck = db.execute(select(Job.id, User.premium_until).join(User, User.id == Job.user_id)
                           .where(Job.status == "queued", Job.created_at < queued_before).limit(500)).all()
        for job_id, premium_until in stuck:
            premium = bool(premium_until and aware(premium_until) > now())
            process.apply_async([job_id], queue=PRIORITY_QUEUE if premium else DEFAULT_QUEUE)
        from workers import broadcast  # ad posts whose batch chain was interrupted
        broadcast.resume(db)
        from backend.services import billing  # unpaid payment links older than their lifetime
        billing.expire_stale(db)


@celery.task
def cleanup():
    """Retention: delete expired files from storage and stale temp directories."""
    with Session() as db:
        for file in db.scalars(select(UploadedFile).where(UploadedFile.expires_at <= now(), UploadedFile.deleted.is_(False)).limit(500)):
            storage.delete_file(db, file)
    root = Path(cfg.temp_root)
    if root.exists():
        for item in root.glob("job-*"):
            if item.is_dir() and item.stat().st_mtime < (now() - timedelta(seconds=cfg.job_timeout + 300)).timestamp():
                shutil.rmtree(item, ignore_errors=True)
