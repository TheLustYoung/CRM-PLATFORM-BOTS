"""Link -> info card -> format button flow, shared by the Video and Media bots."""
import contextlib
import html
import re
from aiogram import F, Router
from aiogram.filters import Command, or_f
from aiogram.types import CallbackQuery, Message, ReactionTypeEmoji
from backend.services.i18n import tr, raw
from backend.services.platforms import TITLES, platform_for
from bots.common.runner import Context, button_texts, strip

URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def find_url(text: str | None) -> str | None:
    match = URL.search(text or "")
    return match.group(0).rstrip(").,!?") if match else None


def is_library(url: str) -> bool:
    """A link to one of the free-licence libraries (the Video bot accepts only these)."""
    return platform_for(url) in ("wikimedia", "archive")


async def answer_job(event: CallbackQuery, lang: str, job: dict):
    """Clear feedback for repeated presses: the same job is reused, never processed twice."""
    if job["created"]:
        await event.answer(strip(raw(lang, "queued")))
    elif job["status"] in {"queued", "processing"}:
        await event.answer(strip(raw(lang, "already_processing")))
    elif job["status"] == "completed":
        await event.answer(strip(raw(lang, "already_done")))
    else:
        await event.answer(strip(raw(lang, "failed")), show_alert=True)


def history_text(lang: str, items: list[dict]) -> str:
    if not items:
        return tr(lang, "history_empty")
    lines = [tr(lang, "history_title")]
    for item in items:
        icon = raw(lang, f"st_{item['status']}") if item["status"] in {"completed", "failed", "processing", "queued"} else "•"
        details = " · ".join(filter(None, [TITLES.get(item.get("platform"), ""), item.get("label"), item["created_at"][:10]]))
        link = f' · <a href="{html.escape(item["url"], quote=True)}">{html.escape(raw(lang, "history_open"))}</a>' if item.get("url") else ""
        lines.append(f"{icon} <b>{html.escape((item.get('title') or '')[:80])}</b>\n<i>{html.escape(details)}</i>{link}")
    return "\n\n".join(lines)


def setup_media(router: Router, ctx: Context, libraries_only: bool):
    @router.message(or_f(Command("history"), F.text.in_(button_texts("menu_history"))))
    async def history(message: Message):
        async def action(m: Message, profile: dict):
            items = await ctx.api.post("history", ctx.identity(m.from_user))
            await m.answer(history_text(profile["language"], items)[:4096])
        await ctx.guard(message, action)

    @router.message(F.text)
    async def link(message: Message):
        async def action(m: Message, profile: dict):
            url = find_url(m.text)
            if not url or (libraries_only and not is_library(url)):
                await m.answer(tr(profile["language"], "send_video_link" if libraries_only else "send_link"))
                return
            # The worker posts the status message and the card; nothing else to say here.
            await ctx.api.post("metadata", {**ctx.identity(m.from_user), "url": url, "request_key": f"msg:{m.chat.id}:{m.message_id}"})
            with contextlib.suppress(Exception):  # 👀 = the link was taken; the worker sets 🫡 once the media is delivered
                await ctx.bot.set_message_reaction(m.chat.id, m.message_id, [ReactionTypeEmoji(emoji="👀")])
        await ctx.guard(message, action, gated=True)

    @router.callback_query(F.data.startswith("dl:"))
    async def download(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            _, metadata_id, index = event.data.split(":")
            job = await ctx.api.post("download", {**ctx.identity(event.from_user), "metadata_id": metadata_id, "index": int(index)})
            await answer_job(event, profile["language"], job)
        await ctx.guard(event, action, gated=True)

    @router.callback_query(F.data.startswith("rf:"))
    async def refresh(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            job = await ctx.api.post(f"jobs/{event.data[3:]}/refresh", ctx.identity(event.from_user))
            await answer_job(event, profile["language"], job)
        await ctx.guard(event, action)

    @router.callback_query(F.data.startswith("in:"))
    async def info(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            lang = profile["language"]
            data = await ctx.api.post(f"jobs/{event.data[3:]}/info", ctx.identity(event.from_user))
            await event.answer()
            me = await ctx.bot.me()
            lines = [f"<b>{html.escape(data.get('title') or '')}</b>"]
            if data.get("channel"):
                lines.append(f"{html.escape(raw(lang, 'card_channel'))}: {html.escape(data['channel'])}")
            if data.get("license"):
                lines.append(f"⚖️ {html.escape(raw(lang, 'card_license'))}: {html.escape(data['license'])}")
            url = data.get("webpage_url") or data["url"]
            lines.append(f'🔗 <a href="{html.escape(url)}">{html.escape(raw(lang, "info_link"))}</a>')
            # One clean message with the whole text (no attached file); a very long text continues in the next ones.
            description = data.get("description") or raw(lang, "na")
            head = "\n".join(lines) + f"\n\n<b>{html.escape(raw(lang, 'info_description'))}</b>\n"
            sign = f"\n\n🤖 @{me.username}"
            pieces = [description[i:i + 3500] for i in range(0, len(description), 3500)] or [""]
            for n, piece in enumerate(pieces):
                text = (head if n == 0 else "") + html.escape(piece) + (sign if n == len(pieces) - 1 else "")
                await m.answer(text)
        await ctx.guard(event, action)
