#!/usr/bin/env bash
# One-command server setup. Run from anywhere inside the project, as root:
#
#     bash infrastructure/scripts/server-setup.sh media.example.com            # ports 18000 / 18080
#     bash infrastructure/scripts/server-setup.sh media.example.com 28000 28080
#
# Safe to run again: an existing .env, data and admin accounts are kept. Every run keeps a copy of .env in
# /var/lib/aws-media-hub and backs up the database there before updating.
set -euo pipefail

DOMAIN="${1:-}"
API_PORT="${2:-18000}"
DASHBOARD_PORT="${3:-18080}"
cd "$(dirname "$0")/../.."
PROJECT="$(pwd)"

step() { printf '\n\033[1;32m==> %s\033[0m\n' "$1"; }
fail() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1"; exit 1; }
set_var() {  # set_var KEY VALUE  (values here never contain "|" or "&")
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else printf '%s=%s\n' "$1" "$2" >> .env; fi
}
get_var() { grep -m1 "^$1=" .env | cut -d= -f2- || true; }

[ -n "$DOMAIN" ] || fail "Usage: bash infrastructure/scripts/server-setup.sh <domain> [api_port] [dashboard_port]"
[ "$(id -u)" -eq 0 ] || fail "Please run as root (or with sudo)."

step "1/7 Checking Docker"
command -v docker >/dev/null || fail "Docker is not installed."
docker compose version >/dev/null 2>&1 || fail "The Docker Compose plugin is not installed."
command -v openssl >/dev/null || fail "openssl is not installed (apt install openssl)."
echo "OK: $(docker compose version | head -n1)"

step "2/7 Checking ports $API_PORT and $DASHBOARD_PORT"
if [ -n "$(docker compose ps -q api dashboard 2>/dev/null)" ]; then
  echo "OK: our containers already use them."
else
  for port in "$API_PORT" "$DASHBOARD_PORT"; do
    if ss -ltn "sport = :$port" | grep -q LISTEN; then
      fail "Port $port is used by another application. Run again with other ports, e.g.: bash $0 $DOMAIN 28000 28080"
    fi
  done
  echo "OK: both ports are free."
fi

step "3/7 Configuration file (.env)"
# A copy of .env lives outside the project folder, so an update through Plesk (Pull, a new deployment folder,
# a re-created repository) never loses the passwords that open the existing database.
STATE=/var/lib/aws-media-hub
mkdir -p "$STATE/backups" && chmod 700 "$STATE"
if [ ! -f .env ] && [ -f "$STATE/.env" ]; then
  cp "$STATE/.env" .env
  echo "Restored .env from $STATE (kept from the previous installation)."
fi
if [ ! -f .env ] && docker volume ls -q | grep -qx 'aws-media-hub_postgres-data'; then
  fail "The database of a previous installation exists, but its .env is missing. Copy the old .env into $PROJECT (or $STATE) and run this again; new passwords would lock you out of the existing data."
fi
if [ ! -f .env ]; then
  cp .env.example .env
  for key in POSTGRES_PASSWORD JWT_SECRET VIDEO_SERVICE_KEY MEDIA_SERVICE_KEY FILES_SERVICE_KEY S3_SECRET_KEY; do
    set_var "$key" "$(openssl rand -hex 32)"
  done
  set_var DATABASE_URL "postgresql+psycopg://media:$(get_var POSTGRES_PASSWORD)@postgres:5432/media"
  echo "Created .env with new random passwords."
else
  echo "Keeping the existing .env (passwords unchanged)."
  sed -i 's/\r$//' .env
  # A hand-made .env may be incomplete: add missing settings, generate missing secrets.
  while IFS= read -r line; do
    case "$line" in ''|\#*) continue ;; esac
    grep -q "^${line%%=*}=" .env || printf '%s\n' "$line" >> .env
  done < .env.example
  for key in POSTGRES_PASSWORD JWT_SECRET VIDEO_SERVICE_KEY MEDIA_SERVICE_KEY FILES_SERVICE_KEY S3_SECRET_KEY; do
    case "$(get_var "$key")" in ''|CHANGE_ME*) set_var "$key" "$(openssl rand -hex 32)" ;; esac
  done
  if get_var DATABASE_URL | grep -q CHANGE_ME; then
    set_var DATABASE_URL "postgresql+psycopg://media:$(get_var POSTGRES_PASSWORD)@postgres:5432/media"
  fi
  echo "Completed missing settings in .env."
fi
chmod 600 .env
# Earlier defaults: 200 MB downloads and a RAM-backed temp folder too small for long videos.
[ "$(get_var MAX_DOWNLOAD_BYTES)" != 200000000 ] || set_var MAX_DOWNLOAD_BYTES 2000000000
[ "$(get_var TEMP_ROOT)" != /tmp/media ] || set_var TEMP_ROOT /data/files/.work
# The bundled MinIO is optional (no public image any more): use the server disk unless an external S3 is configured.
if [ "$(get_var STORAGE_BACKEND)" != local ] && get_var S3_ENDPOINT | grep -q '//minio:'; then
  set_var STORAGE_BACKEND local
  echo "Files will be stored on the server disk (Docker volume files-data)."
