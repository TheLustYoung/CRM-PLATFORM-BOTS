"""Stripe Checkout for card payments, over Stripe's HTTP API — no SDK needed.

Premium is granted only from a webhook whose Stripe-Signature is valid; the success redirect is never trusted.
"""
import hashlib
import hmac
import json
import time
import httpx
from backend.config import settings
from backend.services.payments import Event, PaymentError, Urls

KEY, CURRENCY = "stripe", "USD"
API = "https://api.stripe.com/v1/"
TOLERANCE = 300  # seconds: older signed webhooks are rejected (replay protection)
EVENTS = ["checkout.session.completed", "checkout.session.async_payment_succeeded", "checkout.session.async_payment_failed",
          "checkout.session.expired", "charge.refunded"]


def configured(config: dict) -> bool:
    return bool(config.get("secret_key")) and bool(config.get("webhook_secret"))


def price(plan) -> int | None:
    return round(plan.usd * 100) if getattr(plan, "usd", None) else None


def _call(config: dict, method: str, path: str, data: dict | None = None) -> dict:
    try:
        with httpx.Client(proxy=settings().egress_proxy or None, timeout=20) as client:
            response = client.request(method, API + path, data=data, auth=(config["secret_key"], ""))
    except httpx.HTTPError as error:
        raise PaymentError(f"Stripe is unreachable ({type(error).__name__})") from None
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    if response.status_code >= 400:
        raise PaymentError("Stripe: " + str((body.get("error") or {}).get("message") or f"HTTP {response.status_code}")[:300])
    return body


def checkout(order, config: dict, urls: Urls, title: str) -> tuple[str, str, dict]:
    session = _call(config, "POST", "checkout/sessions", {
        "mode": "payment", "client_reference_id": order.id, "metadata[order_id]": order.id,
        "payment_intent_data[metadata][order_id]": order.id,
        "line_items[0][quantity]": "1", "line_items[0][price_data][currency]": CURRENCY.lower(),
        "line_items[0][price_data][unit_amount]": str(order.amount), "line_items[0][price_data][product_data][name]": title,
        "success_url": urls.success, "cancel_url": urls.cancel, "locale": "auto",
        "expires_at": str(int(time.time()) + 1800),  # 30 minutes, Stripe's minimum
    })
    return session["url"], session["id"], {"checkout_url": session["url"]}


def refund(order, config: dict) -> None:
    intent = (order.details or {}).get("payment_intent")
    if not intent:
        raise PaymentError("Stripe: the payment has no payment intent to refund")
    _call(config, "POST", "refunds", {"payment_intent": intent, "metadata[order_id]": order.id})


def check(config: dict) -> str:
    """Admin «Test»: confirms the key works and says whether it is a test or a live key."""
    account = _call(config, "GET", "account")
    mode = "live" if config["secret_key"].startswith(("sk_live", "rk_live")) else "test"
    return f"{account.get('settings', {}).get('dashboard', {}).get('display_name') or account.get('id')} · {mode}"


def verify(body: bytes, header: str, secret: str, now: float | None = None) -> bool:
    parts = [p.split("=", 1) for p in (header or "").split(",") if "=" in p]
    stamp = next((v for k, v in parts if k == "t"), "")
    signatures = [v for k, v in parts if k == "v1"]
    if not stamp.isdigit() or not signatures or abs((now or time.time()) - int(stamp)) > TOLERANCE:
        return False
    expected = hmac.new(secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in signatures)


def parse_webhook(body: bytes, headers, config: dict) -> list[Event]:
    if not verify(body, headers.get("stripe-signature", ""), config.get("webhook_secret", "")):
        raise PaymentError("invalid signature")
    event = json.loads(body)
    kind, obj = event.get("type"), (event.get("data") or {}).get("object") or {}
    order_id = (obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id")
    if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") != "paid":
            return []  # e.g. bank transfer still pending: wait for async_payment_succeeded
        return [Event("paid", order_id, obj.get("id"), {"payment_intent": obj.get("payment_intent")})]
    if kind == "checkout.session.async_payment_failed":
        return [Event("failed", order_id, obj.get("id"))]
    if kind == "checkout.session.expired":
        return [Event("expired", order_id, obj.get("id"))]
    if kind == "charge.refunded":
        return [Event("refunded", order_id, None, {"payment_intent": obj.get("payment_intent")})]
    return []
