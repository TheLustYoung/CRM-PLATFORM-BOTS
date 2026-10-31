# Backup and restore

Back up PostgreSQL, the file storage (volume `files-data`, or `minio-data` with STORAGE_BACKEND=s3) and `.env` (separately and encrypted).
Redis is not a source of truth: queued and stuck jobs are recovered by reconciliation.
For a consistent snapshot, stop the API, bots, worker and beat; let running jobs finish or repeat them after restore.
Run the commands on the server in the project directory.

```bash
umask 077
mkdir -p backups
docker compose stop video-bot media-bot files-bot api worker beat
docker compose exec -T postgres pg_dump -U media -d media -Fc > backups/media.dump
docker run --rm --network none \
  -v telegram-media_files-data:/data:ro \
  -v "$PWD/backups:/backup" alpine:3.21 \
  tar -czf /backup/files.tar.gz -C /data .
docker compose up -d
```

The volume name depends on the Compose project name (`telegram-media` in the file); check `docker volume ls` first.
Move the archives to another disk or server, encrypted and with restricted access. Files deleted from active storage
may remain in backups. Verify with `pg_restore --list backups/media.dump` and `tar -tzf backups/files.tar.gz`.

**Restore only into a separate staging project or empty volumes.** Create the database,
`pg_restore -U media -d media --no-owner` from the dump, unpack the files archive into an empty volume while the
stack is stopped (for MinIO also restore the matching S3 credentials). After start: `alembic upgrade head`, readiness check, download a known file,
check revocation and admin login. Never use `--clean` or overwrite volumes of a running production without a decision.

Test restores regularly. A PostgreSQL dump without the stored files is not a complete backup.

## Automatic safety copies on every update

`infrastructure/scripts/server-setup.sh` (run after every Pull in Plesk) does this by itself:

- keeps `.env` and the generated secrets in `/var/lib/telegram-media`, so a new checkout of the code never creates new
  passwords or loses settings, proxies and accounts;
- dumps the database into `/var/lib/telegram-media/backups/db-<date>.sql.gz` before applying migrations (the last 10
  are kept); restore one with
  `gunzip -c /var/lib/telegram-media/backups/<file>.sql.gz | docker compose exec -T postgres psql -U media -d media`;
- refuses to start with a fresh `.env` when an old database volume exists (instead of silently losing data).

## Updating

1. Plesk → Git → **Pull** (or `git pull` in the project directory).
2. `sudo bash infrastructure/scripts/server-setup.sh` — rebuilds the images, backs up the database, applies migrations
   (`alembic upgrade head`) and restarts the services.
3. If the release notes say so, paste the nginx directives from `infrastructure/plesk/` again.
4. Check: dashboard login, Overview (bots online), one download per bot, Settings → Monitoring → «Check now».

Rollback: check out the previous commit, run the script again; to undo a migration restore the dump taken before it.

## Regular maintenance

| How often | What |
|---|---|
| Every day (automatic) | Monitoring every 5 minutes: disk, failed downloads, silent bots, queue, proxies; alerts to Telegram / e-mail |
| Every day (automatic) | Expired files and temporary downloads are removed by the cleanup task; stuck jobs are recovered |
| Every week | Look at Reports (error rate by source) and the compatibility list on the Overview |
| Every month | Proxy and API balances, disk usage, test restore of a backup, `docker image prune` |
| When a source site changes | Rebuild the images (new yt-dlp) with the update steps above |
