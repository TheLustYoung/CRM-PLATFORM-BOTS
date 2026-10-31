from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Literal
import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, func, or_
from backend.config import settings
from backend.database import session
from backend.api.deps import admin_required, row, require, audit
from backend.api.schemas import UserPatch, BotPatch, PremiumGrant
from backend.models import User, Bot, BotUser, Job, UploadedFile, Audit, Admin, SystemSetting, Compatibility, Payment, now, aware
from backend.services import analytics, botprofile, i18n, monetization, translations, team, users as user_service
from backend.services.security import DomainError
from workers.telegram import Telegram, TelegramError, TelegramRetry
from backend.services.limits import Policy, policy
import storage

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_required)])
PAGE = 50
# Job payload holds Telegram file_ids and result may hold expiring provider URLs: never expose them.
JOB_FIELDS = {"id", "user_id", "bot_id", "kind", "platform", "source_url", "selected_format", "status", "attempts",
              "created_at", "started_at", "completed_at", "error", "output_file_id"}


def count(db, model, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


@router.get("/me")
def me(admin=Depends(admin_required), db=Depends(session)):
    perms = team.permissions(db, admin)
    return {"username": admin.username, "role": admin.role, "permissions": [p for p in team.PERMISSIONS if p in perms]}


@router.get("/overview")
def overview(db=Depends(session)):
    day_ago, week_ago = now() - timedelta(days=1), now() - timedelta(days=7)
    per_day = db.execute(select(func.date(Job.created_at), Job.kind, func.count()).where(Job.created_at >= week_ago)
                         .group_by(func.date(Job.created_at), Job.kind)).all()
    per_bot = db.execute(select(Job.bot_id, Job.status, func.count()).group_by(Job.bot_id, Job.status)).all()
    return {
        "users": count(db, User), "active_users": count(db, User, User.last_seen >= day_ago),
        "new_users_week": count(db, User, User.created_at >= week_ago),
        "downloads": count(db, Job, Job.kind == "download"),
        "successful_downloads": count(db, Job, Job.kind == "download", Job.status == "completed"),
        "failed_downloads": count(db, Job, Job.kind == "download", Job.status == "failed"),
        "uploads": count(db, Job, Job.kind == "upload", Job.status == "completed"),
        "active_jobs": count(db, Job, Job.status.in_(["queued", "processing"])),
        "files": count(db, UploadedFile, UploadedFile.deleted.is_(False)),
        "storage_bytes": db.scalar(select(func.coalesce(func.sum(UploadedFile.size), 0)).where(UploadedFile.deleted.is_(False))),
        "daily": [{"date": str(d), "kind": k, "count": c} for d, k, c in per_day],
        "bots": [{"bot_id": b, "status": s, "count": c} for b, s, c in per_bot],
        **activity(db),
    }


ACTIVITY_DAYS = 30
ACTIVITY_ROWS = 50_000  # enough for the charts; the reports page has the exact totals


def activity(db) -> dict:
    """The overview charts, all from the jobs table (last 30 days, UTC): outcome of downloads per day, jobs per source,
    a weekday × hour heatmap (when users are active: a hint for scheduling broadcasts and channel posts) and the
    funnel from a link to a delivered file."""
    since = now() - timedelta(days=ACTIVITY_DAYS)
    rows = db.execute(select(Job.created_at, Job.kind, Job.status, Job.platform).where(Job.created_at >= since)
                      .order_by(Job.created_at.desc()).limit(ACTIVITY_ROWS)).all()
    outcome: dict[str, dict[str, int]] = {}
    sources: dict[str, int] = {}
    heat = [[0] * 24 for _ in range(7)]
    funnel = {"links": 0, "downloads": 0, "delivered": 0, "failed": 0}
    for created, kind, status, platform in rows:
        moment = aware(created)
        heat[moment.weekday()][moment.hour] += 1
        if kind == "metadata":
            funnel["links"] += 1
            sources[platform or "direct"] = sources.get(platform or "direct", 0) + 1
        elif kind == "download":
            funnel["downloads"] += 1
            day = outcome.setdefault(moment.date().isoformat(), {"completed": 0, "failed": 0})
            if status in ("completed", "failed"):
                day[status] += 1
                funnel["delivered" if status == "completed" else "failed"] += 1
        elif kind == "upload":
            sources["telegram"] = sources.get("telegram", 0) + 1
    demo = db.scalar(select(User.id).where(User.id >= DEMO_USER_IDS).limit(1)) is not None
    return {"outcome": outcome, "sources": sources, "heatmap": heat, "funnel": funnel, "activity_days": ACTIVITY_DAYS, "demo_data": demo}


DEMO_USER_IDS = 900_000_000  # synthetic presentation data (infrastructure/scripts/demo_data.py): the dashboard says so


@router.get("/analytics")
def analytics_report(period: Literal["day", "week", "month"] = "day", count: int = Query(default=30, ge=1, le=400),
                     bot: str | None = None, db=Depends(session)):
    """Reports by day, week or month (calculation rules: backend/services/analytics.py)."""
    return analytics.report(db, period, count, bot or None)


@router.get("/analytics.csv")
def analytics_csv(period: Literal["day", "week", "month"] = "day", count: int = Query(default=30, ge=1, le=400),
                  bot: str | None = None, db=Depends(session), admin=Depends(admin_required)):
    audit(db, admin, "analytics.export", f"{period}·{count}")
    body = analytics.csv_report(analytics.report(db, period, count, bot or None))
    return Response(body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="report-{period}-{analytics.today()}.csv"'})


@router.get("/translations")
def translation_languages(db=Depends(session)):
    """Every language with its state (on/off) and how many of its texts were edited in the dashboard."""
    edited, disabled = translations.counts(db), translations.load(db)["disabled"]
    return [{"code": code, "name": name, "enabled": code not in disabled, "edited": edited.get(code, 0),
             "fallback": code == i18n.FALLBACK, "rtl": i18n.is_rtl(code)} for code, name in i18n.all_languages().items()]


@router.get("/translations/{lang}")
def translation_texts(lang: str, db=Depends(session)):
    try:
        return translations.texts(db, lang)
    except translations.TranslationError as error:
        raise HTTPException(404, error.code) from None


class TranslationEdit(BaseModel):
    texts: dict[str, str] = Field(max_length=2000)


@router.put("/translations/{lang}")
def save_translations(lang: str, data: TranslationEdit, db=Depends(session), admin=Depends(admin_required)):
    try:
        edited = translations.save(db, lang, data.texts)
    except translations.TranslationError as error:
        raise HTTPException(400, f"{error.code}:{error.key}" if error.key else error.code) from None
    audit(db, admin, "translations.save", f"{lang} · {len(data.texts)} texts")
    return {"edited": edited}


@router.post("/translations/{lang}/{action}")
def switch_language(lang: str, action: Literal["enable", "disable"], db=Depends(session), admin=Depends(admin_required)):
    try:
        disabled = translations.set_enabled(db, lang, action == "enable")
    except translations.TranslationError as error:
        raise HTTPException(400, error.code) from None
    audit(db, admin, f"language.{action}", lang)
    return {"disabled": disabled}


@router.get("/monitoring")
def monitoring_status(db=Depends(session)):
    from workers import monitor
    status = db.get(SystemSetting, monitor.STATUS_KEY)
    return {"settings": monitor.public_options(db), "status": status.value if status else None}


class MonitoringSettings(BaseModel):
    chat_id: str = Field(default="", max_length=32, pattern=r"^(-?\d{1,20}|@[A-Za-z0-9_]{4,32})?$")
    disk_min_gb: int = Field(default=5, ge=0, le=100_000)
    error_rate: int = Field(default=50, ge=1, le=100)
    queue_minutes: int = Field(default=15, ge=1, le=1440)
    bot_silent_minutes: int = Field(default=5, ge=1, le=1440)
    email_to: str = Field(default="", max_length=500, pattern=r"^([^@\s,]+@[^@\s,]+\.[^@\s,]+)(\s*,\s*[^@\s,]+@[^@\s,]+\.[^@\s,]+)*$|^$")
    email_from: str = Field(default="", max_length=120)
    email_provider: Literal["", "sendgrid", "resend"] = ""
    email_key: str = Field(default="", max_length=300)  # empty = keep the saved key


@router.put("/monitoring")
def save_monitoring(data: MonitoringSettings, db=Depends(session), admin=Depends(admin_required)):
    from workers import monitor
    from backend.services.security import encrypt
    values = data.model_dump()
    values["email_key"] = encrypt(data.email_key.strip()) if data.email_key.strip() else monitor.options(db).get("email_key", "")
    db.merge(SystemSetting(key=monitor.SETTINGS_KEY, value=values))
    db.commit()
    audit(db, admin, "monitoring.settings", data.chat_id or "-")
    return monitoring_status(db)


@router.post("/monitoring/check")
def run_monitoring(db=Depends(session)):
    """Runs the checks now and, when asked, sends a test alert to the configured chat."""
    from workers import monitor
    status = monitor.measure(db)
    db.merge(SystemSetting(key=monitor.STATUS_KEY, value=status))
    db.commit()
    try:
        sent = monitor.alert(db, "Test alert: monitoring works. " + (f"{len(status['problems'])} problem(s) now." if status["problems"] else "No problems now."))
    except Exception as error:
        raise HTTPException(400, f"Telegram: {getattr(error, 'description', type(error).__name__)}") from None
    return {**monitoring_status(db), "alert_sent": sent}


@router.get("/bots")
def bots(db=Depends(session)):
    result = []
    for bot in db.scalars(select(Bot).order_by(Bot.id)):
        data = row(bot)
        data["configured"] = bool(settings().bot_token(bot.id))
        data["online"] = bool(bot.last_seen and aware(bot.last_seen) > now() - timedelta(seconds=120))
        data["users"] = count(db, BotUser, BotUser.bot_id == bot.id)
        data["jobs_today"] = count(db, Job, Job.bot_id == bot.id, Job.created_at >= now().replace(hour=0, minute=0, second=0, microsecond=0))
        data["errors_today"] = count(db, Job, Job.bot_id == bot.id, Job.status == "failed", Job.created_at >= now().replace(hour=0, minute=0, second=0, microsecond=0))
        result.append(data)
    return result


@router.patch("/bots/{id}")
def patch_bot(id: str, data: BotPatch, db=Depends(session), admin=Depends(admin_required)):
    bot = require(db, Bot, id)
    bot.enabled, bot.daily_limit = data.enabled, data.daily_limit
    if "platforms" in data.model_fields_set:
        from backend.services.limits import ALL_PLATFORM_NAMES
        unknown = [p for p in data.platforms or [] if p not in ALL_PLATFORM_NAMES]
        if unknown:
            raise HTTPException(400, f"Unknown platform: {', '.join(unknown)}")
        bot.platforms = data.platforms or None
    bot.welcome_text = (data.welcome_text or "").strip() or None
    audit(db, admin, "bot.update", id)
    return row(bot)


def telegram_call(action):
    """Run a Bot API action for the panel; Telegram's own error text is shown to the admin."""
    try:
        return action()
    except TelegramRetry as exc:
        wait = f" Retry in {exc.retry_after} s." if exc.retry_after else ""
        raise HTTPException(429, "Telegram limits how often this can be changed." + wait) from None
    except TelegramError as exc:
        raise HTTPException(502, f"Telegram: {exc.description}") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Telegram is unreachable from the server") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


class BotToken(BaseModel):
    token: str = Field(max_length=100)


@router.get("/bots/{id}/token")
def bot_token_status(id: str, db=Depends(session)):
    """Where the bot's token comes from (the token itself is never returned)."""
    from backend.services import bot_tokens
    bot = require(db, Bot, id)
    return {"source": bot_tokens.source(db, bot.id, settings().env_bot_token(bot.id)), "username": bot.username}


@router.put("/bots/{id}/token")
def set_bot_token(id: str, data: BotToken, db=Depends(session), admin=Depends(admin_required)):
    from backend.services import bot_tokens
    bot = require(db, Bot, id)
    try:
        me = bot_tokens.save(db, bot.id, data.token)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    bot.username = me["username"] or bot.username
    db.commit()
    audit(db, admin, "bot.token", f"{id} → @{me['username']}")
    return {"source": "dashboard", "username": me["username"]}


@router.delete("/bots/{id}/token")
def remove_bot_token(id: str, db=Depends(session), admin=Depends(admin_required)):
    from backend.services import bot_tokens
    bot = require(db, Bot, id)
    bot_tokens.remove(db, bot.id)
    audit(db, admin, "bot.token", f"{id} → .env")
    return {"source": bot_tokens.source(db, bot.id, settings().env_bot_token(bot.id)), "username": bot.username}


def configured_bot(db, id: str) -> Bot:
    bot = require(db, Bot, id)
    if not settings().bot_token(bot.id):
        raise HTTPException(400, "Bot token is not configured on the server")
    return bot


@router.get("/bots/{id}/profile")
def get_profile(id: str, lang: str = "", db=Depends(session)):
    bot = configured_bot(db, id)
    profile = telegram_call(lambda: botprofile.read(bot.id, botprofile.check_language(lang)))
    return {**profile.model_dump(), "language": lang, "languages": {"": "default", **i18n.languages()}, "username": bot.username}


@router.put("/bots/{id}/profile")
def put_profile(id: str, data: botprofile.Profile, lang: str = "", db=Depends(session), admin=Depends(admin_required)):
    bot = configured_bot(db, id)
    profile = telegram_call(lambda: botprofile.write(bot.id, botprofile.check_language(lang), data))
    audit(db, admin, "bot.profile", f"{id}:{lang or 'default'}")
    return {**profile.model_dump(), "language": lang}


@router.get("/bots/{id}/photo")
def get_photo(id: str, db=Depends(session)):
    bot = configured_bot(db, id)
    content = telegram_call(lambda: botprofile.photo(bot.id))
    if not content:
        raise HTTPException(404, "No profile photo")
    return Response(content, media_type="image/jpeg", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/bots/{id}/photo")
async def upload_photo(id: str, file: UploadFile, db=Depends(session), admin=Depends(admin_required)):
    bot = configured_bot(db, id)
    content = await file.read(botprofile.PHOTO_LIMIT + 1)
    await run_in_threadpool(telegram_call, lambda: botprofile.set_photo(bot.id, content, file.content_type or ""))
    audit(db, admin, "bot.photo", id)
    return {"ok": True}


@router.delete("/bots/{id}/photo")
def delete_photo(id: str, db=Depends(session), admin=Depends(admin_required)):
    bot = configured_bot(db, id)
    telegram_call(lambda: botprofile.remove_photo(bot.id))
    audit(db, admin, "bot.photo_remove", id)
    return {"ok": True}


@router.get("/users")
def list_users(q: str = "", offset: int = Query(0, ge=0), db=Depends(session)):
    statement = select(User)
    q = q.strip().lstrip("@")
    if q:
        statement = statement.where(or_(User.username.ilike(f"%{q[:64]}%"), User.id == (int(q) if q.isdigit() and len(q) < 19 else -1)))
    return [row(u) for u in db.scalars(statement.order_by(User.last_seen.desc()).offset(offset).limit(PAGE))]


@router.get("/users/{id}")
def user_detail(id: int, db=Depends(session)):
    user = require(db, User, id)
    return {**row(user), "language": user_service.language(db, id),
            "bots": list(db.scalars(select(BotUser.bot_id).where(BotUser.user_id == id))),
            "downloads": count(db, Job, Job.user_id == id, Job.kind == "download"),
            "uploads": count(db, Job, Job.user_id == id, Job.kind == "upload"),
            "failed": count(db, Job, Job.user_id == id, Job.status == "failed"),
            "files": count(db, UploadedFile, UploadedFile.user_id == id, UploadedFile.deleted.is_(False)),
            # the user's payments and subscription history
            "payments": [{"created_at": p.created_at, "source": p.source, "days": p.days, "stars": p.stars, "bot_id": p.bot_id}
                         for p in db.scalars(select(Payment).where(Payment.user_id == id).order_by(Payment.created_at.desc()).limit(20))],
            "tier": monetization.tier_of(db, user).name if monetization.tier_of(db, user) else None}


class FileKeep(BaseModel):
    days: int = Field(ge=0, le=36500)  # 0 = permanent


@router.post("/files/{id}/keep")
def keep_file(id: str, data: FileKeep, db=Depends(session), admin=Depends(admin_required)):
    """Extend a file's link or make it permanent (it is then never removed by the retention cleanup)."""
    from datetime import datetime, timezone
    file = require(db, UploadedFile, id)
    if file.deleted:
        raise HTTPException(400, "The file is deleted")
    file.expires_at = datetime(2100, 1, 1, tzinfo=timezone.utc) if data.days == 0 else now() + timedelta(days=data.days)
    db.commit()
    audit(db, admin, "file.keep", f"{id}:{data.days or 'permanent'}")
    return {"expires_at": file.expires_at, "permanent": data.days == 0}


@router.patch("/users/{id}")
def patch_user(id: int, data: UserPatch, db=Depends(session), admin=Depends(admin_required)):
    user = require(db, User, id)
    user.banned, user.daily_limit = data.banned, data.daily_limit
    if data.credits is not None and data.credits != (user.credits or 0):
        audit(db, admin, "user.credits", f"{id}:{user.credits or 0}→{data.credits}")
        user.credits = data.credits
    audit(db, admin, "user.ban" if data.banned else "user.update", id)
    return row(user)


@router.get("/jobs")
def jobs(user_id: int | None = None, status: str | None = None, bot_id: str | None = None,
         offset: int = Query(0, ge=0), db=Depends(session)):
    statement = select(Job)
    if user_id:
        statement = statement.where(Job.user_id == user_id)
    if status:
        statement = statement.where(Job.status == status)
    if bot_id:
        statement = statement.where(Job.bot_id == bot_id)
    items = db.scalars(statement.order_by(Job.created_at.desc()).offset(offset).limit(PAGE))
    return [{k: v for k, v in row(j).items() if k in JOB_FIELDS} for j in items]


# What the dashboard's View window shows about a link: never the provider's media URLs, cookies or formats.
JOB_INFO = ("title", "channel", "description", "webpage_url", "date", "duration", "views", "likes", "comments", "count", "restricted")


@router.get("/jobs/{id}")
def job_detail(id: str, db=Depends(session)):
    """One job in full: what was requested, what was found, the files that were delivered and who asked."""
    job = require(db, Job, id)
    info = job.result if job.kind == "metadata" else None
    if not info and job.source_url:  # a download: the details come from the card the user chose the format on
        card = db.scalar(select(Job).where(Job.user_id == job.user_id, Job.kind == "metadata", Job.source_url == job.source_url,
                                           Job.status == "completed").order_by(Job.created_at.desc()).limit(1))
        info = card.result if card else None
    info = {k: v for k, v in (info or {}).items() if k in JOB_INFO and v not in (None, "", [])}
    if not info.get("title") and (job.payload or {}).get("title"):
        info["title"] = job.payload["title"]
    if isinstance(info.get("description"), str):
        info["description"] = info["description"][:2000]
    files = db.scalars(select(UploadedFile).where(UploadedFile.job_id == job.id).order_by(UploadedFile.created_at))
    user = db.get(User, job.user_id)
    return {**{k: v for k, v in row(job).items() if k in JOB_FIELDS}, "info": info,
            "files": [{"id": f.id, "name": f.name, "mime": f.mime, "size": f.size, "deleted": f.deleted, "expires_at": f.expires_at}
                      for f in files],
            "user": {"id": user.id, "username": user.username, "first_name": user.first_name} if user else None}


@router.get("/files")
def files(user_id: int | None = None, offset: int = Query(0, ge=0), db=Depends(session)):
    statement = select(UploadedFile)
    if user_id:
        statement = statement.where(UploadedFile.user_id == user_id)
    items = db.scalars(statement.order_by(UploadedFile.created_at.desc()).offset(offset).limit(PAGE))
    return [{**{k: v for k, v in row(f).items() if k != "object_key"}, "url": storage.public_url(db, f)} for f in items]


# Types the dashboard may show inline; anything else (HTML, SVG, scripts…) is only ever downloaded.
PREVIEW_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "video/mp4", "video/webm", "video/quicktime",
                 "audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/x-m4a", "application/pdf", "text/plain"}


@router.get("/files/{id}/content")
def file_content(id: str, download: bool = False, db=Depends(session)):
    """The file itself for the dashboard's View window (inline for safe types) and its Download button."""
    from urllib.parse import quote
    from fastapi.responses import StreamingResponse
    file = require(db, UploadedFile, id)
    if file.deleted:
        raise HTTPException(404, "not_found")
    try:
        body, close = storage.open_object(file.object_key)
    except storage.ObjectMissing:
        raise HTTPException(404, "file_missing")

    def chunks():
        try:
            yield from body
        finally:
            close()
    mime = (file.mime or "").split(";")[0].strip().lower()
    inline = not download and mime in PREVIEW_TYPES
    headers = {"Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(file.name)}",
               "Content-Length": str(file.size), "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"}
    if not (inline and mime == "application/pdf"):  # the browser's PDF viewer refuses to run in a sandboxed document
        headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox"
    return StreamingResponse(chunks(), media_type=mime if inline else "application/octet-stream", headers=headers)


@router.post("/files/{id}/revoke")
def revoke(id: str, db=Depends(session), admin=Depends(admin_required)):
    storage.revoke_file(db, require(db, UploadedFile, id))
    audit(db, admin, "file.revoke", id)
    return {"ok": True}


@router.delete("/files/{id}")
def delete(id: str, db=Depends(session), admin=Depends(admin_required)):
    storage.delete_file(db, require(db, UploadedFile, id))
    audit(db, admin, "file.delete", id)
    return {"ok": True}


@router.get("/settings")
def get_settings(db=Depends(session)):
    return {**policy(db).model_dump(), "languages": i18n.languages()}


@router.patch("/settings")
def patch_settings(data: Policy, db=Depends(session), admin=Depends(admin_required)):
    db.merge(SystemSetting(key="policy", value=data.model_dump()))
    audit(db, admin, "settings.update", "policy")
    return {**data.model_dump(), "languages": i18n.languages()}


@router.get("/monetization")
def monetization_settings(db=Depends(session)):
    return monetization.settings(db).model_dump()


@router.put("/monetization")
def save_monetization(data: monetization.Settings, db=Depends(session), admin=Depends(admin_required)):
    saved = monetization.save(db, data)
    audit(db, admin, "monetization.update", ", ".join(k for k in ("premium", "referrals", "channel", "ads")
                                                     if getattr(saved, f"{k}_enabled")) or "all off")
    return saved.model_dump()


@router.get("/monetization/stats")
def monetization_stats(db=Depends(session)):
    recent = db.execute(select(Payment, User.username).join(User, User.id == Payment.user_id)
                        .order_by(Payment.created_at.desc()).limit(20)).all()
    return {**monetization.stats(db),
            "recent": [{**{k: v for k, v in row(p).items() if k != "charge_id"}, "username": name} for p, name in recent]}


def channel_status(kind: str, chat: str) -> dict:
    """Can this bot see channel members? It must be an administrator of the channel to check subscriptions."""
    token = settings().bot_token(kind)
    if not token:
        return {"bot": kind, "chat": chat, "ok": False, "detail": "no token"}
    try:
        with Telegram(kind) as telegram:
            member = telegram.call("getChatMember", {"chat_id": chat, "user_id": int(token.split(":")[0])})
        ok = member.get("status") in {"administrator", "creator"}
        return {"bot": kind, "chat": chat, "ok": ok, "detail": member.get("status", "unknown")}
    except TelegramError as error:
        return {"bot": kind, "chat": chat, "ok": False, "detail": error.description}
    except Exception as error:
        return {"bot": kind, "chat": chat, "ok": False, "detail": type(error).__name__}


@router.post("/monetization/channel-test")
def test_channel(db=Depends(session)):
    chats = [c["chat"] for c in monetization.settings(db).required_channels()]
    if not chats:
        raise HTTPException(400, "Set the channel first")
    kinds = list(db.scalars(select(Bot.id).order_by(Bot.id)))
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(lambda pair: channel_status(*pair), [(kind, chat) for chat in chats for kind in kinds]))


@router.post("/users/{id}/premium")
def grant_premium(id: int, data: PremiumGrant, db=Depends(session), admin=Depends(admin_required)):
    """Gift Premium days (support, partners, giveaways) or remove Premium with 0 days."""
    user = require(db, User, id)
    if data.days:
        if data.tier not in {t.key for t in monetization.settings(db).tiers}:
            raise HTTPException(400, "Unknown tier")
        monetization.grant(db, user, data.days, "admin", tier=data.tier)
    else:
        monetization.revoke(db, user)
    audit(db, admin, "user.premium", f"{id}:{data.days}d:{data.tier}")
    return row(user)


@router.get("/compatibility")
def compatibility(db=Depends(session)):
    return [row(c) for c in db.scalars(select(Compatibility).order_by(Compatibility.platform))]


@router.get("/audit")
def audit_log(offset: int = Query(0, ge=0), db=Depends(session)):
    items = db.execute(select(Audit, Admin.username).join(Admin, Admin.id == Audit.admin_id)
                       .order_by(Audit.created_at.desc()).offset(offset).limit(PAGE)).all()
    return [{**row(a), "admin": name} for a, name in items]
