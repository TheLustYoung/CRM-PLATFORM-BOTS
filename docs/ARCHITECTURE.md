# Architecture

```
Telegram ──► video-bot   ┐
Telegram ──► media-bot   ├─► API (FastAPI) ──► PostgreSQL
Telegram ──► files-bot   ┘        │  └────────► Redis (queue, rate limits, locks)
                                  ▼
                          Celery worker ──► egress proxy ──► Wikimedia Commons / Internet Archive / direct files / Telegram
                                  │
                                  ▼
                          Storage: MinIO/S3 (private) or disk ──► /f/<token> via the API (Plesk: files.<domain>)
Admin dashboard (React) ──► /api/admin/* (cookie session, Origin check) ──► Telegram Bot API (bot appearance)
```

**Principles**

- **Thin bots.** Bots hold no business logic: every action goes to `/internal/*` with that bot's own service key.
  A new bot is a new folder in `bots/` plus an entry in `BOT_KINDS`; the core does not change.
- **Shared users.** One `users` row per Telegram account, linked to bots through `bot_users`.
  The language lives in `user_preferences` and applies to every bot.
- **Idempotency.** A job is unique per `(user, bot, request_key)`. Repeated messages or button presses return the same job,
  so nothing is downloaded or sent twice.
- **Reliable queue.** A job is first stored in the database as `queued`, then sent to Celery. The `reconcile` task re-queues
  lost jobs and recovers stuck ones every minute. Temporary network errors are retried up to 3 times.
- **Licensed sources only.** `backend/services/platforms.py` accepts Wikimedia Commons, the Internet Archive and
  direct media-file links; each source is limited to its own yt-dlp extractor. See [LEGAL.md](LEGAL.md).
- **Fault isolation.** A source failure affects only its own job: the user gets a clear message in their language,
  other jobs and bots keep working.
- **Storage.** Never public. Links are served by the API, which checks expiry and revocation. Files are served as
  attachments, so uploaded HTML/SVG never executes on your domain. Size and SHA-256 are recorded after upload.
  The provider is switched with `STORAGE_BACKEND` (`s3` or `local`).
- **Security.** SSRF protection (only public IPs, egress proxy pins the IP after the DNS check), Argon2 passwords,
  HttpOnly session cookie, Origin check for admin requests, tokens only in the environment and never in logs.

## Data

| Tables | Purpose |
|---|---|
| users, bot_users, user_preferences | shared users, bot membership, language |
| bots | bot: enabled, daily limit, custom welcome text, username, heartbeat |
| download_jobs, usage_records | jobs (metadata/download/upload), usage for limits and bytes |
| uploaded_files, public_file_links | stored files, public link tokens, revocation, expiry, download counter |
| admin_users, audit_logs, system_settings | administrators, audit log, settings edited in the dashboard |
| platform_compatibility | measured source status (NOT VERIFIED → VERIFIED / PARTIAL / ...) |

Bot appearance (name, descriptions, commands, photo) is not stored in the database: Telegram is the source of truth and the
dashboard reads and writes it through the Bot API. Bots fill in default texts on startup only where Telegram has none.

## Localization

`backend/services/locales/<code>.json`: keys and texts, plus `_meta` with the language name and an RTL flag.
The user's language is detected from Telegram's `language_code` (e.g. `ar-SA` → `ar`) and changed with `/language`.
Missing keys fall back to English; RTL texts get an RLM mark. The public file page picks the language from
`Accept-Language` or `?lang=`. The dashboard has its own en/ar/he dictionaries in `dashboard/src/services/`.