fi
set_var ADMIN_ORIGIN "https://$DOMAIN"
set_var PUBLIC_FILES_URL "https://$DOMAIN"
set_var API_PORT "$API_PORT"
set_var DASHBOARD_PORT "$DASHBOARD_PORT"
for kind in VIDEO MEDIA FILES; do
  while ! get_var "${kind}_BOT_TOKEN" | grep -Eq '^[0-9]+:[A-Za-z0-9_-]{30,}$'; do
    read -rsp "Paste the ${kind} bot token from @BotFather (hidden) and press Enter: " token </dev/tty; echo
    if printf '%s' "$token" | grep -Eq '^[0-9]+:[A-Za-z0-9_-]{30,}$'; then
      set_var "${kind}_BOT_TOKEN" "$token"
    else
      echo "That doesn't look like a bot token (format 123456789:AA...). Please try again."
    fi
  done
  echo "OK: ${kind} bot token is set."
done
left="$(grep -E '^[A-Z_]+=.*CHANGE_ME' .env | cut -d= -f1 | tr '\n' ' ' || true)"
[ -z "$left" ] || fail ".env still contains CHANGE_ME values in: $left"
docker compose config --quiet || fail "docker-compose.yml or .env is invalid."
echo "OK: configuration is valid."
cp .env "$STATE/.env" && chmod 600 "$STATE/.env"
echo "OK: a copy of .env is kept in $STATE."

step "4/7 Building (the first time takes several minutes)"
docker compose build

step "5/7 Starting the database, cache and storage, applying migrations"
docker compose up -d postgres redis
for _ in $(seq 1 30); do docker compose exec -T postgres pg_isready -U media -d media >/dev/null 2>&1 && break; sleep 2; done
# Backup before every update (the last 10 are kept): restore with
#   gunzip -c /var/lib/aws-media-hub/backups/<file>.sql.gz | docker compose exec -T postgres psql -U media -d media
if docker compose exec -T postgres psql -U media -d media -tAc "select 1 from information_schema.tables where table_name='users'" 2>/dev/null | grep -q 1; then
  backup="$STATE/backups/db-$(date +%Y%m%d-%H%M%S).sql.gz"
  if docker compose exec -T postgres pg_dump -U media -d media --clean --if-exists | gzip > "$backup" && [ -s "$backup" ]; then
    echo "OK: database backup saved to $backup"
    ls -1t "$STATE"/backups/db-*.sql.gz | tail -n +11 | xargs -r rm -f
  else
    rm -f "$backup"; fail "Could not back up the database before the update; nothing was changed."
  fi
fi
docker compose run --rm migrate
# Settings saved in the dashboard with the old 200 MB download limit: raise it to the new 2 GB default.
docker compose run --rm -T api python -c 'from backend.database import Session
from backend.models import SystemSetting
with Session() as db:
    row = db.get(SystemSetting, "policy")
    if row and row.value.get("max_download_bytes") == 200000000:
        row.value = {**row.value, "max_download_bytes": 2000000000}
        db.commit()
        print("OK: download limit raised to 2 GB.")' || true

step "6/7 Administrator account"
admins="$(docker compose run --rm -T api python -c 'from sqlalchemy import select, func
from backend.database import Session
from backend.models import Admin
with Session() as db: print(db.scalar(select(func.count()).select_from(Admin)))' | tail -n1)"
if [ "${admins:-0}" -gt 0 ] 2>/dev/null; then
  echo "OK: an administrator already exists."
else
  echo "Create the login for the admin panel (password: at least 12 characters):"
  docker compose run --rm api python -m backend.cli create-admin </dev/tty
fi

step "7/7 Starting everything"
docker compose up -d
printf 'Waiting for the API'
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$API_PORT/health/ready" >/dev/null 2>&1; then ready=1; break; fi
  printf '.'; sleep 3
done
echo
[ "${ready:-0}" -eq 1 ] || fail "The API did not become ready. Send the output of: docker compose logs --tail=80 api migrate"
docker compose ps --format 'table {{.Service}}\t{{.Status}}'

cat <<EOF

$(printf '\033[1;32m')DONE! The platform is running.$(printf '\033[0m')

Last step in Plesk: Websites & Domains -> $DOMAIN -> Apache & nginx Settings
  1) UNTICK "Proxy mode"
  2) Paste this into "Additional nginx directives" and click OK:
----------------------------------------------------------------
$(sed -e "s/__API_PORT__/$API_PORT/g" -e "s/__DASHBOARD_PORT__/$DASHBOARD_PORT/g" "$PROJECT/infrastructure/plesk/single-domain.nginx.conf")
----------------------------------------------------------------
Then open https://$DOMAIN and sign in. In Telegram, send /start to each bot.
EOF
