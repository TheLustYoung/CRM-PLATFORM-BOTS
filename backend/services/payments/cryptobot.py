"""CryptoBot (Crypto Pay API, @CryptoBot): TON, USDT, BTC and more, invoices priced in USD.

Premium is granted only from a webhook signed with the app token (HMAC-SHA256, key = SHA-256 of the token).
"""
import hashlib
import hmac
import json
import httpx
from backend.config import settings
from backend.services.payments import Event, PaymentError, Urls

KEY, CURRENCY = "cryptobot", "USD"
HOSTS = {"mainnet": "https://pay.crypt.bot/api/", "testnet": "https://testnet-pay.crypt.bot/api/"}
ASSETS = "USDT,TON,BTC,ETH,LTC,BNB,TRX,USDC"


def configured(config: dict) -> bool:
    return bool(config.get("api_token"))


def price(plan) -> int | None:
    return round(plan.usd * 100) if getattr(plan, "usd", None) else None


def _call(config: dict, method: str, params: dict | None = None) -> dict:
    base = HOSTS.get(config.get("network") or "mainnet", HOSTS["mainnet"])
    try:
        with httpx.Client(proxy=settings().egress_proxy or None, timeout=20) as client:
            response = client.post(base + method, json=params or {}, headers={"Crypto-Pay-API-Token": config["api_token"]})
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise PaymentError(f"CryptoBot is unreachable ({type(error).__name__})") from None
    if not body.get("ok"):
        raise PaymentError("CryptoBot: " + str((body.get("error") or {}).get("name") or body.get("error") or "error")[:200])
    return body["result"]


def checkout(order, config: dict, urls: Urls, title: str) -> tuple[str, str, dict]:
    invoice = _call(config, "createInvoice", {
        "currency_type": "fiat", "fiat": "USD", "amount": f"{order.amount / 100:.2f}", "accepted_assets": config.get("assets") or ASSETS,
        "description": title[:1024], "payload": order.id, "paid_btn_name": "callback", "paid_btn_url": urls.success,
        "allow_comments": False, "allow_anonymous": True, "expires_in": 7200,
    })
    url = invoice.get("bot_invoice_url") or invoice.get("pay_url")
    return url, str(invoice["invoice_id"]), {"checkout_url": url}


def refund(order, config: dict) -> None:
    raise PaymentError("CryptoBot invoices cannot be refunded automatically: send the coins back from @CryptoBot")


def check(config: dict) -> str:
    me = _call(config, "getMe")
    return f"{me.get('name') or me.get('app_id')} · {config.get('network') or 'mainnet'}"


def verify(body: bytes, signature: str, token: str) -> bool:
    expected = hmac.new(hashlib.sha256(token.encode()).digest(), body, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


def parse_webhook(body: bytes, headers, config: dict) -> list[Event]:
    if not verify(body, headers.get("crypto-pay-api-signature", ""), config.get("api_token", "")):
        raise PaymentError("invalid signature")
    update = json.loads(body)
    invoice = update.get("payload") or {}
    if update.get("update_type") == "invoice_paid" and invoice.get("status") == "paid":
        return [Event("paid", invoice.get("payload"), str(invoice.get("invoice_id")),
                      {"asset": invoice.get("paid_asset") or invoice.get("asset"), "paid_amount": invoice.get("paid_amount")})]
    return []
