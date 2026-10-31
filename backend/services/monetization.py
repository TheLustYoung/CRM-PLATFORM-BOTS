"""Monetization: Premium (Telegram Stars), referral rewards, sponsored messages and the required channel.

Everything is configured in the admin dashboard and stored as one system setting, so the owner can switch
each income source on or off without a deploy. Premium is a date on the shared user, so it works in every bot.
"""
import hashlib
import re
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from backend.config import BOT_KINDS
from backend.models import Payment, SystemSetting, User, aware, now, uid
from backend.services import limits
from backend.services.limits import Policy
from backend.services.security import DomainError

SETTING_KEY = "monetization"
AD_VIEWS_KEY = "ads:views"
INVOICE_PREFIX = "premium"
CHANNEL = re.compile(r"^(@[A-Za-z][A-Za-z0-9_]{3,31}|-100\d{5,15})$")
LINK = re.compile(r"^https://[^\s<>\"']{3,300}$")


STARS_MAX = 10_000  # Telegram's limit for a Stars invoice and for a Stars subscription price
SUBSCRIPTION_DAYS = 30  # Telegram Stars subscriptions always renew every 30 days (subscription_period = 2592000 s)
# "30" = one-time 30 days, "30r" = Telegram subscription renewed every 30 days; "gold.30" = 30 days of the tier "gold"
# (the default tier "premium" keeps the short keys, so earlier invoices and running subscriptions stay valid).
PLAN_KEY = r"(?:[a-z0-9_-]{1,24}\.)?\d{1,4}r?"
DEFAULT_TIER = "premium"


class Tier(BaseModel):
    """A paid level with its own limits; 0 means «no extra limit» (the server limits still apply)."""
    key: str = Field(default=DEFAULT_TIER, pattern=r"^[a-z0-9_-]{1,24}$")
    name: str = Field(default="Premium", min_length=1, max_length=32)
    daily_jobs: int = Field(default=0, ge=0, le=100_000)  # downloads and uploads per day
    max_mb: int = Field(default=0, ge=0, le=2000)  # largest download
    max_height: int = Field(default=0, ge=0, le=4320)  # best video quality
    storage_mb: int = Field(default=0, ge=0, le=10_000_000)  # files kept by the File bot at once
    priority: bool = True  # jobs go before the free queue
    no_ads: bool = True  # sponsored messages are not shown
    platforms: list[str] = Field(default_factory=list, max_length=20)  # platforms included; empty = every platform


class Plan(BaseModel):
    """A Premium plan exactly as Telegram allows it: a one-time purchase of N days, or a Stars subscription
    that Telegram renews every 30 days until the user cancels it in Telegram settings."""
    tier: str = Field(default=DEFAULT_TIER, pattern=r"^[a-z0-9_-]{1,24}$")
    days: int = Field(ge=1, le=3650)
    stars: int = Field(ge=1, le=STARS_MAX)
    usd: float | None = Field(default=None, ge=0.5, le=10_000)  # price on the payment page (cards, crypto); None = Stars only
    recurring: bool = False
    enabled: bool = True
    title: str = Field(default="", max_length=32)  # optional own name, e.g. "Monthly"
    badge: str = Field(default="", max_length=24)  # optional label, e.g. "🔥 Best value"
    discount: int = Field(default=0, ge=0, le=90)  # percent off both prices

    @model_validator(mode="after")
    def telegram_rules(self):
        if self.recurring and self.days != SUBSCRIPTION_DAYS:
            raise ValueError("a Telegram Stars subscription always renews every 30 days")
        self.title, self.badge = self.title.strip(), self.badge.strip()
        return self

    @property
    def key(self) -> str:
        prefix = "" if self.tier == DEFAULT_TIER else f"{self.tier}."
        return f"{prefix}{self.days}{'r' if self.recurring else ''}"

    def stars_price(self) -> int:
        return max(1, round(self.stars * (100 - self.discount) / 100))

    def usd_price(self) -> float | None:
        return round(self.usd * (100 - self.discount) / 100, 2) if self.usd else None

    def same(self, key: str, stars: int) -> bool:
        return self.key == key and self.stars_price() == stars


