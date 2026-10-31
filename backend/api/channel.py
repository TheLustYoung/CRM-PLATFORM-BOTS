"""Dashboard «Channel» page: the bots' public channel — connect it, publish (now or scheduled), edit, pin, delete."""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from backend.database import session
from backend.api.deps import admin_required, audit, require
from backend.api.broadcasts import connected_bots
from backend.models import ChannelPost, now
from backend.services import channel

router = APIRouter(prefix="/api/admin/channel", tags=["admin"], dependencies=[Depends(admin_required)])


class ChannelSettings(BaseModel):
    chat: str = Field(max_length=200)
    bots: list[str] = Field(default_factory=list, max_length=50)  # ticked bots
    all: bool = False  # every bot, including bots connected later
    bot: str | None = Field(default=None, max_length=16)  # one bot or "all" (older dashboards)


@router.get("")
def overview(db=Depends(session)):
    posts = db.scalars(select(ChannelPost).where(ChannelPost.status != "deleted").order_by(ChannelPost.publish_at.desc()).limit(100))
    bots = connected_bots(db)
    return {"settings": channel.settings(db), "bots": bots, "channel": channel.info(db, bots),
            "posts": [channel.view(p) for p in posts]}


@router.put("")
def save(data: ChannelSettings, db=Depends(session), admin=Depends(admin_required)):
    bots = connected_bots(db)
    picked = list(data.bots) + ([data.bot] if data.bot and data.bot != channel.ALL else [])
    all_bots = data.all or data.bot == channel.ALL
    unknown = [b for b in picked if b not in bots]
    if unknown:
        raise HTTPException(400, f"Bot not connected: {', '.join(unknown)}")
    try:
        result = channel.save_settings(db, data.chat, picked, all_bots)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    audit(db, admin, "channel.settings", f"{result['chat']} · {'all bots' if all_bots else ', '.join(picked)}")
    return {"settings": result, "channel": channel.info(db, bots)}


def parse_buttons(value: str) -> list[dict]:
    try:
        rows = json.loads(value or "[]")
        assert isinstance(rows, list)
    except (ValueError, AssertionError):
        raise HTTPException(400, "Bad buttons") from None
    try:
        return channel.clean_buttons(rows)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "Bad publishing time") from None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


@router.post("/posts")
async def create(text: str = Form(default="", max_length=20_000), buttons: str = Form(default="[]", max_length=5000),
                 publish_at: str = Form(default="", max_length=40), media: UploadFile | None = None,
                 db=Depends(session), admin=Depends(admin_required)):
    s = channel.settings(db)
    if not s["chat"] or not (s["all"] or s["bots"]):
        raise HTTPException(400, "Connect the channel first")
    bot = channel.posting_bot(db, connected_bots(db))
    if not bot:
        raise HTTPException(400, "No bot can post in this channel: make a bot an administrator with the right to post")
    content = await media.read(channel.MEDIA_LIMIT + 1) if media is not None and media.filename else None
    if content is not None and len(content) > channel.MEDIA_LIMIT:
        raise HTTPException(400, "The file must be up to 50 MB")
    try:
        kind = channel.media_kind(content) if content else None
        body = channel.clean_text(text, bool(content))
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    when = parse_time(publish_at)
    post = ChannelPost(chat=s["chat"], bot_id=bot, text=body, media=content, media_kind=kind,
                       media_name=(media.filename or "")[:128] if content else None, buttons=parse_buttons(buttons),
                       publish_at=when or now(), status="scheduled", created_by=admin.id)
    db.add(post)
    db.commit()
    if not when or when <= now():
        channel.publish(db, post)
    audit(db, admin, "channel.post", f"{post.id} · {post.status}")
    return channel.view(post)


@router.post("/posts/{id}/edit")
async def edit(id: str, text: str = Form(default="", max_length=20_000), buttons: str = Form(default="[]", max_length=5000),
               publish_at: str = Form(default="", max_length=40), db=Depends(session), admin=Depends(admin_required)):
    post = require(db, ChannelPost, id)
    if post.status not in ("scheduled", "published", "failed"):
        raise HTTPException(400, "This post can't be edited now")
    try:
        post.text = channel.clean_text(text, bool(post.media_kind))
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    post.buttons = parse_buttons(buttons)
    if post.status == "published":
        try:
            channel.edit(db, post)
        except ValueError as error:
            db.rollback()
            raise HTTPException(400, str(error)) from None
    elif publish_at:
        post.publish_at, post.status, post.error = parse_time(publish_at), "scheduled", None
    post.edited_at = now()
    db.commit()
    audit(db, admin, "channel.edit", post.id)
    return channel.view(post)


@router.post("/posts/{id}/publish")
def publish_now(id: str, db=Depends(session), admin=Depends(admin_required)):
    """A scheduled post right now, or another try for a failed one."""
    post = require(db, ChannelPost, id)
    if post.status not in ("scheduled", "failed"):
        raise HTTPException(400, "Already published")
    post.publish_at = now()
    channel.publish(db, post)
    audit(db, admin, "channel.publish", f"{post.id} · {post.status}")
    return channel.view(post)


class Pin(BaseModel):
    pin: bool


@router.post("/posts/{id}/pin")
def pin(id: str, data: Pin, db=Depends(session), admin=Depends(admin_required)):
    post = require(db, ChannelPost, id)
    if post.status != "published":
        raise HTTPException(400, "Only a published post can be pinned")
    try:
        channel.pin(db, post, data.pin)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    audit(db, admin, "channel.pin" if data.pin else "channel.unpin", post.id)
    return channel.view(post)


@router.post("/posts/{id}/delete")
def delete(id: str, db=Depends(session), admin=Depends(admin_required)):
    """Removes the post from the channel (or cancels a scheduled one)."""
    post = require(db, ChannelPost, id)
    try:
        channel.remove(db, post)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    audit(db, admin, "channel.delete", post.id)
    return {"ok": True}


@router.get("/posts/{id}/media")
def media(id: str, db=Depends(session)):
    """The post's photo or video for the dashboard preview."""
    from fastapi import Response
    post = require(db, ChannelPost, id)
    if not post.media:
        raise HTTPException(404, "No media")
    kind = "video/mp4" if post.media_kind == "video" else "image/jpeg"
    return Response(post.media, media_type=kind, headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff",
                                                          "Content-Security-Policy": "default-src 'none'; sandbox"})
