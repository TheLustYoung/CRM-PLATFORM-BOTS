"""Payment page on the neutral domain and provider webhooks.

/pay/<token>            order summary and the enabled methods (cards, crypto), in the user's language
/pay/<token>/go/<m>     creates the provider checkout and redirects there
/pay/<token>/done       return page: shows the real status, refreshes until the webhook arrives
/webhooks/<method>      signed provider notifications: the only thing that activates Premium
"""
import html
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from backend.api.public import SECURITY_HEADERS, page_language
from backend.database import session
from backend.models import Bot, User, aware
from backend.services import billing, i18n
from backend.services.limits import rate_limit
from backend.services.payments import PaymentError, Urls, catalog
from backend.services.security import DomainError
from workers.telegram import Telegram

router = APIRouter(tags=["payments"])
log = logging.getLogger(__name__)
STYLE = """Body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;
display:grid;place-items:center}main{width:min(440px,calc(100% - 32px));background:#111c33;border:1px solid #23314f;border-radius:20px;padding:28px;
box-shadow:0 20px 60px rgba(0,0,0,.35)}h1{font-size:22px;margin:0 0 6px}p{color:#94a3b8;line-height:1.5;margin:0 0 18px}
.price{font-size:15px;color:#cbd5e1;margin-bottom:20px}a.button{display:flex;justify-content:space-between;align-items:center;gap:12px;
background:#1e293b;border:1px solid #334155;color:#f8fafc;font-weight:600;padding:15px 16px;border-radius:14px;text-decoration:none;margin-bottom:10px}
a.button.primary{background:#3b82f6;border-color:#3b82f6}a.button:hover{filter:brightness(1.1)}a.back{display:block;text-align:center;color:#94a3b8;
margin-top:14px;text-decoration:none}.secure{font-size:12px;color:#64748b;text-align:center;margin-top:16px}footer{margin-top:18px;font-size:12px;
color:#64748b;text-align:center;line-height:1.8}footer a{color:#64748b}"""


def amount_text(amount: int, currency: str) -> str:
    return f"${amount / 100:.2f}" if currency == "USD" else f"{amount} {currency}"


def page(lang: str, body: str, refresh: bool = False, status: int = 200) -> HTMLResponse:
    t = lambda key: html.escape(i18n.raw(lang, key))
    switch = " · ".join(f'<a href="?lang={code}">{html.escape(name)}</a>' for code, name in i18n.languages().items())
    meta = '<meta http-equiv="refresh" content="3">' if refresh else ""
    document = f"""<!doctype html><html lang="{lang}" dir="{'rtl' if i18n.is_rtl(lang) else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">{meta}
<title>{t('page_pay_title')}</title><style>{STYLE}</style></head><body><main>{body}<footer>{switch}</footer></main></body></html>"""
    return HTMLResponse(document, status_code=status, headers={**SECURITY_HEADERS,
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})


def bot_link(db, order) -> str:
    bot = db.get(Bot, order.bot_id)
    return f"https://t.me/{bot.username}" if bot and bot.username else "https://t.me/"


def back(db, order, lang) -> str:
    return f'<a class="back" href="{html.escape(bot_link(db, order), quote=True)}">{html.escape(i18n.raw(lang, "btn_back_to_bot"))}</a>'


def message(db, order, lang, title: str, text: str, refresh=False, status=200) -> HTMLResponse:
    return page(lang, f"<h1>{html.escape(title)}</h1><p>{html.escape(text)}</p>{back(db, order, lang)}", refresh, status)


def lookup(db, token: str, request: Request):
    rate_limit(f"pay:{request.client.host}", 60, 60)
    order = billing.by_token(db, token)
    lang = request.query_params.get("lang") if request.query_params.get("lang") in i18n.catalogs() else order.lang
    return order, lang


def status_page(db, order, lang):
    raw = lambda key, **kw: i18n.raw(lang, key).format(**kw)
    if order.status == "paid":
        user = db.get(User, order.user_id)
        until = aware(user.premium_until).date().isoformat() if user and user.premium_until else ""
        return message(db, order, lang, raw("pay_paid_title"), raw("pay_paid_text", date=until))
    texts = {"expired": "pay_expired", "failed": "pay_failed", "canceled": "pay_expired", "refunded": "pay_refunded"}
    return message(db, order, lang, raw("page_pay_title"), raw(texts.get(order.status, "pay_expired")))


