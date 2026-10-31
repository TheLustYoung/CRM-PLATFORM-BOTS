# Installation, deployment and operation guide

This guide covers everything needed to run the Telegram Media Platform:
**A.** production deployment on a dedicated server with Plesk and Docker Compose, **B.** day-to-day operation,
**C.** running it locally for development and testing.

---

## 0. What runs where

| Service (docker-compose) | Purpose | Port |
|---|---|---|
| `postgres` | PostgreSQL 16, the shared database | internal only |
| `redis` | job queue, locks, rate limits | internal only |
| `minio` | optional S3-compatible file storage (profile `minio`; files are on the server disk by default) | internal only |
| `migrate` | one-shot: database migrations + initial data | — |
| `api` | FastAPI backend: admin API, bot API, public file links | `127.0.0.1:8000` |
| `worker` | Celery workers: metadata, downloads, uploads, delivery | — |
| `beat` | Celery scheduler: lost-job recovery, file retention cleanup | — |
| `egress` | outbound proxy for workers (blocks access to internal addresses) | internal only |
| `video-bot`, `media-bot`, `files-bot` | the three Telegram bots (long polling) | — |
| `dashboard` | React admin panel served by nginx | `127.0.0.1:8080` |

Only `api` and `dashboard` listen on the server, and only on `127.0.0.1`. Plesk publishes them over HTTPS:

| Public address (example) | Plesk proxies to | Used for |
|---|---|---|
| `https://admin.example.com` | `127.0.0.1:8080` | admin panel (it calls the API itself via `/api`) |
| `https://files.example.com` | `127.0.0.1:8000`, path `/f/` only | public download links sent by the bots |
| `https://api.example.com` (optional) | `127.0.0.1:8000`, `/internal` and `/api/admin` blocked | health checks / future integrations |

---

## A. Production deployment

### A1. Requirements

- A dedicated server or VPS: Ubuntu 22.04/24.04 or Debian 12, **4 CPU, 8 GB RAM, 50 GB+ free disk**
  (downloads and stored files use disk; plan more if you keep large files for long).
- Plesk Obsidian (for domains and SSL). Without Plesk, any nginx + certbot setup works the same way.
- Docker Engine 24+ with the Compose v2 plugin (`docker compose version`).
- A domain where you can create DNS records.
- Three Telegram bots created in @BotFather (A2).

### A2. Create the bots in @BotFather

For each of the three bots (Video, Media, File Sharing):
1. Open @BotFather → `/newbot` → enter a display name and a username ending in `bot`.
2. Copy the token (`123456789:AA...`). Keep it secret: anyone with the token controls the bot.
3. Optional: `/setprivacy` is not needed (bots work in private chats only).

The bot's name, photo, descriptions and menu commands can later be changed from the admin panel
(Bots → 🎨 Appearance). Only the @username must be changed in @BotFather.

### A3. DNS

Create `A` records pointing to the server IP: `admin`, `files` (and optionally `api`).
Add `AAAA` records only if the server has working IPv6.

### A4. Install Docker

If Docker is not installed (Plesk's Docker extension is not required):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker compose version
```

### A5. Get the code

```bash
sudo mkdir -p /opt/telegram-media && sudo chown "$USER" /opt/telegram-media
cd /opt/telegram-media
git clone <repository-url> .        # or: unzip telegram-media-platform.zip -d . (archive root = project root)
```

Keep the project **outside** any website `httpdocs` directory.

### A6. Configure `.env`

```bash
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_hex(32))'   # run once per secret below
nano .env
```

| Variable | What to put |
|---|---|
| `POSTGRES_PASSWORD` | a generated secret |
| `DATABASE_URL` | `postgresql+psycopg://media:<POSTGRES_PASSWORD>@postgres:5432/media` — **same password** as above (hex secrets need no URL escaping) |
| `JWT_SECRET` | a generated secret (admin sessions) |
| `VIDEO_BOT_TOKEN`, `MEDIA_BOT_TOKEN`, `FILES_BOT_TOKEN` | tokens from @BotFather |
| `VIDEO_SERVICE_KEY`, `MEDIA_SERVICE_KEY`, `FILES_SERVICE_KEY` | three different generated secrets (bot ↔ backend authentication) |
| `ADMIN_ORIGIN` | exact admin URL, e.g. `https://admin.example.com` (no trailing `/`) |
| `PUBLIC_FILES_URL` | e.g. `https://files.example.com` — used in links sent to users |
| `S3_SECRET_KEY` | a generated secret (MinIO password) |
| `API_PORT`, `DASHBOARD_PORT` | localhost ports for Plesk, default `8000` / `8080`; change them if another application already uses these ports (check with `sudo ss -ltnp 'sport = :8000 or sport = :8080'`) and use the same ports in the Plesk snippets |
| `DEFAULT_LANGUAGE` | `en`, `ar` or `he` — for users whose Telegram language is not supported |
| Limits (`DAILY_JOBS`, `MAX_DOWNLOAD_BYTES`, `RETENTION_DAYS`, ...) | defaults are sensible; they can also be changed later in the admin panel (Settings) |

