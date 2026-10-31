"""Payment providers for the payment page (cards, crypto). Telegram Stars is paid inside the bot.

The catalog below describes every provider the dashboard offers: its category (what the bot button says),
the fields the owner fills in, and where to get them. A provider with a `module` works end to end; one without
is ready in the dashboard (fields are saved) and its button leads to a "coming soon" page until the module is added.

A module exposes: KEY, CURRENCY, configured(config), price(plan), checkout(order, config, urls, title) -> (url, ref, details),
refund(order, config), check(config) -> str, parse_webhook(body, headers, config) -> list[Event].
"""
from dataclasses import dataclass, field


class PaymentError(Exception):
    """Provider refused or is unreachable; the text is safe to show to an administrator."""


@dataclass
class Event:
    """A verified provider notification mapped to our vocabulary."""
    kind: str  # paid | failed | expired | refunded
    order_id: str | None = None
    ref: str | None = None
    details: dict = field(default_factory=dict)


@dataclass
class Urls:
    success: str
    cancel: str


CATEGORIES = {"card": "btn_pay_card", "crypto": "btn_pay_crypto"}  # bot/page button label per category


def _field(key, label, secret=False, placeholder="", options=None):
    return {"key": key, "label": label, "secret": secret, "placeholder": placeholder, **({"options": options} if options else {})}


def catalog() -> dict:
    from backend.services.payments import cryptobot, stripe  # noqa: F401 (modules register below)
    return {
        "stripe": {"category": "card", "title": "Stripe", "module": stripe, "docs": "https://dashboard.stripe.com/apikeys",
                   "webhook": True, "fields": [_field("secret_key", "Secret key", True, "sk_live_… / sk_test_…"),
                                               _field("webhook_secret", "Webhook signing secret", True, "whsec_…")],
                   "events": "checkout.session.completed, checkout.session.async_payment_succeeded, "
                             "checkout.session.async_payment_failed, checkout.session.expired, charge.refunded"},
        "yookassa": {"category": "card", "title": "ЮKassa", "module": None, "docs": "https://yookassa.ru/my/merchant/integration/api-keys",
                     "webhook": True, "fields": [_field("shop_id", "shopId"), _field("secret_key", "Secret key", True, "live_…")]},
        "cloudpayments": {"category": "card", "title": "CloudPayments", "module": None, "docs": "https://merchant.cloudpayments.ru/",
                          "webhook": True, "fields": [_field("public_id", "Public ID", False, "pk_…"), _field("api_secret", "API secret", True)]},
        "paypal": {"category": "card", "title": "PayPal", "module": None, "docs": "https://developer.paypal.com/dashboard/applications",
                   "webhook": True, "fields": [_field("client_id", "Client ID"), _field("client_secret", "Client secret", True),
                                               _field("mode", "Mode", options=["live", "sandbox"])]},
        "cryptobot": {"category": "crypto", "title": "CryptoBot (@CryptoBot)", "module": cryptobot, "docs": "https://t.me/CryptoBot",
                      "webhook": True, "fields": [_field("api_token", "Crypto Pay API token", True, "12345:AA…"),
                                                  _field("network", "Network", options=["mainnet", "testnet"]),
                                                  _field("assets", "Accepted coins", False, "USDT,TON,BTC")]},
        "nowpayments": {"category": "crypto", "title": "NOWPayments", "module": None, "docs": "https://account.nowpayments.io/store-settings",
                        "webhook": True, "fields": [_field("api_key", "API key", True), _field("ipn_secret", "IPN secret", True)]},
        "coingate": {"category": "crypto", "title": "CoinGate", "module": None, "docs": "https://coingate.com/",
                     "webhook": True, "fields": [_field("api_token", "API token", True), _field("mode", "Mode", options=["live", "sandbox"])]},
        "ton_wallet": {"category": "crypto", "title": "Own TON / USDT wallet", "module": None, "docs": "https://toncenter.com/",
                       "webhook": False, "fields": [_field("wallet", "Wallet address", False, "UQ…"),
                                                    _field("api_key", "TON Center API key", True)]},
    }