class Ad(BaseModel):
    """A short sponsored message shown under the status message while a file downloads."""
    id: str = Field(default_factory=lambda: uid()[:8], pattern=r"^[a-z0-9-]{1,36}$")
    text: str = Field(min_length=1, max_length=300)
    button: str = Field(default="", max_length=40)
    url: str = Field(default="", max_length=300)
    enabled: bool = True
    bots: list[str] = Field(default_factory=list, max_length=10)  # empty = every bot
    languages: list[str] = Field(default_factory=list, max_length=20)  # empty = every language (targeting, no personal data)
    weight: int = Field(default=1, ge=1, le=100)  # how often this ad is chosen compared with the others
    max_views: int = Field(default=0, ge=0, le=100_000_000)  # 0 = no limit; the campaign stops after this many views

    @field_validator("url")
    @classmethod
    def https_only(cls, value):
        value = value.strip()
        if value and not LINK.match(value):
            raise ValueError("the ad link must start with https://")
        return value


def channel_ref(value: str) -> str:
    value = value.strip()
    match = re.match(r"^(?:https?://)?t\.me/([A-Za-z][A-Za-z0-9_]{3,31})/?$", value)
    value = "@" + match.group(1) if match else value
    if value and not CHANNEL.match(value):
        raise ValueError("channel must be @username or a numeric id like -1001234567890")
    return value


class ExtraChannel(BaseModel):
    """One more channel users must join (the owner may require several)."""
    chat: str
    link: str = ""

    @field_validator("chat")
    @classmethod
    def chat_id(cls, value):
        value = channel_ref(value)
        if not value:
            raise ValueError("channel must be @username or a numeric id like -1001234567890")
        return value

    @field_validator("link")
    @classmethod
    def invite(cls, value):
        value = value.strip()
        if value and not LINK.match(value):
            raise ValueError("the channel link must start with https://")
        return value

    @model_validator(mode="after")
    def private_needs_link(self):
        if self.chat.startswith("-100") and not self.link:
            raise ValueError(f"the private channel {self.chat} needs an invite link")
        return self

    def url(self) -> str:
        return self.link or f"https://t.me/{self.chat[1:]}"


