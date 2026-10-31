import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from backend.config import settings
from backend.models import Order, User
from backend.services import billing, monetization, users
from backend.services.payments import cryptobot, stripe


def headers(kind="media"):
    return {"X-Bot-Kind": kind, "X-Service-Key": settings().service_key(kind)}


def signed_stripe(payload: dict, secret="whsec_test") -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256).hexdigest()
    return body, {"Stripe-Signature": f"t={stamp},v1={signature}", "Content-Type": "application/json"}


def setup_shop(db, **payments):
    monetization.save(db, monetization.Settings(premium_enabled=True, plans=[
        {"days": 30, "stars": 100, "usd": 2.0}, {"days": 30, "stars": 100, "recurring": True, "discount": 20}, {"days": 90, "stars": 250}]))
    billing.save(db, {"public_url": "https://pay.neutral.example", **payments})
    users.register(db, "media", 7)


def test_stripe_and_cryptobot_signatures():
    body, hdrs = signed_stripe({"type": "x"})
    assert stripe.verify(body, hdrs["Stripe-Signature"], "whsec_test")
    assert not stripe.verify(body + b" ", hdrs["Stripe-Signature"], "whsec_test")
    assert not stripe.verify(body, hdrs["Stripe-Signature"], "whsec_test", now=time.time() + 600)  # replayed later
    token = "12345:AAtest"
    raw = json.dumps({"update_type": "invoice_paid", "payload": {"invoice_id": 9, "status": "paid", "payload": "order-1"}}).encode()
    signature = hmac.new(hashlib.sha256(token.encode()).digest(), raw, hashlib.sha256).hexdigest()
    events = cryptobot.parse_webhook(raw, {"crypto-pay-api-signature": signature}, {"api_token": token})
    assert events[0].kind == "paid" and events[0].order_id == "order-1" and events[0].ref == "9"
    with pytest.raises(Exception):
        cryptobot.parse_webhook(raw, {"crypto-pay-api-signature": "0" * 64}, {"api_token": token})


def test_card_payment_from_bot_to_premium(client, db, monkeypatch):
    setup_shop(db, card={"enabled": True, "provider": "stripe"},
               providers={"stripe": {"secret_key": "sk_test_123456789", "webhook_secret": "whsec_test"}})
    money = client.post("/internal/register", headers=headers(), json={"user_id": 7}).json()["money"]
    month = next(p for p in money["plans"] if p["key"] == "30")
    assert month["page"][0] == {"key": "card", "label_key": "btn_pay_card", "provider": "stripe", "currency": "USD", "amount": 200, "ready": True}
    assert next(p for p in money["plans"] if p["key"] == "30r")["page"] == []  # subscriptions renew in Stars only

    order = client.post("/internal/premium/order", headers=headers(), json={"user_id": 7, "plan": "30"}).json()
    assert order["url"].startswith("https://pay.neutral.example/pay/")
    path = order["url"].removeprefix("https://pay.neutral.example")
    page = client.get(path + "?m=card")
    assert page.status_code == 200 and "$2.00" in page.text and "/go/card" in page.text

    calls = []
    monkeypatch.setattr(stripe, "_call", lambda config, method, route, data=None: calls.append(data) or
                        {"id": "cs_1", "url": "https://checkout.stripe.com/c/cs_1"})
    go = client.get(path + "/go/card", follow_redirects=False)
    assert go.status_code == 303 and go.headers["location"] == "https://checkout.stripe.com/c/cs_1"
    assert client.get(path + "/go/card", follow_redirects=False).headers["location"].endswith("cs_1") and len(calls) == 1  # reused
    assert calls[0]["line_items[0][price_data][unit_amount]"] == "200" and calls[0]["success_url"].endswith("/done?lang=en")
    assert "Confirming" in client.get(path + "/done").text  # the redirect alone never activates anything

    from backend.api import pay
    told = MagicMock()
    told.__enter__ = lambda self: self
    told.__exit__ = lambda self, *a: None
    monkeypatch.setattr(pay, "Telegram", lambda kind: told)
    event = {"type": "checkout.session.completed", "data": {"object": {"id": "cs_1", "payment_status": "paid",
             "payment_intent": "pi_1", "metadata": {"order_id": db.scalar(select(Order.id))}}}}
    body, hdrs = signed_stripe(event)
    assert client.post("/webhooks/stripe", content=body, headers=hdrs).status_code == 200
    assert client.post("/webhooks/stripe", content=body, headers=hdrs).status_code == 200  # Stripe retries: harmless
    assert monetization.is_premium(db.get(User, 7)) and told.message.call_count == 1
    paid = db.scalar(select(Order))
    assert (paid.status, paid.method, paid.amount, paid.details["payment_intent"]) == ("paid", "stripe", 200, "pi_1")
    assert "Payment received" in client.get(path + "/done").text
    bad = signed_stripe(event, secret="whsec_other")
    assert client.post("/webhooks/stripe", content=bad[0], headers=bad[1]).status_code == 400

    monkeypatch.setattr(stripe, "_call", lambda config, method, route, data=None: calls.append((route, data)) or {})
    billing.refund(db, paid)
    assert calls[-1] == ("refunds", {"payment_intent": "pi_1", "metadata[order_id]": paid.id})
    assert paid.status == "refunded" and not monetization.is_premium(db.get(User, 7))


