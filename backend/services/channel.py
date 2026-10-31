"""The bots' public channel, run from the dashboard: which channel and which bot posts there, publishing
(now or at a set time), editing, pinning and deleting posts, and what the channel looks like right now.

The posting bot must be an administrator of the channel with the right to post (and to edit, delete and pin,
for those buttons). Telegram's Bot API gives the subscriber count but not post views, so views are not shown.
"""
import logging
from sqlalchemy import select
from backend.models import ChannelPost, SystemSetting, aware, now
from backend.services import broadcasts
from backend.services.monetization import channel_ref
from backend.services.security import DomainError

log = logging.getLogger(__name__)
SETTINGS_KEY = "public_channel"
MEDIA_LIMIT = 50_000_000  # Telegram's limit for files a bot uploads
MAX_BUTTONS = 6
VIDEO_SIGNATURES = (b"ftyp",)  # MP4/MOV: "ftyp" box at offset 4
PHOTO_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")


def settings(db) -> dict:
    """{chat, bots, all}: the channel, the bots chosen to work with it, or every bot (new bots join automatically)."""
    row = db.get(SystemSetting, SETTINGS_KEY)
    value = dict(row.value) if row else {}
    if "bots" not in value:  # saved before several bots could be chosen: {"bot": "<id>" | "all"}
        old = value.get("bot") or ""
        value["all"], value["bots"] = old == "all", [] if old in ("", "all") else [old]
    return {"chat": value.get("chat", ""), "bots": list(value.get("bots") or []), "all": bool(value.get("all"))}


def save_settings(db, chat: str, bots: list[str], all_bots: bool) -> dict:
    chat = channel_ref(chat)  # @name, t.me/name or -100… id
    if not chat:
        raise ValueError("Enter the channel as @username, a t.me link or a -100… id")
    if not all_bots and not bots:
        raise ValueError("Choose at least one bot, or All bots")
    db.merge(SystemSetting(key=SETTINGS_KEY, value={"chat": chat, "bots": [] if all_bots else list(dict.fromkeys(bots)), "all": all_bots}))
    db.commit()
    return settings(db)


def chosen_bots(s: dict, connected: list[str]) -> list[str]:
    """The bots that work with the channel now: every connected bot with «All bots», otherwise the ticked ones."""
    return list(connected) if s["all"] else [b for b in s["bots"] if b in connected]


def media_kind(content: bytes) -> str:
    if content.startswith(PHOTO_SIGNATURES):
        return "photo"
    if content[4:8] in VIDEO_SIGNATURES:
        return "video"
    raise ValueError("The file must be a photo (JPEG, PNG, WebP) or an MP4 video")


