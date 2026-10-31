"""File Sharing Bot: Telegram upload -> private storage -> public browser link on our domain."""
import html
from aiogram import F, Router
from aiogram.filters import Command, or_f
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from backend.services.i18n import tr, raw
from bots.common.runner import Context, button_texts, strip


def attachment(m: Message):
    """(telegram file object, file name) for every supported message type."""
    if m.document:
        return m.document, m.document.file_name or "file.bin"
    if m.photo:
        return m.photo[-1], f"photo_{m.message_id}.jpg"
    if m.video:
        return m.video, m.video.file_name or f"video_{m.message_id}.mp4"
    if m.audio:
        return m.audio, m.audio.file_name or f"audio_{m.message_id}.mp3"
    if m.voice:
        return m.voice, f"voice_{m.message_id}.ogg"
    if m.video_note:
        return m.video_note, f"video_note_{m.message_id}.mp4"
    if m.animation:
        return m.animation, m.animation.file_name or f"animation_{m.message_id}.mp4"
    return None, None


def setup(router: Router, ctx: Context):
    @router.message(or_f(Command("myfiles"), F.text.in_(button_texts("menu_files"))))
    async def my_files(message: Message):
        async def action(m: Message, profile: dict):
            lang = profile["language"]
            items = await ctx.api.post("files", ctx.identity(m.from_user))
            if not items:
                await m.answer(tr(lang, "myfiles_empty"))
                return
            lines = [tr(lang, "myfiles_title")]
            buttons = []
            for i, f in enumerate(items, 1):
                lines.append(f"{i}. <b>{html.escape(f['name'])}</b> — {f['expires_at'][:10]}\n{html.escape(f['url'] or '—')}")
                buttons.append([InlineKeyboardButton(text=f"{i}. {raw(lang, 'btn_revoke')}", callback_data=f"rv:{f['id']}"),
                                InlineKeyboardButton(text=f"{i}. {raw(lang, 'btn_delete')}", callback_data=f"rm:{f['id']}")])
            await m.answer("\n\n".join(lines)[:4096], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons[:20]))
        await ctx.guard(message, action)

    @router.message(F.document | F.photo | F.video | F.audio | F.voice | F.video_note | F.animation)
    async def upload(message: Message):
        async def action(m: Message, profile: dict):
            file, name = attachment(m)
            await ctx.api.post("upload", {**ctx.identity(m.from_user), "request_key": f"msg:{m.chat.id}:{m.message_id}",
                                          "file_id": file.file_id, "name": name, "size": file.file_size or 1})
        await ctx.guard(message, action, gated=True)

    @router.message()
    async def other(message: Message):
        async def action(m: Message, profile: dict):
            await m.answer(tr(profile["language"], "send_file"))
        await ctx.guard(message, action)

    @router.callback_query(F.data.startswith("rv:") | F.data.startswith("rm:"))
    async def manage(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            revoke = event.data.startswith("rv:")
            await ctx.api.post(f"files/{event.data[3:]}/{'revoke' if revoke else 'delete'}", ctx.identity(event.from_user))
            await event.answer(strip(raw(profile["language"], "revoked" if revoke else "deleted")), show_alert=True)
        await ctx.guard(event, action)
