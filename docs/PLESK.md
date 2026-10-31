# Deployment behind Plesk

Use staging first, then the acceptance check in [DEPLOYMENT.md](DEPLOYMENT.md#a9-acceptance-check).

1. Create DNS A/AAAA records for `admin`, `files` (and optionally `api`). Do not add AAAA without working IPv6.
2. Create the subdomains in Plesk; issue Let's Encrypt certificates and enable the HTTP→HTTPS redirect.
3. Put the project outside public `httpdocs`, e.g. `/opt/telegram-media`, owned by a service account; `.env` mode 600,
   never in Git.
4. Run the commands from DEPLOYMENT.md. Check `docker compose config --quiet`, `docker compose ps` and readiness before
   configuring the proxy. Do not publish MinIO, PostgreSQL or Redis.
5. Point `admin` to `http://127.0.0.1:8080` and `api`/`files` to `127.0.0.1:8000`, either with Plesk Docker Proxy Rules
   (manual port mapping) or with **Apache & nginx Settings → Additional nginx directives** using the snippets in
   `infrastructure/plesk/`.
6. When using a manual `location /`, disable the standard nginx Proxy mode for that subdomain, otherwise Plesk may report
   a duplicate location. Do not edit generated `nginx.conf` files directly (Plesk overwrites them); apply and check `nginx -t`.
7. On `api`/`files`, `/internal/` is closed; files are served only under `/f/`. The dashboard calls the API same-origin via
   its own `/api`, so the browser needs no cross-site cookies.
8. The `Origin` header must reach the backend unchanged, and `ADMIN_ORIGIN` must exactly equal `https://admin.example.com`
   (no trailing `/`).
9. Open the dashboard, sign in with the created account, check all bots and files.

The snippets are meant for the HTTPS vhost; certificates and redirects are handled by Plesk, not Docker.
Do not add a second `location /` if you use Docker Proxy Rules.

Uvicorn does not trust forwarded headers. The public download limit (120 requests/minute) therefore applies to the
proxy IP (shared by visitors), while bot job limits apply per Telegram user. Do not enable blind trust of
`X-Forwarded-For`; for a large audience configure per-IP `limit_req` in the trusted outer nginx.

## Updates and monitoring

```bash
docker compose logs --tail=100 api worker video-bot media-bot files-bot
docker compose exec api alembic current
docker compose ps
docker compose exec worker python -c 'import yt_dlp; print(yt_dlp.version.__version__)'
```

Do not enable HTTP debug or yt-dlp verbose logging: Telegram URLs contain the bot token.
After rotating tokens: `docker compose up -d --force-recreate api worker video-bot media-bot files-bot`.
Tokens are set by the operator in `.env`; the dashboard only shows configured / username / online.
Enable/disable is stored in PostgreSQL and checked by the API and worker; the poller may stay online.
Back up before updating. Keep a single Celery beat. The tmpfs size is sized for concurrency 2; more requires more RAM.

References: [Plesk Docker](https://doc.plesk.com/en-US/obsidian/administrator-guide/plesk-administration/using-docker.75823/),
[reverse proxy to a local port](https://support.plesk.com/hc/en-us/articles/12388464421143-How-to-pass-requests-from-a-Plesk-hosted-domain-to-the-application-listening-on-a-local-port),
[duplicate location](https://support.plesk.com/hc/en-us/articles/12377110016151-Can-t-add-location-to-additional-nginx-directives-in-Plesk-nginx-emerg-duplicate-location).