class Settings(BaseModel):
    premium_enabled: bool = False
    plans: list[Plan] = Field(default_factory=lambda: [Plan(days=30, stars=100), Plan(days=90, stars=250), Plan(days=365, stars=900)],
                              max_length=8)
    invoice_photo_url: str = ""  # optional picture on the Telegram Stars invoice
    free_max_height: int = Field(default=720, ge=0, le=4320)  # 0 = every quality is free
    free_max_mb: int = Field(default=200, ge=0, le=2000)  # 0 = no extra size limit for free users
    free_storage_mb: int = Field(default=0, ge=0, le=10_000_000)  # File bot storage quota of a free user (0 = none)
    free_platforms: list[str] = Field(default_factory=list, max_length=20)  # platforms for free users; empty = every platform
    tiers: list[Tier] = Field(default_factory=lambda: [Tier()], min_length=1, max_length=6)
    referrals_enabled: bool = False
    referral_invites: int = Field(default=3, ge=1, le=100)
    referral_days: int = Field(default=7, ge=1, le=365)
    referral_credits: int = Field(default=0, ge=0, le=10_000)  # extra downloads given with each reward
    channel_enabled: bool = False
    channel: str = ""
    channel_link: str = ""
    channel_skip_premium: bool = True
    extra_channels: list[ExtraChannel] = Field(default_factory=list, max_length=9)  # more required channels after the first
    ads_enabled: bool = False
    ads_every: int = Field(default=1, ge=1, le=50)  # display frequency: an ad with every N-th download of a user
    ads: list[Ad] = Field(default_factory=list, max_length=20)

    @field_validator("channel")
    @classmethod
    def channel_id(cls, value):
        return channel_ref(value)

    @field_validator("channel_link", "invoice_photo_url")
    @classmethod
    def invite_link(cls, value, info):
        value = value.strip()
        if value and not LINK.match(value):
            raise ValueError(f"the {'channel link' if info.field_name == 'channel_link' else 'invoice picture'} must start with https://")
        return value

    @model_validator(mode="after")
    def complete(self):
        if self.channel_enabled and not self.channel:
            raise ValueError("set the channel before turning the requirement on")
        if self.channel_enabled and self.channel.startswith("-100") and not self.channel_link:
            raise ValueError("a private channel needs an invite link")
        if self.premium_enabled and not any(p.enabled for p in self.plans):
            raise ValueError("add at least one active Premium plan")
        self.tiers = list({t.key: t for t in self.tiers}.values())
        known = {t.key for t in self.tiers}
        if DEFAULT_TIER not in known:
            raise ValueError("the «premium» tier cannot be removed (earlier purchases use it)")
        for plan in self.plans:
            if plan.tier not in known:
                raise ValueError(f"plan for {plan.days} days uses an unknown tier «{plan.tier}»")
        self.plans = sorted({p.key: p for p in self.plans}.values(), key=lambda p: (p.tier != DEFAULT_TIER, p.tier, p.days, p.recurring))
        return self

    def plan(self, key: str) -> Plan | None:
        return next((p for p in self.plans if p.key == key and p.enabled), None)

    def tier(self, key: str | None) -> Tier:
        return next((t for t in self.tiers if t.key == (key or DEFAULT_TIER)), None) or next(t for t in self.tiers if t.key == DEFAULT_TIER)

    @property
    def sells_premium(self) -> bool:
        """Free-tier locks only make sense while Premium can be bought or earned."""
        return self.premium_enabled or self.referrals_enabled

    def channel_url(self) -> str:
        return self.channel_link or (f"https://t.me/{self.channel[1:]}" if self.channel.startswith("@") else "")

    def required_channels(self) -> list[dict]:
        """Every channel a user must join, in order, without duplicates."""
        found = [{"chat": self.channel, "url": self.channel_url()}] if self.channel else []
        for extra in self.extra_channels:
            if extra.chat not in {c["chat"] for c in found}:
                found.append({"chat": extra.chat, "url": extra.url()})
        return found


def settings(db) -> Settings:
    row = db.get(SystemSetting, SETTING_KEY)
    return Settings.model_validate(row.value) if row else Settings()


def save(db, data: Settings) -> Settings:
    db.merge(SystemSetting(key=SETTING_KEY, value=data.model_dump()))
    db.commit()
    return data


# ---------- Premium ----------

def is_premium(user: User | None) -> bool:
    return bool(user and user.premium_until and aware(user.premium_until) > now())


def tier_of(db, user: User | None) -> Tier | None:
    """The paid tier a user is on right now, None for a free user."""
    return settings(db).tier(user.premium_tier) if is_premium(user) else None


def tier_key(plan_key: str) -> str:
    return plan_key.split(".", 1)[0] if "." in plan_key else DEFAULT_TIER


def grant(db, user: User, days: int, source: str, stars: int = 0, bot_id: str | None = None,
          charge_id: str | None = None, tier: str = DEFAULT_TIER) -> datetime:
    """Extend Premium by `days` from today or from the current end date, and record why. Idempotent per charge.
    A purchase of another tier switches the user to it (the remaining days carry over)."""
    if charge_id and db.scalar(select(Payment).where(Payment.charge_id == charge_id)):
        return aware(user.premium_until)
    start = max(now(), aware(user.premium_until) or now())
    user.premium_until = start + timedelta(days=days)
    user.premium_tier = tier or DEFAULT_TIER
    db.add(Payment(user_id=user.id, bot_id=bot_id, source=source, stars=stars, days=days, charge_id=charge_id))
    db.commit()
    return aware(user.premium_until)


def revoke(db, user: User) -> None:
    user.premium_until = None
    db.commit()


