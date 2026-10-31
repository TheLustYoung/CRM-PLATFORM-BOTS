"""Local all-in-one run for development and live bot testing without Docker.

    python -m infrastructure.scripts.dev

Runs the API (http://127.0.0.1:8000), a background worker pool and every bot that has a
token in ``local/.env``. Uses SQLite, in-process Redis (fakeredis) and disk storage in
``local/storage``. Production uses PostgreSQL, Redis, MinIO and Celery via docker-compose.yml.
"""
import asyncio
import logging
import os
import secrets
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "local"
LOCAL.mkdir(exist_ok=True)
(LOCAL / "tmp").mkdir(exist_ok=True)

env_file = LOCAL / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# Generated once and kept, so admin sessions survive restarts of the local runner.
secrets_file = LOCAL / "dev-secrets.env"
if not secrets_file.exists():
    secrets_file.write_text("".join(f"{key}={secrets.token_hex(32)}\n" for key in
                                    ("JWT_SECRET", "VIDEO_SERVICE_KEY", "MEDIA_SERVICE_KEY", "FILES_SERVICE_KEY")), encoding="utf-8")
for line in secrets_file.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)

defaults = {
    "DATABASE_URL": f"sqlite:///{(LOCAL / 'dev.db').as_posix()}",
    "REDIS_URL": "redis://fake",
    # Files on disk: they survive restarts of the local runner (in-memory S3 did not).
    "STORAGE_BACKEND": "local", "STORAGE_DIR": str(LOCAL / "storage"),
    "S3_ACCESS_KEY": "local", "S3_SECRET_KEY": "local-secret-key",
    "ADMIN_ORIGIN": "http://localhost:5173", "COOKIE_SECURE": "false", "PUBLIC_FILES_URL": "http://127.0.0.1:8000",
    "API_INTERNAL_URL": "http://127.0.0.1:8000", "EGRESS_PROXY": "", "TEMP_ROOT": str(LOCAL / "tmp"), "MIN_FREE_DISK_BYTES": "0",
}
for key, value in defaults.items():
    os.environ.setdefault(key, value)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("dev")


def patch_infrastructure():
    import fakeredis
    from backend.services import limits, queue
    from workers import tasks

    redis = fakeredis.FakeRedis(decode_responses=True)
    limits.redis_client.cache_clear()
    limits.redis_client = lambda: redis
    tasks.redis_client = lambda: redis
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="worker")

    def execute(job_id: str, priority: bool = False):
        def job():
            try:
                tasks.run(job_id)
            except tasks.Temporary as exc:
                retry = 30 * int(str(exc) or 1)
                log.info("job %s: temporary error, retry in %ss", job_id, retry)
                threading.Timer(retry, lambda: pool.submit(tasks.run, job_id)).start()
            except Exception:
                log.exception("job %s crashed", job_id)
        pool.submit(job)

    queue.enqueue = execute

    def run_task(name: str, *args, countdown: float = 0):
        from workers import broadcast
        task = {broadcast.SEND_TASK: broadcast.send, broadcast.DELETE_TASK: broadcast.delete}.get(name)
        if task:
            pool.submit(task, *args)

    queue.task = run_task

    def channel_schedule():  # what celery beat does on the server: scheduled channel posts
        from backend.database import Session
        from backend.services import channel
        while True:
            try:
                with Session() as db:
                    channel.publish_due(db)
            except Exception:
                log.exception("channel schedule")
            threading.Event().wait(30)
    threading.Thread(target=channel_schedule, daemon=True, name="channel").start()


def prepare_database():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select
    from backend.cli import seed
    from backend.database import Session
    from backend.models import Admin
    from backend.services.auth import hasher

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "database" / "migrations"))
    command.upgrade(config, "head")
    seed()
    credentials = LOCAL / "dev-admin.txt"
    with Session() as db:
        if not db.scalar(select(Admin).where(Admin.username == "admin")):
            password = secrets.token_urlsafe(12)
            db.add(Admin(username="admin", password_hash=hasher.hash(password)))
            db.commit()
            credentials.write_text(f"username: admin\npassword: {password}\n", encoding="utf-8")
    log.info("Admin credentials for the local dashboard: %s", credentials)
    if os.environ.get("DEMO_DATA") == "1":  # synthetic, clearly marked data for presentations (scripts/demo_data.py)
        from infrastructure.scripts import demo_data
        with Session() as db:
            if not demo_data.has_demo(db):
                log.info("Demo data: %s jobs created", demo_data.fill(db))


def start_api():
    import uvicorn
    from backend.main import app
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True, name="api")
    thread.start()
    return server


async def run_bots():
    from backend.config import settings, BOT_KINDS
    from bots.common.runner import serve
    from bots.video import setup as video
    from bots.media import setup as media
    from bots.file_sharing import setup as files

    setups = {"video": (video, [("history", "My downloads"), ("help", "Help")]),
              "media": (media, [("history", "My downloads"), ("help", "Help")]),
              "files": (files, [("myfiles", "My files"), ("help", "Help")])}
    active = [kind for kind in BOT_KINDS if settings().bot_token(kind)]
    if not active:
        log.warning("No bot tokens in local/.env - API only. Add VIDEO_BOT_TOKEN / MEDIA_BOT_TOKEN / FILES_BOT_TOKEN.")
        while True:
            await asyncio.sleep(3600)
    log.info("Starting bots: %s", ", ".join(active))
    await asyncio.gather(*(serve(kind, *setups[kind]) for kind in active))


def main():
    patch_infrastructure()
    prepare_database()
    start_api()
    log.info("API: http://127.0.0.1:8000  |  dashboard: cd dashboard && npm run dev -> http://localhost:5173")
    try:
        asyncio.run(run_bots())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