@router.get("/pay/{token}", response_class=HTMLResponse)
def pay_page(token: str, request: Request, db=Depends(session)):
    try:
        order, lang = lookup(db, token, request)
    except DomainError:
        return page(page_language(request), f"<h1>{html.escape(i18n.raw(page_language(request), 'page_not_found'))}</h1>", status=404)
    if order.status != "pending":
        return status_page(db, order, lang)
    try:
        methods = billing.page_methods(db, billing.plan_for(db, billing.order_plan(order)))
    except DomainError:
        methods = []
    if not methods:
        return message(db, order, lang, i18n.raw(lang, "page_pay_title"), i18n.raw(lang, "pay_unavailable"))
    wanted = request.query_params.get("m")
    methods.sort(key=lambda m: m["key"] != wanted)
    buttons = "".join(
        f'<a class="button{" primary" if i == 0 else ""}" href="/pay/{html.escape(token)}/go/{m["key"]}?lang={lang}">'
        f'<span>{html.escape(i18n.raw(lang, m["label_key"]))}</span>'
        f'<span>{html.escape(amount_text(m["amount"], m["currency"])) if m["amount"] else ""}</span></a>'
        for i, m in enumerate(methods))
    body = (f'<h1>{html.escape(i18n.raw(lang, "pay_plan").format(days=order.days))}</h1>'
            f'<p>{html.escape(i18n.raw(lang, "pay_choose"))}</p>{buttons}'
            f'<div class="secure">🔒 {html.escape(i18n.raw(lang, "pay_secure"))}</div>{back(db, order, lang)}')
    return page(lang, body)


@router.get("/pay/{token}/go/{category}")
def pay_go(token: str, category: str, request: Request, db=Depends(session)):
    try:
        order, lang = lookup(db, token, request)
    except DomainError:
        return page(page_language(request), f"<h1>{html.escape(i18n.raw(page_language(request), 'page_not_found'))}</h1>", status=404)
    if order.status != "pending":
        return status_page(db, order, lang)
    base = f"{billing.public_base(db)}/pay/{token}"
    urls = Urls(success=f"{base}/done?lang={lang}", cancel=f"{base}?lang={lang}")
    try:
        url = billing.start(db, order, category, urls, i18n.raw(lang, "invoice_title").format(days=order.days))
    except DomainError as error:
        # Switched on in the dashboard but no provider connected yet: an honest "coming soon" page.
        key = "pay_soon" if str(error) == "payment_soon" else "pay_unavailable"
        return message(db, order, lang, i18n.raw(lang, "page_pay_title"), i18n.raw(lang, key))
    except PaymentError as error:
        log.warning('{"event":"checkout_failed","order":"%s","category":"%s","error":"%s"}', order.id, category, str(error)[:200])
        return message(db, order, lang, i18n.raw(lang, "page_pay_title"), i18n.raw(lang, "pay_unavailable"), status=503)
    return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.get("/pay/{token}/done", response_class=HTMLResponse)
def pay_done(token: str, request: Request, db=Depends(session)):
    try:
        order, lang = lookup(db, token, request)
    except DomainError:
        return page(page_language(request), f"<h1>{html.escape(i18n.raw(page_language(request), 'page_not_found'))}</h1>", status=404)
    if order.status == "pending":  # the provider sent the user back before its webhook reached us
        return message(db, order, lang, i18n.raw(lang, "page_pay_title"), i18n.raw(lang, "pay_waiting"), refresh=True)
    return status_page(db, order, lang)


def notify(db, order) -> None:
    """Tell the user in the bot that Premium is active (best effort: the payment is already recorded)."""
    try:
        user = db.get(User, order.user_id)
        with Telegram(order.bot_id) as telegram:
            telegram.message(order.user_id, i18n.tr(order.lang, "premium_thanks", date=aware(user.premium_until).date().isoformat()))
    except Exception:
        log.warning('{"event":"paid_notice_failed","order":"%s"}', order.id)


@router.post("/webhooks/{provider}")
async def webhook(provider: str, request: Request, db=Depends(session)):
    info = catalog().get(provider)
    if not info or not info["module"]:
        raise HTTPException(404, "not_found")
    body = await request.body()
    if len(body) > 1_000_000:
        raise HTTPException(413, "too_large")
    try:
        events = info["module"].parse_webhook(body, request.headers, billing.config(db, provider))
    except (PaymentError, ValueError):
        log.warning('{"event":"webhook_rejected","provider":"%s"}', provider)
        raise HTTPException(400, "invalid") from None
    for event in events:
        paid = billing.apply(db, provider, event)
        if paid:
            log.info('{"event":"order_paid","order":"%s","provider":"%s"}', paid.id, provider)
            await run_in_threadpool(notify, db, paid)
    return JSONResponse({"ok": True})
