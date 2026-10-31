"""Unified billing: orders and transactions for every payment method, one place for Premium activation.

Telegram Stars is paid inside the bot. «Card» and «Crypto» buttons lead to our payment page on the neutral domain,
which uses the provider chosen in the dashboard (Stripe, CryptoBot, …):
bot → /pay/<token> → provider → signed webhook → Premium → message in the bot.
A category switched on before its provider is connected still shows its button; the page then says "coming soon".
The provider's redirect back to our page is only a courtesy screen; it never activates anything.
"""
import secrets
from datetime import timedelta
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from backend.config import settings
from backend.models import Order, SystemSetting, User, aware, now
from backend.services import monetization
from backend.services.payments import CATEGORIES, Event, PaymentError, Urls, catalog
from backend.services.security import DomainError

SETTING_KEY = "payments"
ORDER_TTL = timedelta(hours=2)


class Category(BaseModel):
    enabled: bool = True  # the button shows in the bots; it works once the provider below is connected
    provider: str = ""


class PaymentSettings(BaseModel):
    stars_enabled: bool = True
    public_url: str = ""  # neutral domain for payment pages and file links; empty = server default
    card: Category = Field(default_factory=lambda: Category(provider="stripe"))
    crypto: Category = Field(default_factory=lambda: Category(provider="cryptobot"))
    providers: dict[str, dict[str, str]] = Field(default_factory=dict)

    @field_validator("public_url")
    @classmethod
    def https(cls, value):
        value = value.strip().rstrip("/")
        if value and not (value.startswith("https://") and "." in value and " " not in value):
            raise ValueError("the domain must look like https://pay.example.com")
        return value

    @model_validator(mode="after")
    def known_providers(self):
        known = catalog()
        for category in CATEGORIES:
            chosen = getattr(self, category).provider
            if chosen and (chosen not in known or known[chosen]["category"] != category):
                raise ValueError(f"unknown {category} provider: {chosen}")
        for name, values in self.providers.items():
            if name not in known:
                raise ValueError(f"unknown provider: {name}")
            allowed = {f["key"] for f in known[name]["fields"]}
            if set(values) - allowed:
                raise ValueError(f"unknown field for {name}")
        return self


def load(db) -> PaymentSettings:
    row = db.get(SystemSetting, SETTING_KEY)
    return PaymentSettings.model_validate(row.value) if row else PaymentSettings()


def save(db, update: dict) -> PaymentSettings:
    """Merge a dashboard update. None keeps the stored value (secrets are never sent back), "" clears it."""
    current = load(db).model_dump()
    for name, section in update.items():
        if name == "providers":
            for provider, values in (section or {}).items():
                stored = current["providers"].setdefault(provider, {})
                for key, value in (values or {}).items():
                    if value is None:
                        continue
                    if value == "":
                        stored.pop(key, None)
                    else:
                        stored[key] = value.strip()
        elif isinstance(section, dict) and isinstance(current.get(name), dict):
            current[name].update({k: v for k, v in section.items() if v is not None})
        elif section is not None:
            current[name] = section
    data = PaymentSettings.model_validate(current)
    db.merge(SystemSetting(key=SETTING_KEY, value=data.model_dump()))
    db.commit()
    return data


def masked(value: str) -> str:
    return f"{value[:6]}…{value[-4:]}" if len(value) > 12 else ("•••" if value else "")


def public_base(db) -> str:
    """Neutral domain for the payment page and file links (dashboard setting), else the server default."""
    return load(db).public_url or settings().public_files_url.rstrip("/")


def config(db, provider: str) -> dict:
    return dict(load(db).providers.get(provider, {}))


def ready(db, provider: str) -> bool:
    info = catalog().get(provider)
    return bool(info and info["module"] and info["module"].configured(config(db, provider)))