def take_back(db, user: User | None, days: int) -> None:
    """After a refund: remove the purchased days (Premium ends now if nothing else is left)."""
    if not user or not user.premium_until:
        return
    left = aware(user.premium_until) - timedelta(days=days)
    user.premium_until = left if left > now() else None
    db.commit()


PAYLOAD = re.compile(rf"{INVOICE_PREFIX}:((?:[a-z0-9_-]{{1,24}}\.)?)(\d{{1,4}})(r?):(\d{{1,5}})")


def invoice_payload(plan: Plan) -> str:
    """Premium:<key>:<stars>, e.g. premium:30r:100 for a monthly Telegram subscription, premium:gold.30:500 for a tier."""
    return f"{INVOICE_PREFIX}:{plan.key}:{plan.stars_price()}"


def checkout_plan(db, payload: str, amount: int) -> Plan:
    """Validate an invoice before Telegram charges the user: it must match a plan on sale right now, at today's price."""
    from backend.services import billing  # billing builds on this module
    match = PAYLOAD.fullmatch(payload or "")
    m = settings(db)
    if not match or not m.premium_enabled or not billing.load(db).stars_enabled:
        raise DomainError("premium_unavailable")
    key, stars = match.group(1) + match.group(2) + match.group(3), int(match.group(4))
    plan = m.plan(key)
    if not plan or not plan.same(key, stars) or stars != amount:
        raise DomainError("premium_unavailable")
    return plan


def paid_plan(payload: str, amount: int) -> Plan:
    """Plan of a completed payment (also every renewal of a subscription). Telegram already charged the user,
    so a later price change or a plan switched off never cancels days that were paid for."""
    match = PAYLOAD.fullmatch(payload or "")
    if not match or int(match.group(4)) != amount:
        raise DomainError("failed")
    return Plan(tier=match.group(1).rstrip(".") or DEFAULT_TIER, days=int(match.group(2)), stars=amount, recurring=bool(match.group(3)))


def download_limit(db, user: User | None, policy: Policy) -> int:
    """Largest file this user may download: the tier's limit for paying users, the free-tier limit otherwise."""
    m = settings(db)
    tier = tier_of(db, user)
    if tier is not None:
        return min(policy.max_download_bytes, tier.max_mb * 1_000_000) if tier.max_mb else policy.max_download_bytes
    if not m.sells_premium or not m.free_max_mb:
        return policy.max_download_bytes
    return min(policy.max_download_bytes, m.free_max_mb * 1_000_000)


def format_lock(db, user: User | None, fmt: dict) -> str | None:
    """'premium_quality' / 'premium_size' when the user's plan does not include this format, otherwise None."""
    m = settings(db)
    tier = tier_of(db, user)
    if tier is None and not m.sells_premium:
        return None
    max_height = tier.max_height if tier else m.free_max_height
    max_mb = tier.max_mb if tier else m.free_max_mb
    if max_height and fmt.get("kind") == "video" and (fmt.get("height") or 0) > max_height:
        return "premium_quality"
    if max_mb and (fmt.get("size") or 0) > max_mb * 1_000_000:
        return "premium_size"
    return None


def daily_limit(db, user: User, free_limit: int) -> int:
    """Downloads and uploads per day: the tier's limit (0 = unlimited) for paying users, else the free limit."""
    tier = tier_of(db, user)
    if tier is not None:
        return tier.daily_jobs or 0
    return free_limit


def platform_allowed(db, user: User | None, platform: str) -> bool:
    """Whether the user's plan includes this platform."""
    m, tier = settings(db), tier_of(db, user)
    included = tier.platforms if tier else m.free_platforms
    return not included or platform in included


def storage_quota(db, user: User | None) -> int:
    """Bytes of files this user may keep in the File bot at once; 0 = no quota."""
    tier = tier_of(db, user)
    mb = tier.storage_mb if tier else settings(db).free_storage_mb
    return mb * 1_000_000