The application refuses to start while any `CHANGE_ME` value is left. Never commit or share `.env`.

**Storage choice.** By default files are stored on the server disk (`STORAGE_BACKEND=local`, Docker volume `files-data`).
To use an S3-compatible service (AWS S3, Cloudflare R2, Backblaze B2), set `STORAGE_BACKEND=s3` and `S3_ENDPOINT`,
`S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION`. The bundled MinIO is optional: start it with
`docker compose --profile minio up -d` (MinIO no longer publishes public Docker images, so this needs an image you can pull).

### A7. Build and start

```bash
docker compose config --quiet                         # validates the file (prints nothing if OK)
docker compose build
docker compose up -d postgres redis
docker compose run --rm migrate                       # migrations + bots + platform list + storage bucket
docker compose run --rm api python -m backend.cli create-admin   # the owner; asks username and password (12+ chars). Others: dashboard → Team
docker compose up -d
docker compose ps                                     # all services "running" / "healthy"
curl --fail http://127.0.0.1:8000/health/ready        # {"status":"ok","database":"ok","redis":"ok","storage":"ok"}
```

Bots need about a minute to report as healthy (they send a heartbeat every 30 s).

### A8. Plesk: subdomains, SSL, proxy

1. **Websites & Domains → Add Subdomain**: `admin`, `files` (and `api` if used).
2. For each subdomain: **SSL/TLS Certificates → Let's Encrypt**, enable **Redirect from HTTP to HTTPS**.
3. **Apache & nginx Settings → Additional nginx directives**, paste the matching snippet from
   `infrastructure/plesk/`:
   - `admin` → `admin.nginx.conf` (proxy to `127.0.0.1:8080`, 12 MB upload limit for bot photos)
   - `files` → `files.nginx.conf` (only `/f/` is proxied, everything else returns 404)
   - `api` → `api.nginx.conf` (`/internal/`, `/api/admin/`, `/api/auth/` are blocked)
4. If Plesk shows "duplicate location", disable **Proxy mode** for that subdomain in the same settings page
   (or use Docker Proxy Rules instead of the snippets — not both). More detail: [PLESK.md](PLESK.md).

### A9. Acceptance check

1. Open `https://admin.example.com`, sign in. **Bots** page: all three bots *Enabled* and *Online*.
2. In Telegram, send `/start` to each bot. The language follows your Telegram app; `/language` changes it.
3. Video bot: send an Internet Archive or Wikimedia Commons video link → card with formats and the licence → press a format → the file (or a link if > 49 MB) arrives,
   signed with the bot's @username.
4. File bot: send a document → open the received link **from another device's browser** → download works.
5. Admin panel: the user, jobs and file appear; revoke the file link → the link stops working.
6. Record real platform status (shown in the admin overview):

```bash
docker compose exec worker python -m workers.verify \
  --case archive video https://archive.org/details/<item> \
  --case wikimedia image https://commons.wikimedia.org/wiki/File:<name>.jpg \
  --case direct video https://<host>/<file>.mp4
```

---

## B. Operation

### B1. Everyday commands

```bash
docker compose ps
docker compose logs --tail=100 -f api worker video-bot media-bot files-bot
docker compose restart media-bot
docker compose exec api alembic current
```

Logs never contain bot tokens. Do not enable debug/verbose logging of HTTP clients: Telegram URLs embed tokens.

### B2. Updating

```bash
cd /opt/telegram-media
# back up first (B4)
git pull                     # or unpack the new archive over the project, keeping .env
docker compose build
docker compose run --rm migrate
docker compose up -d
```

yt-dlp is updated by rebuilding the image (`docker compose build --no-cache worker` then `up -d`).
Sites change often; rebuild every few weeks or when a platform stops working, then re-run `workers.verify`.

### B3. Scaling and limits

- More parallel downloads: set `WORKER_CONCURRENCY` (default 2) or run more workers:
  `docker compose up -d --scale worker=3`. Each download job may use up to ~1.5 GB of temporary space.
- Per-user and per-bot daily limits, maximum sizes, retention and enabled platforms: admin panel → Settings / Bots.
- Telegram limits: bots send files up to 50 MB (larger results are delivered as links) and receive uploads up to 20 MB
  through the standard cloud Bot API.

