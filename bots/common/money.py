"""Premium screen, Telegram Stars payments, invite link and the "I've joined the channel" check (all three bots)."""
import asyncio
import contextlib
import html
import logging
from urllib.parse import quote
from aiogram import F, Router
from aiogram.filters import Command, or_f
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, PreCheckoutQuery
from backend.services.i18n import RLM, is_rtl, raw, tr
from bots.common.client import ApiError
from bots.common.runner import Context, button_texts, channel_keyboard, menu_keyboard, strip

log = logging.getLogger("bots")
STARS = "XTR"  # Telegram Stars: digital goods are paid in Stars, no payment provider token is needed
SUBSCRIPTION_SECONDS = 2_592_000  # the only period Telegram allows for Stars subscriptions (30 days)


def invite_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


def price_text(amount: int, currency: str) -> str:
    return f"${amount / 100:.2f}" if currency == "USD" else f"{amount} {currency}"


def plan_name(lang: str, plan: dict) -> str:
    """The administrator's own name, else "⭐ 30 days" / "🔄 Every month"."""
    if plan.get("title"):
        return plan["title"]
    key = "btn_plan_sub" if plan.get("recurring") else "btn_plan_days"
    name = raw(lang, key).format(days=plan["days"])
    return f"{plan['tier_name']} · {name}" if plan.get("tier", "premium") != "premium" and plan.get("tier_name") else name


def plan_button(lang: str, plan: dict) -> InlineKeyboardButton:
    """One plan: name · prices · -discount% · badge. Stars only: the invoice opens at once; with card/crypto
    too, the next step asks how to pay."""
    page = plan.get("page") or []
    prices = [f"{plan['stars']} ⭐" + ("/30d" if plan.get("recurring") else "")] if plan.get("stars_ok") else []
    if page and page[0]["amount"]:
        prices.append(price_text(page[0]["amount"], page[0]["currency"]))
    extras = [f"-{plan['discount']}%"] if plan.get("discount") else []
    extras += [plan["badge"]] if plan.get("badge") else []
    label = " · ".join([plan_name(lang, plan), " / ".join(prices), *extras]).replace(" ·  · ", " · ").strip(" ·")
    data = f"plan:{plan['key']}" if page else f"buy:{plan['key']}:{plan['stars']}"
    return InlineKeyboardButton(text=label[:64], callback_data=data)


def payment_choice(lang: str, plan: dict, order: dict) -> tuple[str, InlineKeyboardMarkup]:
    """How to pay for one plan: Telegram Stars right here, cards and crypto on our payment page."""
    rows = []
    if plan.get("stars_ok"):
        rows.append([InlineKeyboardButton(text=f"{raw(lang, 'btn_pay_stars')} · {plan['stars']} ⭐",
                                          callback_data=f"buy:{plan['key']}:{plan['stars']}")])
    for method in order["methods"]:  # a method not connected yet still opens the page, which says "coming soon"
        price = f" · {price_text(method['amount'], method['currency'])}" if method["amount"] else ""
        rows.append([InlineKeyboardButton(text=raw(lang, method["label_key"]) + price, url=f"{order['url']}?m={method['key']}")])
    text = tr(lang, "pay_choose_bot", days=plan["days"])
    return (RLM + text if is_rtl(lang) else text), InlineKeyboardMarkup(inline_keyboard=rows)