def locked_formats(db, user: User | None, formats: list[dict]) -> set[int]:
    return {i for i, f in enumerate(formats) if format_lock(db, user, f)}


# ---------- Referrals ----------

def link_referrer(db, user: User, referrer_id: int | None) -> None:
    """Remember who invited a brand-new user (never yourself, never an unknown account)."""
    if not referrer_id or referrer_id == user.id or user.referred_by or not settings(db).referrals_enabled:
        return
    if db.get(User, referrer_id):
        user.referred_by = referrer_id


def referral_count(db, referrer_id: int) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.referred_by == referrer_id, User.referral_counted.is_(True)))


def count_referral(db, user_id: int) -> dict | None:
    """After an invited user's first successful download: count the invite and reward every N invites."""
    m = settings(db)
    user = db.get(User, user_id)
    if not m.referrals_enabled or not user or not user.referred_by or user.referral_counted:
        return None
    referrer = db.get(User, user.referred_by)
    user.referral_counted = True
    db.commit()
    if not referrer or referrer.banned:
        return None
    count = referral_count(db, referrer.id)
    rewarded = count % m.referral_invites == 0
    if rewarded and m.referral_credits:
        referrer.credits = (referrer.credits or 0) + m.referral_credits
    until = grant(db, referrer, m.referral_days, "referral") if rewarded else None
    return {"referrer": referrer.id, "count": count, "needed": m.referral_invites, "rewarded": rewarded,
            "days": m.referral_days, "until": until.isoformat() if until else None}


# ---------- Sponsored messages ----------

AD_CLICKS_KEY = "ads:clicks"


def pick_ad(db, user: User | None, job_id: str, bot_id: str | None = None, language: str | None = None) -> dict | None:
    """The sponsored message for one download (kept for its retries), or None.

    Premium users never see ads. An ad runs only in its bots and languages, until its view limit; the display
    frequency shows one with every N-th download of a user; among the matching ads the weights decide. Each pick is
    one view; the button opens our /go/ link, which counts the click before forwarding to the advertiser.
    """
    m = settings(db)
    tier = tier_of(db, user)
    if not m.ads_enabled or (tier is not None and tier.no_ads):
        return None
    views = ad_views()
    ads = [a for a in m.ads if a.enabled and (not a.bots or bot_id in a.bots) and (not a.languages or language in a.languages)
           and (not a.max_views or views.get(a.id, 0) < a.max_views)]
    if not ads:
        return None
    redis = limits.redis_client()
    try:
        if user is not None and m.ads_every > 1 and (redis.incr(f"ads:seen:{user.id}") - 1) % m.ads_every:
            return None
    except Exception:
        pass
    spot = int(hashlib.sha256(job_id.encode()).hexdigest(), 16) % sum(a.weight for a in ads)
    for ad in ads:
        spot -= ad.weight
        if spot < 0:
            break
    try:
        redis.hincrby(AD_VIEWS_KEY, ad.id, 1)
        if bot_id:
            redis.hincrby(f"{AD_VIEWS_KEY}:{bot_id}", ad.id, 1)
    except Exception:
        pass  # statistics only: never block a download because Redis is busy
    result = ad.model_dump(include={"id", "text", "button", "url"})
    if ad.url:
        from backend.services import billing
        result["url"] = f"{billing.public_base(db)}/go/{ad.id}/{job_id}"
    return result


def ad_click(db, ad_id: str, job_id: str) -> str | None:
    """Counts a click (once per download) and returns the advertiser's address, or None for an unknown ad."""
    ad = next((a for a in settings(db).ads if a.id == ad_id and a.url), None)
    if not ad:
        return None
    try:
        redis = limits.redis_client()
        if redis.set(f"ads:clicked:{ad_id}:{job_id[:40]}", "1", nx=True, ex=90 * 86400):
            redis.hincrby(AD_CLICKS_KEY, ad.id, 1)
    except Exception:
        pass
    return ad.url


def _counts(key: str) -> dict[str, int]:
    try:
        return {k: int(v) for k, v in limits.redis_client().hgetall(key).items()}
    except Exception:
        return {}


