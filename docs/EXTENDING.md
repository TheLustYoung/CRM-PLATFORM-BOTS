# Extending the platform

## A new language
1. Copy `backend/services/locales/en.json` to `<code>.json` and translate the values.
   In `_meta` set `name`, and `"rtl": true` for Arabic, Hebrew, etc.
2. Restart api, worker and bots. The language appears in `/language`, in the dashboard settings and on file pages.
   `tests/unit/test_i18n.py` checks that every key is present.
3. For the dashboard interface itself, add a dictionary in `dashboard/src/services/i18n.ts`.

## A new bot
1. Add the kind to `BOT_KINDS` (`backend/config.py`) and `<kind>_bot_token` / `<kind>_service_key` fields to `Settings`.
2. Create `bots/<kind>/__init__.py` with `setup(router, ctx)` and `__main__.py` calling `run("<kind>", setup)`.
3. Add a service to `docker-compose.yml`, run `python -m backend.cli seed`. The bot appears in the dashboard.

## A new source
Sources are deliberately limited to sites whose content may be downloaded (see [LEGAL.md](LEGAL.md)).
To add one, for example another open media library:
1. Add it to `PLATFORMS` (`backend/services/platforms.py`) with its yt-dlp extractor keys and host names, and to
   `PlatformName` (`backend/services/limits.py`).
2. Add its title to `TITLES` and to `dashboard/src/services/sources.ts`.
3. Run `seed` and confirm the status with `python -m workers.verify` on real links.

## A new payment method
Payment providers are modules in `backend/services/payments/` (see `stripe.py`, `cryptobot.py`): `checkout()` creates
the provider payment for an order, `verify()` checks the webhook signature, `refund()` returns money. Register the
module in the catalog of `backend/services/payments/__init__.py`; the payment page, the Payments page, refunds and
reports pick it up. Premium is granted only from a verified webhook, once per transaction (see docs/PAYMENTS.md).

## Plans, tiers and limits
Tiers, plans, the free tier, referrals and ads are configured in the dashboard (Monetization). Every job passes through
`jobs.new_job`, where the tier's limits and credits are applied; formats are checked in `monetization.format_lock`.

## Texts and languages without code
Settings → Translations edits any text in any language and switches languages on or off. A language that has no file
yet is added as `backend/services/locales/<code>.json` (copy `en.json`), after which it can be edited in the dashboard.

