"""Ad posts from the dashboard to the bots' users: Telegram-formatted text, audience, delivery batches.

The dashboard editor produces Telegram HTML (bold, italic, underline, strikethrough, spoiler, monospace,
code blocks, links, quotes). Everything is re-parsed here and rebuilt from an allow-list, so only markup
Telegram accepts reaches the bots and nothing else (scripts, styles, unknown tags) can slip through.
"""
import html
import re
from html.parser import HTMLParser
from sqlalchemy import Integer, cast, func, or_, select
from backend.models import BotUser, Broadcast, BroadcastMessage, User, now

TEXT_LIMIT, CAPTION_LIMIT = 4096, 1024  # Telegram counts visible characters, not markup
PHOTO_LIMIT = 10_000_000
DELETE_WINDOW_HOURS = 48  # Telegram lets a bot delete its own messages only within 48 hours
TAGS = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "ins": "u", "s": "s", "strike": "s", "del": "s",
        "tg-spoiler": "tg-spoiler", "code": "code", "pre": "pre", "a": "a", "blockquote": "blockquote"}
SAFE_LINK = re.compile(r"^(https?://|tg://)[^\s\"'<>]{1,500}$", re.IGNORECASE)


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.visible = [], [], 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "br":
            self.handle_data("\n")
            return
        if tag == "span" and "tg-spoiler" in (attrs.get("class") or "").split():
            tag = "tg-spoiler"
        name = TAGS.get(tag)
        if not name:
            self.stack.append(None)  # unknown tag: drop it, keep its text
            return
        if name == "a":
            href = (attrs.get("href") or "").strip()
            if not SAFE_LINK.match(href):
                self.stack.append(None)
                return
            self.out.append(f'<a href="{html.escape(href, quote=True)}">')
        elif name == "blockquote" and "expandable" in attrs:
            self.out.append("<blockquote expandable>")
        else:
            self.out.append(f"<{name}>")
        self.stack.append(name)

    def handle_endtag(self, tag):
        if tag == "br" or not self.stack:
            return
        name = self.stack.pop()
        if name:
            self.out.append(f"</{name}>")

    def handle_data(self, data):
        self.visible += len(data.encode("utf-16-le")) // 2  # Telegram measures UTF-16 code units
        self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            name = self.stack.pop()
            if name:
                self.out.append(f"</{name}>")
        return "".join(self.out)


def clean(text: str) -> tuple[str, int]:
    """(Telegram-safe HTML, visible length) for the editor's output."""
    parser = _Cleaner()
    parser.feed((text or "").replace("\r\n", "\n"))
    parser.close()
    result = re.sub(r"\n{3,}", "\n\n", parser.result()).strip()
    return result, parser.visible


def validate(text: str, button_text: str, button_url: str, photo: bytes | None, bots: list[str]) -> str:
    body, visible = clean(text)
    if not body:
        raise ValueError("Write the text of the post")
    limit = CAPTION_LIMIT if photo else TEXT_LIMIT
    if visible > limit:
        raise ValueError(f"The text is too long: {visible} of {limit} characters" + (" (posts with a photo)" if photo else ""))
    if bool(button_text.strip()) != bool(button_url.strip()):
        raise ValueError("A button needs both a text and a link")
    if button_url.strip() and not SAFE_LINK.match(button_url.strip()):
        raise ValueError("The button link must start with https://")
    if photo is not None and len(photo) > PHOTO_LIMIT:
        raise ValueError("The photo must be up to 10 MB")
    if not bots:
        raise ValueError("Choose at least one bot")
    return body


def buttons(b: Broadcast) -> list[list[dict]] | None:
    return [[{"text": b.button_text, "url": b.button_url}]] if b.button_text and b.button_url else None


def markup(b: Broadcast) -> dict | None:
    """Reply_markup for the Bot API: the optional link button under the post."""
    rows = buttons(b)
    return {"inline_keyboard": rows} if rows else None


def _audience(bots: list[str], skip_premium: bool):
    query = (select(BotUser.user_id).join(User, User.id == BotUser.user_id)
             .where(BotUser.bot_id.in_(bots), User.banned.is_(False)))
    if skip_premium:  # Premium promises no ads
        query = query.where(or_(User.premium_until.is_(None), User.premium_until <= now()))
    return query


def audience(db, bots: list[str], skip_premium: bool) -> dict:
    total = db.scalar(select(func.count()).select_from(_audience(bots, skip_premium).distinct().subquery())) if bots else 0
    per_bot = {bot: db.scalar(select(func.count()).select_from(_audience([bot], skip_premium).subquery())) for bot in bots}
    return {"total": total, "per_bot": per_bot}


def next_batch(db, b: Broadcast, size: int) -> list[tuple[int, str]]:
    """The next people who have not received the post yet, each with the first selected bot they use."""
    done = select(BroadcastMessage.user_id).where(BroadcastMessage.broadcast_id == b.id)
    users = list(db.scalars(_audience(b.bots, b.skip_premium).where(BotUser.user_id.not_in(done))
                            .distinct().order_by(BotUser.user_id).limit(size)))
    if not users:
        return []
    joined: dict[int, set[str]] = {}
    for user_id, bot_id in db.execute(select(BotUser.user_id, BotUser.bot_id).where(BotUser.user_id.in_(users), BotUser.bot_id.in_(b.bots))):
        joined.setdefault(user_id, set()).add(bot_id)
    return [(user_id, next(bot for bot in b.bots if bot in joined[user_id])) for user_id in users]


def counts(db, b: Broadcast) -> dict:
    rows = db.execute(select(func.count(BroadcastMessage.message_id), func.count(),
                             func.coalesce(func.sum(cast(BroadcastMessage.deleted, Integer)), 0),
                             func.coalesce(func.sum(cast(BroadcastMessage.delete_failed, Integer)), 0))
                      .where(BroadcastMessage.broadcast_id == b.id)).one()
    delivered, processed, deleted, not_deleted = rows
    return {"delivered": delivered, "failed": processed - delivered, "processed": processed,
            "deleted": deleted, "not_deleted": not_deleted}