def ad_views() -> dict[str, int]:
    return _counts(AD_VIEWS_KEY)


def ad_clicks() -> dict[str, int]:
    return _counts(AD_CLICKS_KEY)


def ad_report(m: Settings) -> list[dict]:
    """Impressions, clicks and click-through rate per ad (and impressions per bot) for the dashboard."""
    views, clicks = ad_views(), ad_clicks()
    per_bot = {bot: _counts(f"{AD_VIEWS_KEY}:{bot}") for bot in BOT_KINDS}
    return [{"id": a.id, "text": a.text[:60], "views": views.get(a.id, 0), "clicks": clicks.get(a.id, 0),
             "ctr": round(100 * clicks.get(a.id, 0) / views[a.id], 2) if views.get(a.id) else 0.0,
             "by_bot": {bot: counts.get(a.id, 0) for bot, counts in per_bot.items() if counts.get(a.id)}} for a in m.ads]


# ---------- What the bots need to know ----------

def offers(db, m: Settings) -> list[dict]:
    """Plans as the bot shows them: Stars price (if Stars is on) and the card/crypto methods of the payment page."""
    from backend.services import billing
    if not m.premium_enabled:
        return []
    stars = billing.load(db).stars_enabled
    result = []
    for plan in m.plans:
        if not plan.enabled or (plan.recurring and not stars):
            continue
        page = [] if plan.recurring else billing.page_methods(db, plan)  # subscriptions renew in Telegram Stars only
        if stars or page:
            result.append({"key": plan.key, "tier": plan.tier, "tier_name": m.tier(plan.tier).name,
                           "days": plan.days, "recurring": plan.recurring, "title": plan.title, "badge": plan.badge,
                           "discount": plan.discount, "stars": plan.stars_price(), "stars_full": plan.stars, "usd": plan.usd_price(),
                           "stars_ok": stars, "page": page})
    return result


def profile(db, user: User, daily_limit: int, used_today: int) -> dict:
    m = settings(db)
    premium = is_premium(user)
    channel = m.channel if m.channel_enabled and not (premium and m.channel_skip_premium) else None
    return {
        "premium": premium, "premium_until": aware(user.premium_until).isoformat() if premium else None,
        "tier": m.tier(user.premium_tier).name if premium else None, "credits": user.credits or 0,
        "sells_premium": m.sells_premium, "plans": offers(db, m), "invoice_photo": m.invoice_photo_url or None,
        "used_today": used_today, "daily_limit": daily_limit,
        "free_max_height": m.free_max_height if m.sells_premium else 0,
        "free_max_mb": m.free_max_mb if m.sells_premium else 0, "ads": m.ads_enabled,
        "referrals": {"invites": m.referral_invites, "days": m.referral_days, "count": referral_count(db, user.id)}
        if m.referrals_enabled else None,
        "channel": {"chat": channel, "url": m.channel_url()} if channel else None,
        "channels": m.required_channels() if channel else [],
    }


def stats(db) -> dict:
    month_ago = now() - timedelta(days=30)
    stars = lambda *where: db.scalar(select(func.coalesce(func.sum(Payment.stars), 0)).where(Payment.source == "stars", *where))
    purchases = lambda *where: db.scalar(select(func.count()).select_from(Payment).where(Payment.source == "stars", *where))
    return {
        "stars_total": stars(), "stars_30d": stars(Payment.created_at >= month_ago),
        "purchases_total": purchases(), "purchases_30d": purchases(Payment.created_at >= month_ago),
        "premium_users": db.scalar(select(func.count()).select_from(User).where(User.premium_until > now())),
        "referral_rewards": db.scalar(select(func.count()).select_from(Payment).where(Payment.source == "referral")),
        "invited_users": db.scalar(select(func.count()).select_from(User).where(User.referral_counted.is_(True))),
        "ad_views": ad_views(), "ad_clicks": ad_clicks(), "ads": ad_report(settings(db)),
    }