def clean_buttons(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows or []:
        text, url = (row.get("text") or "").strip(), (row.get("url") or "").strip()
        if not text and not url:
            continue
        if not text or not url:
            raise ValueError("Each button needs both a text and a link")
        if not broadcasts.SAFE_LINK.match(url):
            raise ValueError("Button links must start with https://")
        result.append({"text": text[:64], "url": url})
    if len(result) > MAX_BUTTONS:
        raise ValueError(f"At most {MAX_BUTTONS} buttons")
    return result


def clean_text(text: str, with_media: bool) -> str:
    body, visible = broadcasts.clean(text)
    if not body and not with_media:
        raise ValueError("Write the text of the post or add a photo or video")
    limit = broadcasts.CAPTION_LIMIT if with_media else broadcasts.TEXT_LIMIT
    if visible > limit:
        raise ValueError(f"The text is too long: {visible} of {limit} characters" + (" (posts with a photo or video)" if with_media else ""))
    return body


def markup(post: ChannelPost) -> dict:
    # An empty keyboard on edit removes buttons that were taken away.
    return {"inline_keyboard": [[{"text": b["text"], "url": b["url"]}] for b in post.buttons or []]}


def telegram(bot_id: str):
    from workers.telegram import Telegram
    return Telegram(bot_id)


def publish(db, post: ChannelPost) -> ChannelPost:
    """Send the post to the channel now; the result (message id or Telegram's reason) is stored on the post."""
    from workers.telegram import TelegramError, TelegramRetry
    post.status = "sending"
    db.commit()
    data = {"chat_id": post.chat, "parse_mode": "HTML", "reply_markup": markup(post) if post.buttons else None}
    try:
        with telegram(post.bot_id) as tg:
            if post.media_kind == "photo":
                result = tg.call("sendPhoto", {**data, "caption": post.text or None}, files={"photo": (post.media_name or "photo.jpg", post.media, "application/octet-stream")})
            elif post.media_kind == "video":
                result = tg.call("sendVideo", {**data, "caption": post.text or None, "supports_streaming": "true"},
                                 files={"video": (post.media_name or "video.mp4", post.media, "application/octet-stream")})
            else:
                result = tg.call("sendMessage", {**data, "text": post.text})
        post.status, post.message_id, post.published_at, post.error = "published", result["message_id"], now(), None
    except TelegramRetry:
        post.status, post.error = "scheduled", "Telegram asked to wait; it will be sent again in a minute"
    except (TelegramError, DomainError) as error:
        post.status, post.error = "failed", getattr(error, "description", str(error))[:300]
    except Exception as error:  # network trouble: try again with the next run
        post.status, post.error = "scheduled", f"{type(error).__name__}; it will be sent again in a minute"
    db.commit()
    return post


def edit(db, post: ChannelPost) -> None:
    """Apply the dashboard's new text and buttons to the post already in the channel."""
    from workers.telegram import TelegramError
    data = {"chat_id": post.chat, "message_id": post.message_id, "parse_mode": "HTML", "reply_markup": markup(post)}
    try:
        with telegram(post.bot_id) as tg:
            if post.media_kind:
                tg.call("editMessageCaption", {**data, "caption": post.text})
            else:
                tg.call("editMessageText", {**data, "text": post.text})
    except TelegramError as error:
        if "not modified" not in error.description.lower():
            raise ValueError(f"Telegram: {error.description}") from None


def remove(db, post: ChannelPost) -> None:
    from workers.telegram import TelegramError
    if post.status == "published" and post.message_id:
        try:
            with telegram(post.bot_id) as tg:
                tg.call("deleteMessage", {"chat_id": post.chat, "message_id": post.message_id})
        except TelegramError as error:
            if "not found" not in error.description.lower():  # already gone from the channel: just mark it
                raise ValueError(f"Telegram: {error.description}") from None
    post.status, post.pinned = "deleted", False
    db.commit()


def pin(db, post: ChannelPost, on: bool) -> None:
    from workers.telegram import TelegramError
    try:
        with telegram(post.bot_id) as tg:
            if on:
                tg.call("pinChatMessage", {"chat_id": post.chat, "message_id": post.message_id, "disable_notification": True})
            else:
                tg.call("unpinChatMessage", {"chat_id": post.chat, "message_id": post.message_id})
    except TelegramError as error:
        raise ValueError(f"Telegram: {error.description}") from None
    post.pinned = on
    db.commit()


RIGHTS = ("can_post_messages", "can_edit_messages", "can_delete_messages", "can_pin_messages")


ALL = "all"  # the channel belongs to every bot: each one is checked, the first allowed to post publishes


def bot_rights(chat: str, bot: str) -> dict:
    """Is this bot an administrator of the channel, and with which rights."""
    from workers.telegram import TelegramError
    from backend.config import settings as config
    token = config().bot_token(bot)
    if not token:
        return {"bot": bot, "admin": False, "rights": {r: False for r in RIGHTS}, "error": "no token"}
    try:
        with telegram(bot) as tg:
            me = tg.call("getChatMember", {"chat_id": chat, "user_id": int(token.split(":")[0])})
    except TelegramError as error:
        return {"bot": bot, "admin": False, "rights": {r: False for r in RIGHTS}, "error": error.description}
    except Exception as error:
        return {"bot": bot, "admin": False, "rights": {r: False for r in RIGHTS}, "error": type(error).__name__}
    creator = me.get("status") == "creator"
    return {"bot": bot, "admin": creator or me.get("status") == "administrator",
            "rights": {r: creator or bool(me.get(r)) for r in RIGHTS}}


def posting_bot(db, connected: list[str]) -> str | None:
    """The bot that publishes: the first chosen bot that may post in the channel."""
    s = settings(db)
    return next((b["bot"] for b in (bot_rights(s["chat"], bot) for bot in chosen_bots(s, connected))
                 if b["rights"].get("can_post_messages")), None)


def info(db, bots: list[str] | None = None) -> dict:
    """The channel as Telegram sees it: title, subscribers, and for every connected bot whether it is an administrator
    there (the lamps) and whether it is chosen to work with the channel."""
    from workers.telegram import TelegramError
    s = settings(db)
    connected = list(bots or [])
    if not s["chat"]:
        return {"connected": False, "bots": [{"bot": b, "chosen": False, "admin": None, "rights": {}} for b in connected]}
    chosen = chosen_bots(s, connected)
    statuses = [{**bot_rights(s["chat"], bot), "chosen": bot in chosen} for bot in connected]
    reader = next((b["bot"] for b in statuses if "error" not in b), None)  # any bot that can see the channel
    if not reader:
        return {"connected": False, "error": (statuses[0].get("error") if statuses else "No connected bots"), "bots": statuses}
    try:
        with telegram(reader) as tg:
            chat = tg.call("getChat", {"chat_id": s["chat"]})
            members = tg.call("getChatMemberCount", {"chat_id": s["chat"]})
    except TelegramError as error:
        return {"connected": False, "error": error.description, "bots": statuses}
    except Exception as error:
        return {"connected": False, "error": type(error).__name__, "bots": statuses}
    poster = next((b for b in statuses if b["chosen"] and b["rights"].get("can_post_messages")), None)
    return {"connected": True, "title": chat.get("title"), "username": chat.get("username"), "type": chat.get("type"),
            "members": members, "admin": bool(poster), "rights": (poster or {}).get("rights", {}),
            "posting_bot": poster["bot"] if poster else None, "all_bots": s["all"], "bots": statuses,
            "link": f"https://t.me/{chat['username']}" if chat.get("username") else chat.get("invite_link")}


def publish_due(db) -> int:
    """Scheduled posts whose time has come (called every minute by the worker)."""
    due = list(db.scalars(select(ChannelPost).where(ChannelPost.status == "scheduled", ChannelPost.publish_at <= now())
                          .order_by(ChannelPost.publish_at).limit(20)))
    for post in due:
        publish(db, post)
    return len(due)


def view(post: ChannelPost) -> dict:
    return {"id": post.id, "chat": post.chat, "bot": post.bot_id, "text": post.text, "media_kind": post.media_kind,
            "media_name": post.media_name, "buttons": post.buttons or [], "status": post.status,
            "publish_at": aware(post.publish_at), "published_at": post.published_at, "message_id": post.message_id,
            "pinned": post.pinned, "error": post.error, "created_at": post.created_at, "edited_at": post.edited_at,
            "link": (f"https://t.me/{post.chat[1:]}/{post.message_id}" if post.chat.startswith("@") and post.message_id else None)}
