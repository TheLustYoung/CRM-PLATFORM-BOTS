# API

Interactive OpenAPI documentation: `/api/docs` (through the dashboard or localhost).

## Admin dashboard: `/api/admin/*`, `/api/auth/*`

Authentication: `POST /api/auth/login` sets an HttpOnly `session` cookie for 8 hours. State-changing requests must send an
`Origin` header equal to `ADMIN_ORIGIN`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/overview` | counters, 7-day activity, jobs per bot |
| GET / PATCH | `/api/admin/bots`, `/api/admin/bots/{id}` | bots (online, users, jobs today); `{enabled, daily_limit, welcome_text}` |
| GET / PUT | `/api/admin/bots/{id}/profile?lang=` | bot appearance in Telegram: `{name, short_description, description, commands[]}`; empty `lang` = all languages, or `en`/`ar`/`he`. Only changed fields are sent (Telegram rate-limits `setMyName`) |
| GET / POST / DELETE | `/api/admin/bots/{id}/photo` | current profile photo / upload JPEG or PNG up to 10 MB (multipart `file`) / remove |
| GET | `/api/admin/users?q=&offset=` | search by Telegram ID or username |
| GET / PATCH | `/api/admin/users/{id}` | details; `{banned, daily_limit}` |
| GET | `/api/admin/jobs?user_id=&status=&bot_id=` | job history |
| GET | `/api/admin/jobs/{id}` | one job for the View window: link, post details, stored files, user (never provider media URLs) |
| GET | `/api/admin/files?user_id=` | files with public links |
| GET | `/api/admin/files/{id}/content?download=` | the file itself: shown inline for safe types (images, video, audio, PDF, text), otherwise and with `download=1` as an attachment |
| POST / DELETE | `/api/admin/files/{id}/revoke`, `/api/admin/files/{id}` | revoke link / delete file |
| GET / PATCH | `/api/admin/settings` | limits, retention, platforms, default language |
| GET | `/api/admin/compatibility`, `/api/admin/audit` | platform compatibility, audit log |
| GET / PUT / DELETE | `/api/admin/bots/{id}/token` | where the bot token comes from (never the token) / set a token (checked with Telegram, encrypted) / back to `.env` |
| POST | `/api/admin/users/{id}/premium` | `{days, tier}`: gift a tier for N days (0 removes Premium); user details also list payments, tier and credits; PATCH `{credits}` |
| POST | `/api/admin/files/{id}/keep` | `{days}`: extend a public file, `0` = permanent |
| GET | `/api/admin/analytics?period=day\|week\|month&count=&bot=` | reports (rules in `backend/services/analytics.py`); `/api/admin/analytics.csv` exports them |
| GET / PUT / POST | `/api/admin/translations`, `/api/admin/translations/{lang}`, `/api/admin/translations/{lang}/enable\|disable` | languages, texts of a language, saving edits `{texts: {key: text}}`, switching a language |
| GET / PUT / POST | `/api/admin/monitoring`, `/api/admin/monitoring/check` | monitoring status and alert settings; run the checks now and send a test alert |
| GET / PUT | `/api/admin/monetization`, `/api/admin/monetization/stats` | tiers, plans, free tier, referrals, required channel, ads (bots, languages, weight, view limit, frequency); views, clicks, CTR |
| POST | `/api/admin/proxies/{group}/{number}` | `{action: on\|off\|only\|reset}`: switch one proxy on or off, use only this one, or clear its failure mark |
| GET / PUT | `/api/admin/channel` | the bots' public channel: settings `{chat, bot}`, live info (title, subscribers, bot rights), posts |
| POST | `/api/admin/channel/posts` | multipart `text, buttons (JSON), publish_at (ISO, empty = now), media (photo or MP4)` |
| POST | `/api/admin/channel/posts/{id}/edit\|publish\|pin\|delete` | edit text and buttons (also in Telegram), publish now, `{pin: bool}`, delete from the channel |
| GET / PUT / POST | `/api/admin/payments`, `/orders`, `/revenue`, `/orders/{id}/refund` | payment providers, transactions, revenue, refunds |
| GET / POST | `/api/admin/broadcasts`, `/audience`, `/test`, `/{id}/delete` | broadcasts to the bots' users |
| * | `/api/admin/team/accounts`, `/api/admin/team/roles` | administrators and roles (permissions) |

## Bots: `/internal/*`

Headers `X-Bot-Kind: video|media|files` and `X-Service-Key`. Blocked in Plesk (`return 404`).
Endpoints: `register`, `language`, `metadata`, `download`, `upload`, `jobs/{id}/refresh`, `jobs/{id}/info`,
`jobs/{id}/cancel`, `files`, `files/{id}/revoke`, `files/{id}/delete`, `history`, `premium/checkout`, `premium/activate`,
`premium/order`, `heartbeat` (returns the
dashboard's translation edits and the token fingerprint). Errors are `{"detail": "<code>"}`; the code equals a translation key
(`rate_limit`, `invalid_url`, `unsupported`, ...).

## Public

`GET /f/{token}` — file page (name, size, type, dates, `@bot`) in the browser's language.
`GET /f/{token}/download` — direct download. `GET /health/live`, `GET /health/ready` — health checks.
`GET /pay/{token}` — payment page (cards, crypto); `POST /webhooks/{provider}` — signed provider webhooks.
`GET /go/{ad}/{job}` — sponsored-message button: counts the click, then redirects to the advertiser.
