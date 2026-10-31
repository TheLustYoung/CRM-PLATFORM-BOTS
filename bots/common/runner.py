"""Shared bot runtime: registration, language selection, error handling, heartbeat, polling."""
import asyncio
import contextlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable
import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart, or_f
from aiogram.types import (BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)
from backend.config import settings
from backend.services.i18n import catalogs, tr, raw, set_edits
from bots.common.client import ApiClient, ApiError

log = logging.getLogger("bots")
RETIRED_LANGUAGES: list[str] = []  # languages that were supported earlier and whose Telegram texts must be cleared


PREMIUM_ERRORS = {"premium_limit", "premium_quality", "premium_size", "premium_feature"}  # answered with a "Get Premium" button
MEMBER_STATUSES = {"creator", "administrator", "member"}
MEMBER_CACHE_SECONDS = 600


@dataclass
class Context:
    kind: str
    bot: Bot
    api: ApiClient
    profiles: dict = field(default_factory=dict)
    members: dict = field(default_factory=dict)  # user id -> time until which the channel check is trusted

    @staticmethod
    def identity(user) -> dict:
        return {"user_id": user.id, "username": user.username}

    async def profile(self, user, referrer: int | None = None) -> dict:
        data = await self.api.post("register", {**self.identity(user), "first_name": user.first_name,
                                                "language_code": user.language_code, "referrer": referrer})
        self.profiles[user.id] = data
        return data

    def lang(self, user) -> str:
        return self.profiles.get(user.id, {}).get("language") or "en"

    async def missing_channels(self, user_id: int, money: dict | None, fresh: bool = False) -> list[dict]:
        """Required channels the user has not joined yet (the owner may require several)."""
        money = money or {}
        channels = money.get("channels") or ([money["channel"]] if money.get("channel") else [])
        return [c for c in channels if not await self.subscribed(user_id, c["chat"], fresh)]

    async def subscribed(self, user_id: int, chat: str, fresh: bool = False) -> bool:
        """Is the user in the required channel? Positive answers are cached for a few minutes."""
        if not fresh and self.members.get((user_id, chat), 0) > time.monotonic():
            return True
        try:
            member = await self.bot.get_chat_member(chat, user_id)
        except Exception:
            # The bot is not an admin of the channel or the channel is wrong: a setup mistake must not lock users out.
            log.warning('{"event":"channel_check_failed","bot":"%s"}', self.kind)
            return True
        ok = member.status in MEMBER_STATUSES or bool(getattr(member, "is_member", False))
        if ok:
            self.members[(user_id, chat)] = time.monotonic() + MEMBER_CACHE_SECONDS
        return ok

    async def guard(self, event: Message | CallbackQuery, action: Callable[[Message, dict], Awaitable[None]],
                    gated: bool = False, referrer: int | None = None):
        """Private chats only; backend error codes become messages in the user's language.

        `gated` actions (new links and files) first require the channel subscription when the owner turned it on.
        """
        message = event.message if isinstance(event, CallbackQuery) else event
        if message is None:
            return
        if message.chat.type != "private":
            await message.answer(tr("en", "private"))
            return
        lang = self.lang(event.from_user)
        try:
            profile = await self.profile(event.from_user, referrer)
            lang = profile["language"]
            missing = await self.missing_channels(event.from_user.id, profile.get("money")) if gated else []
            if missing:
                if isinstance(event, CallbackQuery):
                    await event.answer()
                await message.answer(tr(lang, "channel_required"), reply_markup=channel_keyboard(lang, missing))
                return
            await action(message, profile)
        except ApiError as error:
            code = str(error)
            money = self.profiles.get(event.from_user.id, {}).get("money") or {}
            limit = {"premium_limit": money.get("daily_limit"), "premium_size": money.get("free_max_mb")}.get(code)
            text = tr(lang, code, limit=limit or self.profiles.get(event.from_user.id, {}).get("upload_limit_mb", 19))
            if code in PREMIUM_ERRORS:
                if isinstance(event, CallbackQuery):
                    await event.answer()
                await message.answer(text, reply_markup=premium_button(lang))
            elif isinstance(event, CallbackQuery):
                await event.answer(strip(text), show_alert=True)
            else:
                await message.answer(text)
        except httpx.HTTPError:
            log.warning('{"event":"backend_unavailable","bot":"%s"}', self.kind)
            await message.answer(tr(lang, "temporary"))
        except Exception:
            # Never leave the user without an answer; the traceback goes to the container log.
            log.exception('{"event":"handler_error","bot":"%s"}', self.kind)
            with contextlib.suppress(Exception):
                await message.answer(tr(lang, "failed"))


