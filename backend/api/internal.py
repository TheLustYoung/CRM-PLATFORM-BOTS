"""API used only by the bot processes (authenticated by per-bot service keys, blocked in Plesk)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from backend.config import settings
from backend.database import session
from backend.api.deps import bot_required, require
from backend.api.schemas import Checkout, Identity, Paid, Register, Submit, SelectFormat, Upload, Language, Heartbeat
from backend.models import Bot, Job, UploadedFile, User, now, aware
from backend.services import billing, i18n, jobs, monetization, users
from backend.services.security import DomainError
from backend.services.limits import policy
import storage

router = APIRouter(prefix="/internal", tags=["internal"])
INFO_FIELDS = ("title", "channel", "description", "thumbnail", "webpage_url", "date", "duration", "views", "likes", "comments", "platform", "license")


def job_response(result) -> dict:
    job, created = result
    return {"id": job.id, "status": job.status, "created": created}


@router.post("/heartbeat")
def heartbeat(data: Heartbeat, kind=Depends(bot_required), db=Depends(session)):
    bot = require(db, Bot, kind)
    bot.username = data.username or bot.username
    bot.last_seen = now()
    db.commit()
    from backend.services import bot_tokens, translations
    return {"enabled": bot.enabled, "translations": translations.load(db),  # dashboard edits reach the bot within 30 s
            "token": bot_tokens.fingerprint(settings().bot_token(kind))}  # a new token set in the dashboard restarts the bot


def money(db, user) -> dict:
    return monetization.profile(db, user, users.daily_limit(db, user), users.used_today(db, user.id))


@router.post("/register")
def register(data: Register, kind=Depends(bot_required), db=Depends(session)):
    user, created = users.register(db, kind, data.user_id, data.username, data.first_name, data.language_code, data.referrer)
    bot = db.get(Bot, kind)
    return {"language": users.language(db, data.user_id), "created": created, "welcome": bot.welcome_text,
            "languages": i18n.languages(), "upload_limit_mb": min(policy(db).max_upload_bytes, settings().telegram_receive_bytes) // 1_000_000,
            "money": money(db, user)}


@router.post("/premium/checkout")
def premium_checkout(data: Checkout, kind=Depends(bot_required), db=Depends(session)):
    """Pre-checkout: Telegram asks the bot to confirm the order before charging Stars."""
    user, _ = users.register(db, kind, data.user_id, data.username)
    plan = monetization.checkout_plan(db, data.payload, data.amount)
    return {"ok": True, "days": plan.days, "premium": monetization.is_premium(user)}


@router.post("/premium/activate")
def premium_activate(data: Paid, kind=Depends(bot_required), db=Depends(session)):
    """Successful payment: add the plan's days. The charge id makes a repeated update harmless."""
    user = require(db, User, data.user_id)
    plan = monetization.paid_plan(data.payload, data.amount)
    until = monetization.grant(db, user, plan.days, "stars", stars=plan.stars, bot_id=kind, charge_id=data.charge_id, tier=plan.tier)
    billing.record_stars(db, user, kind, plan, data.charge_id, users.language(db, user.id))
    return {"premium_until": until.isoformat(), "days": plan.days, "money": money(db, user)}


class OrderRequest(Identity):
    plan: str = Field(pattern=monetization.PLAN_KEY)


@router.post("/premium/order")
def premium_order(data: OrderRequest, kind=Depends(bot_required), db=Depends(session)):
    """Card/crypto: an order and the link to our payment page, where the user pays and comes back to the bot."""
    user, _ = users.register(db, kind, data.user_id, data.username)
    plan = billing.plan_for(db, data.plan)
    methods = billing.page_methods(db, plan)
    if not methods:
        raise DomainError("premium_unavailable")
    order = billing.create_order(db, user, kind, data.plan, users.language(db, user.id))
    return {"url": f"{billing.public_base(db)}/pay/{order.token}", "methods": methods}


