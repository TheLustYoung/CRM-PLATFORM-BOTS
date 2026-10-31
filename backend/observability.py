"""Error tracking: with SENTRY_DSN set in .env, unhandled errors of the API, the workers and the bots are
reported to Sentry (or a self-hosted, Sentry-compatible service such as GlitchTip). Without it nothing is sent.

Reports never include personal data or secrets: request bodies, cookies and user details are not attached
(send_default_pii=False), and bot tokens are removed from any text before sending.
"""
import logging
import re
from backend.config import settings

TOKEN = re.compile(r"\d{5,15}:[A-Za-z0-9_-]{30,64}")
_started = False


def _scrub(event, _hint):
    """Removes bot tokens from messages and exception values."""
    def clean(value):
        if isinstance(value, str):
            return TOKEN.sub("[token]", value)
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value
    return clean(event)


def setup(service: str) -> bool:
    """Starts error reporting for one service (api, worker, bot-media, ...); False when no DSN is configured."""
    global _started
    dsn = settings().sentry_dsn.get_secret_value()
    if not dsn or _started:
        return _started
    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger("observability").warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False
    sentry_sdk.init(dsn=dsn, environment=settings().environment, server_name=service, send_default_pii=False,
                    traces_sample_rate=0.0, before_send=_scrub, http_proxy=settings().egress_proxy or None,
                    https_proxy=settings().egress_proxy or None)
    sentry_sdk.set_tag("service", service)
    _started = True
    return True
