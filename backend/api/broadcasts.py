"""Dashboard «Ads» tab: write a Telegram-formatted post, send it to the bots' users, delete it from their chats."""
from datetime import timedelta
from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from backend.config import settings
from backend.database import session
from backend.api.deps import admin_required, audit, require
from backend.models import Bot, Broadcast, aware, now
from backend.services import broadcasts, limits, queue
from workers.telegram import Telegram, TelegramError, TelegramRetry

router = APIRouter(prefix="/api/admin/broadcasts", tags=["admin"], dependencies=[Depends(admin_required)])
SEND_TASK, DELETE_TASK = "workers.broadcast.send", "workers.broadcast.delete"
IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")  # JPEG, PNG, WebP


def connected_bots(db) -> list[str]:
    """Bots set up in the dashboard with a token: the only ones that can post."""
    return [bot.id for bot in db.scalars(select(Bot).order_by(Bot.id)) if settings().bot_token(bot.id)]


def chosen_bots(db, value: str) -> list[str]:
    available = connected_bots(db)
    picked = [b.strip() for b in value.split(",") if b.strip()]
    unknown = [b for b in picked if b not in available]
    if unknown:
        raise HTTPException(400, f"Bot not connected: {', '.join(unknown)}")
    return picked


async def read_photo(photo: UploadFile | None) -> bytes | None:
    if photo is None or not photo.filename:
        return None
    content = await photo.read(broadcasts.PHOTO_LIMIT + 1)
    if len(content) > broadcasts.PHOTO_LIMIT:
        raise HTTPException(400, "The photo must be up to 10 MB")
    if not content.startswith(IMAGE_SIGNATURES):
        raise HTTPException(400, "The photo must be JPEG, PNG or WebP")
    return content


def view(db, b: Broadcast) -> dict:
    age = now() - aware(b.created_at)
    return {"id": b.id, "text": b.text, "button_text": b.button_text, "button_url": b.button_url, "has_photo": b.photo is not None,
            "bots": b.bots, "skip_premium": b.skip_premium, "status": b.status, "audience": b.audience,
            "created_at": b.created_at, "finished_at": b.finished_at, "deleted_at": b.deleted_at,
            "deletable": age < timedelta(hours=broadcasts.DELETE_WINDOW_HOURS), **broadcasts.counts(db, b)}


@router.get("")
def list_broadcasts(db=Depends(session)):
    return {"bots": connected_bots(db), "delete_window_hours": broadcasts.DELETE_WINDOW_HOURS,
            "items": [view(db, b) for b in db.scalars(select(Broadcast).order_by(Broadcast.created_at.desc()).limit(50))]}


@router.get("/audience")
def audience(bots: str = "", skip_premium: bool = True, db=Depends(session)):
    return broadcasts.audience(db, chosen_bots(db, bots), skip_premium)


@router.get("/{id}/photo")
def photo(id: str, db=Depends(session)):
    b = require(db, Broadcast, id)
    if b.photo is None:
        raise HTTPException(404, "No photo")
    return Response(b.photo, media_type="application/octet-stream", headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.post("")
async def create(text: str = Form(max_length=20_000), button_text: str = Form(default="", max_length=64),
                 button_url: str = Form(default="", max_length=300), bots: str = Form(max_length=200),
                 skip_premium: bool = Form(default=True), photo: UploadFile | None = None,
                 db=Depends(session), admin=Depends(admin_required)):
    picked, image = chosen_bots(db, bots), await read_photo(photo)
    try:
        body = broadcasts.validate(text, button_text, button_url, image, picked)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    size = broadcasts.audience(db, picked, skip_premium)["total"]
    if not size:
        raise HTTPException(400, "Nobody to send to: the chosen bots have no users yet")
    b = Broadcast(text=body, button_text=button_text.strip() or None, button_url=button_url.strip() or None, photo=image,
                  photo_ids={}, bots=picked, skip_premium=skip_premium, audience=size, created_by=admin.id)
    db.add(b)
    db.commit()
    audit(db, admin, "broadcast.send", f"{b.id} · {size} users")
    limits.redis_client().set(f"broadcast:alive:{b.id}", "1", ex=180)  # the periodic restart leaves a fresh post alone
    queue.task(SEND_TASK, b.id)
    return view(db, b)


@router.post("/test")
async def test(text: str = Form(max_length=20_000), button_text: str = Form(default="", max_length=64),
               button_url: str = Form(default="", max_length=300), bots: str = Form(max_length=200),
               chat_id: int = Form(gt=0), photo: UploadFile | None = None, db=Depends(session)):
    """Send the post once to one Telegram account (yours) to see it exactly as users will."""
    picked, image = chosen_bots(db, bots), await read_photo(photo)
    try:
        body = broadcasts.validate(text, button_text, button_url, image, picked)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    preview = Broadcast(text=body, button_text=button_text.strip() or None, button_url=button_url.strip() or None, photo=image)
    markup = broadcasts.markup(preview)
    try:
        with Telegram(picked[0]) as telegram:
            if image:
                telegram.call("sendPhoto", {"chat_id": chat_id, "caption": body, "parse_mode": "HTML", "reply_markup": markup},
                              files={"photo": ("post.jpg", image, "image/jpeg")})
            else:
                telegram.call("sendMessage", {"chat_id": chat_id, "text": body, "parse_mode": "HTML",
                                              "link_preview_options": {"is_disabled": True}, "reply_markup": markup})
    except TelegramRetry:
        raise HTTPException(429, "Telegram asks to wait a little. Try again in a minute.") from None
    except TelegramError as error:
        hint = " Open the bot and press Start first." if "chat not found" in error.description.lower() else ""
        raise HTTPException(400, f"Telegram: {error.description}.{hint}") from None
    return {"ok": True, "bot": picked[0]}


@router.post("/{id}/delete")
def remove(id: str, db=Depends(session), admin=Depends(admin_required)):
    """Delete the post from every chat it reached (stops sending first if it is still going)."""
    b = require(db, Broadcast, id)
    if b.status in {"deleting", "deleted"}:
        return view(db, b)
    b.status = "deleting"
    db.commit()
    audit(db, admin, "broadcast.delete", b.id)
    limits.redis_client().set(f"broadcast:alive:{b.id}", "1", ex=180)
    queue.task(DELETE_TASK, b.id)
    return view(db, b)