def referrer_id(start_args: str | None) -> int | None:
    """User id from an invite link: t.me/<bot>?start=ref_<id>."""
    match = re.fullmatch(r"ref_(\d{1,19})", (start_args or "").strip())
    return int(match.group(1)) if match else None


def strip(text: str) -> str:
    """Plain text for callback toasts (no HTML), max 200 characters."""
    for tag in ("<b>", "</b>", "<i>", "</i>"):
        text = text.replace(tag, "")
    return text[:200]


def premium_button(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=raw(lang, "btn_premium"), callback_data="pm")]])


def channel_keyboard(lang: str, channels: list[dict] | str) -> InlineKeyboardMarkup:
    """A Join button per channel still to join (numbered when there are several), then "I've joined"."""
    channels = [{"url": channels}] if isinstance(channels, str) else channels
    label = raw(lang, "btn_join_channel")
    rows = [[InlineKeyboardButton(text=f"{label} {i}" if len(channels) > 1 else label, url=c["url"])]
            for i, c in enumerate(channels, 1)]
    return InlineKeyboardMarkup(inline_keyboard=[*rows, [InlineKeyboardButton(text=raw(lang, "btn_joined"), callback_data="jn")]])


def language_keyboard(languages: dict) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=name, callback_data=f"lang:{code}") for code, name in languages.items()]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def button_texts(key: str) -> set[str]:
    """A menu button's label in every language, so taps work whatever language the keyboard was sent in."""
    return {raw(code, key) for code in catalogs()}


def menu_keyboard(kind: str, lang: str, money: dict | None = None) -> ReplyKeyboardMarkup:
    """Persistent menu under the input field: the main action, Premium (when on sale), help and language."""
    main = [KeyboardButton(text=raw(lang, "menu_files" if kind == "files" else "menu_history"))]
    if money and (money.get("plans") or money.get("referrals") or money.get("premium")):
        main.append(KeyboardButton(text=raw(lang, "menu_premium")))
    return ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, keyboard=[
        main,
        [KeyboardButton(text=raw(lang, "menu_help")), KeyboardButton(text=raw(lang, "menu_language"))],
    ])


