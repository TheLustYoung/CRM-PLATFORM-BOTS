"""Docker healthcheck: `python -m bots.health video` exits 0 if the bot sent a heartbeat recently."""
import sys
from datetime import timedelta
from backend.database import Session
from backend.models import Bot, now, aware

with Session() as db:
    bot = db.get(Bot, sys.argv[1])
    healthy = bool(bot and bot.last_seen and aware(bot.last_seen) > now() - timedelta(seconds=120))
    raise SystemExit(0 if healthy else 1)