def public_view(db) -> dict:
    """Everything the «Payments» page needs. Secret values never leave the server: only a masked hint."""
    data, base = load(db), public_base(db)
    providers = []
    for name, info in catalog().items():
        stored = data.providers.get(name, {})
        fields = [{**f, "value": None if f["secret"] else stored.get(f["key"], ""), "set": bool(stored.get(f["key"])),
                   "hint": masked(stored.get(f["key"], "")) if f["secret"] else ""} for f in info["fields"]]
        providers.append({"key": name, "category": info["category"], "title": info["title"], "docs": info["docs"],
                          "implemented": info["module"] is not None, "ready": ready(db, name), "fields": fields,
                          "webhook_url": f"{base}/webhooks/{name}" if info["webhook"] else None, "events": info.get("events")})
    return {"stars_enabled": data.stars_enabled, "public_url": data.public_url, "base_url": base,
            "card": data.card.model_dump(), "crypto": data.crypto.model_dump(), "providers": providers}


def page_methods(db, plan) -> list[dict]:
    """Card / crypto buttons for a plan: every category switched on, with `ready` once its provider works."""
    data, result = load(db), []
    for category, label_key in CATEGORIES.items():
        chosen = getattr(data, category)
        if not chosen.enabled:
            continue
        info = catalog().get(chosen.provider)
        amount = round(plan.usd_price() * 100) if plan.usd_price() else None  # discount included
        result.append({"key": category, "label_key": label_key, "provider": chosen.provider, "currency": "USD", "amount": amount,
                       "ready": bool(info and amount and ready(db, chosen.provider))})
    return result


def plan_for(db, key: str | int) -> monetization.Plan:
    """A one-time plan on sale (subscriptions renew in Telegram Stars only, never on the payment page)."""
    m = monetization.settings(db)
    plan = m.plan(str(key))
    if not m.premium_enabled or not plan or plan.recurring:
        raise DomainError("premium_unavailable")
    return plan


def create_order(db, user: User, bot_id: str, key: str, lang: str) -> Order:
    plan = plan_for(db, key)
    order = Order(token=secrets.token_urlsafe(24), user_id=user.id, bot_id=bot_id, days=plan.days, lang=lang,
                  details={"plan": plan.key}, expires_at=now() + ORDER_TTL)
    db.add(order)
    db.commit()
    return order


def by_token(db, token: str) -> Order:
    order = db.scalar(select(Order).where(Order.token == token)) if 10 < len(token) <= 48 else None
    if not order:
        raise DomainError("not_found")
    if order.status == "pending" and aware(order.expires_at) < now():
        order.status = "expired"
        db.commit()
    return order


def start(db, order: Order, category: str, urls: Urls, title: str) -> str:
    """Create (or reuse) the provider checkout for this order; "payment_soon" while the provider is not connected."""
    if order.status != "pending":
        raise DomainError("not_found")
    offer = next((m for m in page_methods(db, plan_for(db, order_plan(order))) if m["key"] == category), None)
    if not offer:
        raise DomainError("premium_unavailable")
    if not offer["ready"]:
        raise DomainError("payment_soon")
    if order.method == offer["provider"] and order.details.get("checkout_url"):
        return order.details["checkout_url"]  # pressing the button twice never creates a second payment
    module = catalog()[offer["provider"]]["module"]
    order.method, order.currency, order.amount = offer["provider"], offer["currency"], offer["amount"]
    url, ref, details = module.checkout(order, config(db, offer["provider"]), urls, title)
    order.provider_ref, order.details = ref, {**(order.details or {}), **details, "category": category}
    db.commit()
    return url


def order_plan(order: Order) -> str:
    """The plan key of an order («30», «gold.30»); orders made before tiers existed only know their days."""
    return (order.details or {}).get("plan") or str(order.days)


def _grant(db, order: Order) -> None:
    user = db.get(User, order.user_id)
    monetization.grant(db, user, order.days, (order.method or "page")[:16], stars=order.amount if order.currency == "XTR" else 0,
                       bot_id=order.bot_id, charge_id=f"{order.method}:{order.provider_ref or order.id}",
                       tier=monetization.tier_key(order_plan(order)))