@router.post("/language")
def language(data: Language, kind=Depends(bot_required), db=Depends(session)):
    users.register(db, kind, data.user_id, data.username)
    return {"language": users.set_language(db, data.user_id, data.language)}


@router.post("/metadata")
def metadata(data: Submit, kind=Depends(bot_required), db=Depends(session)):
    return job_response(jobs.submit_metadata(db, kind, data.user_id, data.username, data.url, data.request_key))


@router.post("/download")
def download(data: SelectFormat, kind=Depends(bot_required), db=Depends(session)):
    return job_response(jobs.select_format(db, kind, data.user_id, data.username, data.metadata_id, data.index))


@router.post("/upload")
def upload(data: Upload, kind=Depends(bot_required), db=Depends(session)):
    return job_response(jobs.submit_upload(db, kind, data.user_id, data.username, data.request_key, data.file_id, data.name, data.size))


@router.post("/jobs/{id}/refresh")
def refresh(id: str, data: Identity, kind=Depends(bot_required), db=Depends(session)):
    return job_response(jobs.refresh_metadata(db, kind, data.user_id, data.username, id))


@router.post("/jobs/{id}/cancel")
def cancel(id: str, data: Identity, kind=Depends(bot_required), db=Depends(session)):
    job = jobs.cancel(db, kind, data.user_id, id)
    return {"id": job.id, "status": job.status}


@router.post("/jobs/{id}/info")
def info(id: str, data: Identity, kind=Depends(bot_required), db=Depends(session)):
    job = jobs.owned_metadata(db, kind, data.user_id, id)
    if job.status != "completed":
        raise HTTPException(404, "not_found")
    return {key: job.result.get(key) for key in INFO_FIELDS} | {"url": job.source_url}


@router.post("/files")
def my_files(data: Identity, kind=Depends(bot_required), db=Depends(session)):
    users.register(db, kind, data.user_id, data.username)
    items = db.scalars(select(UploadedFile).where(UploadedFile.user_id == data.user_id, UploadedFile.bot_id == kind,
                                                  UploadedFile.deleted.is_(False), UploadedFile.expires_at > now())
                       .order_by(UploadedFile.created_at.desc()).limit(20))
    return [{"id": f.id, "name": f.name, "size": f.size, "expires_at": aware(f.expires_at).isoformat(), "url": storage.public_url(db, f)} for f in items]


@router.post("/history")
def history(data: Identity, kind=Depends(bot_required), db=Depends(session)):
    """The user's last 10 downloads in this bot, with a public link when the file is still available."""
    users.register(db, kind, data.user_id, data.username)
    items = db.scalars(select(Job).where(Job.user_id == data.user_id, Job.bot_id == kind, Job.kind == "download")
                       .order_by(Job.created_at.desc()).limit(10))
    result = []
    for job in items:
        file = db.get(UploadedFile, job.output_file_id) if job.output_file_id else None
        url = storage.public_url(db, file) if file and aware(file.expires_at) > now() else None
        result.append({"title": (job.payload or {}).get("title") or job.source_url, "label": (job.payload or {}).get("label"),
                       "platform": job.platform, "status": job.status, "created_at": aware(job.created_at).isoformat(), "url": url})
    return result


def owned_file(db, kind, data, id) -> UploadedFile:
    users.register(db, kind, data.user_id, data.username)
    file = require(db, UploadedFile, id)
    if file.user_id != data.user_id:
        raise HTTPException(404, "not_found")
    return file


@router.post("/files/{id}/revoke")
def own_revoke(id: str, data: Identity, kind=Depends(bot_required), db=Depends(session)):
    storage.revoke_file(db, owned_file(db, kind, data, id))
    return {"ok": True}


@router.post("/files/{id}/delete")
def own_delete(id: str, data: Identity, kind=Depends(bot_required), db=Depends(session)):
    storage.delete_file(db, owned_file(db, kind, data, id))
    return {"ok": True}