### B4. Backups

Back up PostgreSQL **and** the file storage together, plus `.env` (separately, encrypted).
Step-by-step commands and restore procedure: [BACKUPS.md](BACKUPS.md). Redis does not need backups.

### B5. Rotating a bot token

Revoke the token in @BotFather (`/revoke`), put the new one into `.env`, then
`docker compose up -d --force-recreate api worker video-bot media-bot files-bot`.

### B6. Troubleshooting

| Symptom | Check |
|---|---|
| A service keeps restarting | `docker compose logs <service>`; a `CHANGE_ME` left in `.env`; `DATABASE_URL` password ≠ `POSTGRES_PASSWORD` |
| Bot shows *Offline* in the panel | its token in `.env`; `docker compose logs <bot>`; only one process may poll a token (stop local test copies) |
| Admin login returns 403 | `ADMIN_ORIGIN` must exactly match the address in the browser (scheme + host, no `/`) |
| Download links return 404 | link revoked/expired, or `PUBLIC_FILES_URL` does not match the `files` subdomain |
| A platform stopped working | rebuild to update yt-dlp (B2), then `workers.verify`; some content is private or login-only by design |
| Photo upload in Appearance fails with 413 | the Plesk `admin` snippet must include `client_max_body_size 12m` |

---

### B7. Logging, monitoring and error reporting

| What | Where it is configured | Where you see it |
|---|---|---|
| Logs | Structured JSON lines from every service (`docker-compose.yml` keeps them with Docker's log rotation) | `docker compose logs -f <service>` |
| Monitoring | Settings → Monitoring: disk minimum, failed-download rate, queue wait, silent bots (task `workers.monitor.check`, every 5 minutes) | The Monitoring card; alerts at most once an hour per problem |
| Alerts | Settings → Monitoring: Telegram chat ID and e-mail (SendGrid or Resend API key, stored encrypted) | Telegram chat / mailbox; «Check now» sends a test alert |
| Proxy alerts | Automatic: a failing proxy is skipped for 10 minutes and reported once | Settings → proxies (red lamp with the reason) |
| Error tracking | `SENTRY_DSN=` in `.env` (optional, `ENVIRONMENT=production`); bot tokens are removed from every report, no personal data is sent | Your Sentry project |
| Error statistics | Built in | Reports: error rate, top errors, failures by platform |

## C. Local run (development and testing)

Works on Windows, macOS and Linux without Docker. Uses one process for the API, workers and all bots,
SQLite or PostgreSQL, an in-process Redis replacement and disk storage in `local/storage`.

### C1. Requirements

- Python 3.12+, Node.js 22+, FFmpeg in `PATH` (merging video + audio).
- Optional: PostgreSQL 16 (otherwise SQLite is used automatically).
- Test bots from @BotFather (do not use production tokens: one token can be polled by only one process).

### C2. Install

```bash
python -m pip install -e ".[test]" lupa
cd dashboard && npm install && cd ..
```

### C3. Configure `local/.env`

```ini
VIDEO_BOT_TOKEN=...
MEDIA_BOT_TOKEN=...
FILES_BOT_TOKEN=...
# optional, PostgreSQL instead of SQLite:
DATABASE_URL=postgresql+psycopg://media:<password>@127.0.0.1:5432/media
```

`local/` is git-ignored. Secrets for sessions and service keys are generated automatically into `local/dev-secrets.env`.

### C4. Run

```bash
python -m infrastructure.scripts.dev                        # API on 127.0.0.1:8000 + workers + bots
cd dashboard && npm run dev                                 # admin panel on http://localhost:5173
```

Open **http://localhost:5173** (use `localhost`, not `127.0.0.1`: the admin origin check is exact).
The admin username and password are written to `local/dev-admin.txt` on first start.
Download links are `http://127.0.0.1:8000/f/...` and work only on this computer.

To move existing local SQLite data into PostgreSQL:

```bash
python -m infrastructure.scripts.sqlite_to_postgres sqlite:///local/dev.db postgresql+psycopg://media:<password>@127.0.0.1:5432/media
```

### C5. Tests

```bash
pytest -q                                                    # unit + integration on SQLite
TEST_DATABASE_URL=postgresql+psycopg://media:<password>@127.0.0.1:5432/media_test pytest -q tests/integration
                                                             # the same on PostgreSQL, plus migration-vs-models check
cd dashboard && npm run build                                # TypeScript check + production build
```

`TEST_DATABASE_URL` must point to a **disposable** database: tests drop and recreate all tables.