def apply(db, provider: str, event: Event) -> Order | None:
    """Apply one verified provider event. Idempotent: repeated or out-of-order webhooks change nothing twice.
    Returns the order when this event is the one that made it paid (so the user is told exactly once)."""
    order = db.get(Order, event.order_id) if event.order_id else None
    if order is None and event.details.get("payment_intent"):
        order = next((o for o in db.scalars(select(Order).where(Order.method == provider, Order.status.in_(["paid", "refunded"])))
                      if (o.details or {}).get("payment_intent") == event.details["payment_intent"]), None)
    if order is None or order.method not in (None, provider):
        return None
    if event.kind == "paid" and order.status in ("pending", "expired", "failed"):  # a late payment still counts
        order.method = provider
        order.status, order.paid_at = "paid", now()
        order.provider_ref = event.ref or order.provider_ref
        order.details = {**(order.details or {}), **event.details}
        db.commit()
        _grant(db, order)
        return order
    if event.kind in ("failed", "expired") and order.status == "pending":
        order.status = event.kind
        db.commit()
    elif event.kind == "refunded" and order.status == "paid":
        _refunded(db, order)
    return None


def _refunded(db, order: Order) -> None:
    order.status, order.refunded_at = "refunded", now()
    db.commit()
    monetization.take_back(db, db.get(User, order.user_id), order.days)


def record_stars(db, user: User, bot_id: str, plan: monetization.Plan, charge_id: str, lang: str) -> None:
    """Stars are paid inside Telegram: keep them in the same transaction history and revenue reports."""
    if db.scalar(select(Order).where(Order.method == "stars", Order.provider_ref == charge_id)):
        return
    db.add(Order(token=secrets.token_urlsafe(24), user_id=user.id, bot_id=bot_id, days=plan.days, method="stars", currency="XTR",
                 amount=plan.stars, status="paid", details={"recurring": plan.recurring, "plan": plan.key}, provider_ref=charge_id, lang=lang, paid_at=now(),
                 expires_at=now()))
    db.commit()


def refund(db, order: Order, telegram=None) -> Order:
    """Administrator refund: money back through the provider, then the Premium days are taken back."""
    if order.status != "paid":
        raise PaymentError("Only paid orders can be refunded")
    if order.method == "stars":
        if telegram is None:
            raise PaymentError("Telegram is not available")
        telegram.call("refundStarPayment", {"user_id": order.user_id, "telegram_payment_charge_id": order.provider_ref})
    else:
        info = catalog().get(order.method or "")
        if not info or not info["module"]:
            raise PaymentError("This payment method has no automatic refunds")
        info["module"].refund(order, config(db, order.method))
    _refunded(db, order)
    return order


def expire_stale(db) -> int:
    stale = list(db.scalars(select(Order).where(Order.status == "pending", Order.expires_at < now()).limit(500)))
    for order in stale:
        order.status = "expired"
    db.commit()
    return len(stale)


def revenue(db) -> list[dict]:
    """Paid revenue by method and currency for today, 7 and 30 days and all time (refunds excluded)."""
    rows = []
    start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
    periods = {"today": start_of_day, "d7": now() - timedelta(days=7), "d30": now() - timedelta(days=30), "all": None}
    keys = db.execute(select(Order.method, Order.currency).where(Order.status == "paid").distinct()).all()
    for method, currency in keys:
        row = {"method": method, "currency": currency}
        for name, since in periods.items():
            where = [Order.status == "paid", Order.method == method, Order.currency == currency]
            if since is not None:
                where.append(Order.paid_at >= since)
            row[name] = db.scalar(select(func.coalesce(func.sum(Order.amount), 0)).where(*where))
            row[f"{name}_count"] = db.scalar(select(func.count()).select_from(Order).where(*where))
        rows.append(row)
    return rows