def test_buttons_work_before_a_provider_is_connected(client, db):
    setup_shop(db, crypto={"enabled": True, "provider": "nowpayments"}, card={"enabled": False, "provider": "stripe"})
    order = client.post("/internal/premium/order", headers=headers(), json={"user_id": 7, "plan": "30"}).json()
    assert [m["key"] for m in order["methods"]] == ["crypto"] and order["methods"][0]["ready"] is False
    path = order["url"].removeprefix("https://pay.neutral.example")
    soon = client.get(path + "/go/crypto")
    assert soon.status_code == 200 and "available very soon" in soon.text and "t.me/media_test_bot" in soon.text


def test_stars_payments_join_the_same_history(client, db):
    setup_shop(db)
    paid = {"user_id": 7, "payload": "premium:30r:80", "amount": 80, "charge_id": "tg-1"}
    assert client.post("/internal/premium/checkout", headers=headers(), json=paid).json()["days"] == 30  # 20% off 100 ⭐
    assert client.post("/internal/premium/checkout", headers=headers(), json={**paid, "payload": "premium:30r:100", "amount": 100}).status_code == 400
    client.post("/internal/premium/activate", headers=headers(), json=paid)
    client.post("/internal/premium/activate", headers=headers(), json={**paid, "charge_id": "tg-2"})  # Telegram renewal 30 days later
    assert db.scalar(select(func.count()).select_from(Order).where(Order.method == "stars")) == 2
    row = billing.revenue(db)[0]
    assert (row["method"], row["currency"], row["all"], row["all_count"]) == ("stars", "XTR", 160, 2)


def test_plans_follow_telegram_rules():
    with pytest.raises(ValidationError):
        monetization.Plan(days=90, stars=100, recurring=True)  # Telegram renews subscriptions every 30 days only
    with pytest.raises(ValidationError):
        monetization.Plan(days=30, stars=10_001)
    plan = monetization.Plan(days=30, stars=99, usd=4.99, discount=50)
    assert (plan.stars_price(), plan.usd_price(), plan.key) == (50, 2.5, "30")


def test_admin_keeps_secrets_on_the_server(admin_client, db):
    saved = admin_client.put("/api/admin/payments", json={"card": {"enabled": True, "provider": "stripe"},
                                                          "providers": {"stripe": {"secret_key": "sk_test_abcdefghijklmnop", "webhook_secret": "whsec_x"}}}).json()
    stripe_view = next(p for p in saved["providers"] if p["key"] == "stripe")
    secret = next(f for f in stripe_view["fields"] if f["key"] == "secret_key")
    assert secret["value"] is None and secret["set"] and secret["hint"] == "sk_tes…mnop" and "abcdefgh" not in json.dumps(saved)
    assert stripe_view["webhook_url"].endswith("/webhooks/stripe") and stripe_view["ready"]
    admin_client.put("/api/admin/payments", json={"providers": {"stripe": {"secret_key": None, "webhook_secret": ""}}})
    assert billing.config(db, "stripe") == {"secret_key": "sk_test_abcdefghijklmnop"}  # None kept, "" removed
    assert admin_client.put("/api/admin/payments", json={"card": {"provider": "cryptobot"}}).status_code == 400
    assert admin_client.put("/api/admin/payments", json={"public_url": "http://plain.example"}).status_code == 400
    assert admin_client.post("/api/admin/payments/yookassa/test").json()["ok"] is False
