"""Bot tokens set in the dashboard.

A token saved in the dashboard is checked with Telegram (getMe), stored encrypted and takes priority over the one in
.env; removing it brings the .env token back. The bot notices the change with its next heartbeat and restarts itself
with the new token (Docker starts it again), so the other bots keep running.
"""
import hashlib
import re
import time
import httpx
from backend.models import SystemSetting

TOKEN = re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{30,64}$")
REFRESH_SECONDS = 30
_cache: dict[str, tuple[float, str | None]] = {}


def _key(kind: str) -> str:
    return f"bot_token:{kind}"


def stored(db, kind: str) -> str | None:
    from backend.services.security import decrypt
    row = db.get(SystemSetting, _key(kind))
    return decrypt(row.value.get("token")) if row else None


def override(kind: str) -> str | None:
    """The dashboard's token for a bot (cached 30 s), None when it has none or the database is not reachable."""
    cached = _cache.get(kind)
    if cached and time.monotonic() - cached[0] < REFRESH_SECONDS:
        return cached[1]
    try:
        from backend.database import Session
        with Session() as db:
            value = stored(db, kind)
    except Exception:
        value = cached[1] if cached else None
    _cache[kind] = (time.monotonic(), value)
    return value


def fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:12] if token else ""


def check(token: str) -> dict:
    """Telegram's getMe for the token: {"username", "id"}; ValueError when Telegram refuses it."""
    from backend.config import settings
    token = token.strip()
    if not TOKEN.match(token):
        raise ValueError("This is not a bot token (format 123456789:AA…).")
    try:
        with httpx.Client(timeout=15, proxy=None) as http:
            answer = http.get(f"https://api.telegram.org/bot{token}/getMe").json()
    except (httpx.HTTPError, ValueError):
        raise ValueError("Telegram could not be reached. Try again in a minute.") from None
    if not answer.get("ok"):
        raise ValueError("Telegram does not accept this token. Copy it again from @BotFather.")
    me = answer["result"]
    return {"id": me.get("id"), "username": me.get("username")}


def save(db, kind: str, token: str) -> dict:
    from backend.services.security import encrypt
    me = check(token)
    db.merge(SystemSetting(key=_key(kind), value={"token": encrypt(token.strip()), "username": me["username"]}))
    db.commit()
    _cache.pop(kind, None)
    return me


def remove(db, kind: str) -> None:
    row = db.get(SystemSetting, _key(kind))
    if row:
        db.delete(row)
        db.commit()
    _cache.pop(kind, None)


def source(db, kind: str, env_token: str) -> str:
    """Where the bot's token comes from: dashboard, env or none."""
    return "dashboard" if stored(db, kind) else "env" if env_token else "none"
