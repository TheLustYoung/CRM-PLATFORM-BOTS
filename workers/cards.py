"""Telegram message rendering: media info card and result captions with bot attribution."""
import html
from backend.services.i18n import tr, raw, is_rtl, RLM
from backend.services.platforms import TITLES

CAPTION_LIMIT = 1024


CARD_LIMIT = 1024  # a card with a picture is one message only while its caption fits Telegram's limit


def post_text(description: str | None, room: int) -> str:
    """The post's own text in the card, as a collapsible quote, cut to the room left in the caption."""
    text = (description or "").strip()
    frame = len("<blockquote expandable></blockquote>\n")
    if not text or room - frame < 40:
        return ""
    escaped = html.escape(text)
    if len(escaped) > room - frame:
        cut = text
        while cut and len(html.escape(cut)) + 1 > room - frame:
            cut = cut[:max(len(cut) - max(len(cut) // 10, 1), 0)]
        escaped = html.escape(cut.rstrip()) + "…"
    return f"<blockquote expandable>{escaped}</blockquote>\n"


def signature(username: str | None) -> str:
    return f"\n\n🤖 @{html.escape(username)}" if username else ""


def human_size(size: int | None) -> str | None:
    if not size:
        return None
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000


def duration(seconds) -> str | None:
    if not seconds:
        return None
    seconds = int(seconds)
    h, m, s = seconds // 3600, seconds % 3600 // 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def number(value) -> str | None:
    return f"{int(value):,}" if isinstance(value, (int, float)) else None


def date(value) -> str | None:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if isinstance(value, str) and len(value) == 8 and value.isdigit() else None


def format_line(f: dict) -> str:
    size = human_size(f.get("size"))
    return f"• {html.escape(f['label'])}" + (f" · ≈ {size}" if size else "")


def short_size(size: int | None) -> str | None:
    if not size:
        return None
    if size >= 1e9:
        return f"{size / 1e9:.1f}G"
    if size >= 1e6:
        return f"{size / 1e6:.0f}M" if size >= 1e7 else f"{size / 1e6:.1f}M"
    return f"{max(size / 1e3, 1):.0f}K"


def button_text(f: dict, lang: str) -> str:
    """Compact enough for two buttons per row on a phone; full details are in the card text."""
    kind = f.get("kind")
    if kind == "collection":
        return f"🗂 {raw(lang, 'btn_all_items').format(count=f.get('count'))}"
    ext = (f.get("ext") or "").lower()
    if kind == "video":
        main = f"🎞 {f['height']}p {ext}" if f.get("height") else f"🎞 {ext}"
    elif kind == "audio":
        main = f"🎧 {ext} {f['abr']}k" if f.get("abr") else f"🎧 {ext}"
    else:
        main = f"🖼 {ext}"
    size = short_size(f.get("size"))
    return main + (f" · {size}" if size else "")


def card(info: dict, job_id: str, lang: str, username: str | None, locked: set[int] | None = None) -> tuple[str, list[list[dict]]]:
    """Info card text (formats listed in the text itself,) and inline keyboard.

    `locked`: indexes of Premium-only formats (HD/4K, large files) for a free user; they get a ⭐ mark.
    """
    locked = locked or set()
    na = f"<i>{html.escape(raw(lang, 'na'))}</i>"
    rows = []

    def add(icon: str, key: str, value: str | None, required: bool = False):
        if value is not None:
            rows.append(f"{icon} {html.escape(raw(lang, key))}: {html.escape(value)}")
        elif required:
            rows.append(f"{icon} {html.escape(raw(lang, key))}: {na}")  # unavailable, never a fake 0

    add("🌐", "card_platform", TITLES.get(info.get("platform"), "Web"), True)
    add("⚖️", "card_license", info.get("license"), info.get("platform") != "direct")  # the licence shown on the source page
    add("👤", "card_channel", info.get("channel"))
    add("⏱", "card_duration", duration(info.get("duration")))
    add("👁", "card_views", number(info.get("views")))
    add("👍", "card_likes", number(info.get("likes")))
    add("💬", "card_comments", number(info.get("comments")))
    add("📅", "card_published", date(info.get("date")))
    if (info.get("count") or 1) > 1:
        add("🗂", "card_items", str(info["count"]), True)

    formats = info.get("formats", [])
    sections = []
    for kind, key, icon in (("video", "card_video_formats", "🎞"), ("audio", "card_audio_formats", "🎧")):
        lines = [format_line(f) for f in formats if f.get("kind") == kind]
        if lines:
            sections.append(f"{icon} <b>{html.escape(raw(lang, key))}</b>\n" + "\n".join(lines))
    other = [format_line(f) for f in formats if f.get("kind") == "image"]
    if other:
        sections.append(f"🖼 <b>{html.escape(raw(lang, 'card_other_formats'))}</b>\n" + "\n".join(other))

    head = f"🎬 <b>{html.escape(info.get('title') or 'Media')}</b>\n"
    body = "\n".join(rows)
    if sections:
        body += "\n\n" + "\n\n".join(sections)
    body += f"\n\n{html.escape(raw(lang, 'card_choose'))}"
    if locked:
        body += f"\n{html.escape(raw(lang, 'card_premium_note'))}"
    body += signature(username)
    text = head + post_text(info.get("description"), CARD_LIMIT - len(head) - len(body) - (1 if is_rtl(lang) else 0)) + body
    if is_rtl(lang):
        text = RLM + text

    buttons, pair = [], []
    for index, f in enumerate(formats):
        label = ("⭐ " if index in locked else "") + button_text(f, lang)
        pair.append({"text": label[:64], "callback_data": f"dl:{job_id}:{index}"})
        if len(pair) == 2:
            buttons.append(pair)
            pair = []
    if pair:
        buttons.append(pair)
    buttons.append([{"text": raw(lang, "btn_refresh"), "callback_data": f"rf:{job_id}"},
                    {"text": raw(lang, "btn_info"), "callback_data": f"in:{job_id}"}])
    return text, buttons


def signed(lang: str, key: str, username: str | None, **kwargs) -> str:
    return tr(lang, key, **kwargs) + signature(username)