def premium_screen(lang: str, money: dict, link: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Status, benefits, plans with prices and the personal invite link — one message, every button inside."""
    lines = [raw(lang, "premium_title"), ""]
    if money.get("premium"):
        lines.append(tr(lang, "premium_status_active", date=money["premium_until"][:10]))
    else:
        lines.append(tr(lang, "premium_status_free", used=money.get("used_today", 0), limit=money.get("daily_limit", 0)))
    lines += ["", raw(lang, "premium_benefits"), raw(lang, "premium_b_unlimited")]
    if money.get("free_max_height"):
        lines.append(tr(lang, "premium_b_quality", height=money["free_max_height"]))
    if money.get("free_max_mb"):
        lines.append(tr(lang, "premium_b_size", mb=money["free_max_mb"]))
    lines.append(raw(lang, "premium_b_priority"))
    if money.get("ads"):
        lines.append(raw(lang, "premium_b_noads"))
    buttons = []
    if money.get("plans"):
        lines += ["", raw(lang, "premium_extend" if money.get("premium") else "premium_choose")]
        buttons = [[plan_button(lang, p)] for p in money["plans"]]
    referrals = money.get("referrals")
    if referrals:
        lines += ["", tr(lang, "premium_referral", invites=referrals["invites"], days=referrals["days"],
                         count=referrals["count"], link=link)]
        share = f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(raw(lang, 'share_text'), safe='')}"
        buttons.append([InlineKeyboardButton(text=raw(lang, "btn_share"), url=share)])
    text = "\n".join(lines)
    return (RLM + text if is_rtl(lang) else text), InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def money_router(ctx: Context) -> Router:
    router = Router(name="money")

    async def show(m: Message, profile: dict, user_id: int):
        lang, money = profile["language"], profile.get("money") or {}
        if not (money.get("plans") or money.get("referrals") or money.get("premium")):
            await m.answer(tr(lang, "premium_unavailable"))
            return
        me = await ctx.bot.me()
        text, markup = premium_screen(lang, money, invite_link(me.username, user_id))
        await m.answer(text, reply_markup=markup)

    @router.message(or_f(Command("premium"), F.text.in_(button_texts("menu_premium"))))
    async def premium(message: Message):
        await ctx.guard(message, lambda m, profile: show(m, profile, message.from_user.id))

    @router.callback_query(F.data == "pm")
    async def premium_button(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            await event.answer()
            await show(m, profile, event.from_user.id)
        await ctx.guard(event, action)

    def offered(profile: dict, key: str) -> dict | None:
        return next((p for p in (profile.get("money") or {}).get("plans", []) if p["key"] == key), None)

    @router.callback_query(F.data.startswith("plan:"))
    async def choose_method(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            lang, plan = profile["language"], offered(profile, event.data.split(":")[1])
            if not plan:
                await event.answer(strip(raw(lang, "premium_unavailable")), show_alert=True)
                return
            order = await ctx.api.post("premium/order", {**ctx.identity(event.from_user), "plan": plan["key"]})
            await event.answer()
            text, markup = payment_choice(lang, plan, order)
            await m.answer(text, reply_markup=markup)
        await ctx.guard(event, action)

    @router.callback_query(F.data.startswith("buy:"))
    async def buy(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            lang, money = profile["language"], profile.get("money") or {}
            _, key, stars = event.data.split(":")
            plan = offered(profile, key)
            if not plan or not plan.get("stars_ok") or plan["stars"] != int(stars):
                await event.answer(strip(raw(lang, "premium_unavailable")), show_alert=True)
                return
            await event.answer()
            days = plan["days"]
            invoice = dict(title=(plan.get("title") or raw(lang, "invoice_sub_title" if plan["recurring"] else "invoice_title").format(days=days))[:32],
                           description=raw(lang, "invoice_description").format(days=days)[:255],
                           payload=f"premium:{key}:{stars}", currency=STARS, photo_url=money.get("invoice_photo"),
                           prices=[LabeledPrice(label=raw(lang, "invoice_label").format(days=days)[:32], amount=plan["stars"])])
            if plan["recurring"]:
                # Telegram subscriptions exist only as invoice links; Telegram charges again every 30 days.
                link = await ctx.bot.create_invoice_link(**invoice, subscription_period=SUBSCRIPTION_SECONDS)
                await m.answer(tr(lang, "sub_link_text", stars=stars), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{raw(lang, 'btn_subscribe')} · {stars} ⭐", url=link)]]))
            else:
                await ctx.bot.send_invoice(chat_id=m.chat.id, **invoice)
        await ctx.guard(event, action)

    @router.pre_checkout_query()
    async def checkout(query: PreCheckoutQuery):
        """Telegram asks to confirm the order; we have 10 seconds. Only plans on sale right now are accepted."""
        try:
            if query.currency != STARS:
                raise ApiError("premium_unavailable")
            await ctx.api.post("premium/checkout", {**ctx.identity(query.from_user), "payload": query.invoice_payload,
                                                     "amount": query.total_amount})
            await query.answer(ok=True)
        except Exception:
            await query.answer(ok=False, error_message=strip(raw(ctx.lang(query.from_user), "premium_unavailable")))

    @router.message(F.successful_payment)
    async def paid(message: Message):
        """Stars are charged: activate Premium. Retried, because Telegram sends this update only once."""
        payment = message.successful_payment

        async def action(m: Message, profile: dict):
            body = {**ctx.identity(m.from_user), "payload": payment.invoice_payload, "amount": payment.total_amount,
                    "charge_id": payment.telegram_payment_charge_id}
            for attempt in range(5):
                try:
                    result = await ctx.api.post("premium/activate", body)
                    break
                except Exception:
                    if attempt == 4:
                        # Logged with the charge id so the administrator can grant the days by hand in the dashboard.
                        log.error('{"event":"premium_activation_failed","bot":"%s","user":%s,"charge":"%s"}',
                                  ctx.kind, m.from_user.id, payment.telegram_payment_charge_id)
                        raise
                    await asyncio.sleep(2 ** attempt)
            lang = profile["language"]
            profile["money"] = result["money"]
            await m.answer(tr(lang, "premium_thanks", date=result["premium_until"][:10]),
                           reply_markup=menu_keyboard(ctx.kind, lang, result["money"]))
        await ctx.guard(message, action)

    @router.callback_query(F.data == "jn")
    async def joined(event: CallbackQuery):
        async def action(m: Message, profile: dict):
            lang = profile["language"]
            missing = await ctx.missing_channels(event.from_user.id, profile.get("money"), fresh=True)
            if missing:
                await event.answer(strip(raw(lang, "channel_not_yet")), show_alert=True)
                with contextlib.suppress(Exception):  # only the channels still to join stay on the message
                    await m.edit_reply_markup(reply_markup=channel_keyboard(lang, missing))
                return
            await event.answer()
            await m.edit_text(html.escape(raw(lang, "channel_thanks")))
        await ctx.guard(event, action)

    return router