def common_router(ctx: Context) -> Router:
    router = Router(name="common")

    async def welcome(message: Message, profile: dict):
        lang = profile["language"]
        text = profile.get("welcome") or tr(lang, f"welcome_{ctx.kind}", limit=profile.get("upload_limit_mb", 19))
        await message.answer(text, reply_markup=menu_keyboard(ctx.kind, lang, profile.get("money")))

    async def help_text(message: Message, profile: dict):
        lang = profile["language"]
        await message.answer(tr(lang, f"help_{ctx.kind}", limit=profile.get("upload_limit_mb", 19)),
                             reply_markup=menu_keyboard(ctx.kind, lang, profile.get("money")))

    @router.message(CommandStart())
    async def start(message: Message, command: CommandObject):
        async def action(m: Message, profile: dict):
            await welcome(m, profile)
            if profile.get("created"):
                # First visit: the Telegram language is pre-selected, the user can confirm or change it.
                await m.answer(tr(profile["language"], "choose_language"), reply_markup=language_keyboard(profile["languages"]))
        await ctx.guard(message, action, referrer=referrer_id(command.args))

    # or_f, not "|": `Command(...) | F.text...` raises TypeError on every message, so the bot never answered.
    @router.message(or_f(Command("help"), F.text.in_(button_texts("menu_help"))))
    async def help_(message: Message):
        await ctx.guard(message, help_text)

    @router.message(or_f(Command("language"), F.text.in_(button_texts("menu_language"))))
    async def choose(message: Message):
        async def action(m: Message, profile: dict):
            await m.answer(tr(profile["language"], "choose_language"), reply_markup=language_keyboard(profile["languages"]))
        await ctx.guard(message, action)

    @router.callback_query(F.data.startswith("lang:"))
    async def set_language(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            code = event.data.split(":", 1)[1]
            await ctx.api.post("language", {**ctx.identity(event.from_user), "language": code})
            ctx.profiles[event.from_user.id]["language"] = code
            await event.answer()
            await m.edit_text(tr(code, "language_saved", name=profile["languages"].get(code, code)))
            await welcome(m, {**profile, "language": code})
        await ctx.guard(event, action)

    @router.callback_query(F.data.startswith("cx:"))
    async def cancel(event: CallbackQuery):
        """Cancel button on a download/upload status message; only the owner's own job can be stopped."""
        async def action(m: Message, profile: dict):
            job = await ctx.api.post(f"jobs/{event.data[3:]}/cancel", ctx.identity(event.from_user))
            done = job["status"] == "completed"
            await event.answer(strip(raw(profile["language"], "already_done" if done else "cancelling")))
        await ctx.guard(event, action)

    return router


async def heartbeat(ctx: Context, dp: Dispatcher | None = None, token: str = ""):
    from backend.services.bot_tokens import fingerprint
    while True:
        try:
            me = await ctx.bot.get_me()
            beat = await ctx.api.post("heartbeat", {"username": me.username or ""})
            if isinstance(beat, dict) and "translations" in beat:
                set_edits(beat["translations"])  # texts and languages edited in the dashboard
            if dp and isinstance(beat, dict) and beat.get("token") and beat["token"] != fingerprint(token):
                log.info('{"event":"token_changed","bot":"%s"}', ctx.kind)
                await dp.stop_polling()  # a new token was set in the dashboard: the container restarts the bot with it
                return
        except Exception:
            log.warning('{"event":"heartbeat_failed","bot":"%s"}', ctx.kind)
        await asyncio.sleep(30)


async def describe(bot: Bot, kind: str, commands: list[str]):
    """Default menu commands, profile text and pre-/start description in every supported language.

    Only empty values are filled: anything an administrator set in the panel (stored by Telegram)
    is never overwritten on restart. The fallback language is also registered without
    language_code, so Telegram users with any other interface language see English.
    """
    for code in RETIRED_LANGUAGES:
        # Texts Telegram still stores for a removed language would hide the English default.
        with contextlib.suppress(Exception):
            await bot.delete_my_commands(language_code=code)
            await bot.set_my_short_description("", language_code=code)
            await bot.set_my_description("", language_code=code)
    for code in [None, *catalogs()]:
        lang = code or "en"
        with contextlib.suppress(Exception):
            if not await bot.get_my_commands(language_code=code):
                await bot.set_my_commands([BotCommand(command=c, description=raw(lang, f"cmd_{c}")) for c in commands], language_code=code)
            if not (await bot.get_my_short_description(language_code=code)).short_description:
                await bot.set_my_short_description(raw(lang, f"about_{kind}")[:120], language_code=code)
            if not (await bot.get_my_description(language_code=code)).description:
                await bot.set_my_description(raw(lang, f"welcome_{kind}").format(limit=19)[:512], language_code=code)


async def serve(kind: str, setup: Callable[[Router, Context], None], commands: list[tuple[str, str]]):
    token = settings().bot_token(kind)
    if not token:
        raise SystemExit(f"Set the {kind} bot token in the dashboard (Bots) or {kind.upper()}_BOT_TOKEN in .env")
    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True))
    ctx = Context(kind=kind, bot=bot, api=ApiClient(kind))
    dp = Dispatcher()
    dp.include_router(common_router(ctx))
    from bots.common.money import money_router  # imported here: it builds on this module
    dp.include_router(money_router(ctx))  # before the feature router, whose catch-all handlers take any message
    feature = Router(name=kind)
    setup(feature, ctx)
    dp.include_router(feature)
    await describe(bot, kind, ["start", *(c for c, _ in commands), "language"])
    pulse = asyncio.create_task(heartbeat(ctx, dp, token))
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query", "pre_checkout_query"])
    finally:
        pulse.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pulse
        await ctx.api.close()
        await bot.session.close()


def run(kind: str, setup, commands=()):
    logging.basicConfig(level=logging.INFO)
    from backend import observability
    observability.setup(f"bot-{kind}")  # error tracking when SENTRY_DSN is set
    asyncio.run(serve(kind, setup, list(commands)))


__all__ = ["Context", "run", "serve", "strip", "raw"]
