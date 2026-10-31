"""Synthetic demo data for local presentations and screenshots. NEVER for production.

    DEMO_DATA=1 python -m infrastructure.scripts.dev      (fills an empty local database once)

Everything created here is clearly marked: Telegram ids start at 900 000 000 (outside real ranges used in tests),
usernames start with ``demo_``, request keys with ``demo:`` and links point to example items. The data follow a
fixed random seed, so screenshots are reproducible. Remove with ``python -m infrastructure.scripts.demo_data --clear``.
"""
import random
import sys
from datetime import timedelta
from sqlalchemy import delete, select
from backend.database import Session
from backend.models import BotUser, Job, Usage, User, now

DEMO_ID = 900_000_000
SOURCES = [("archive", "https://archive.org/details/demo-item-{n}", 0.46), ("wikimedia", "https://commons.wikimedia.org/wiki/File:Demo_{n}.jpg", 0.34),
           ("direct", "https://files.example.org/demo/clip-{n}.mp4", 0.20)]
LANGUAGES = ["en", "en", "en", "es", "pt", "ru", "ar", "hi", "fr", "zh"]
# Activity by hour (UTC): quiet nights, a midday rise, an evening peak — shapes the weekday × hour heatmap.
HOURS = [1, 1, 1, 1, 1, 2, 3, 5, 7, 8, 9, 10, 10, 9, 9, 10, 12, 15, 18, 19, 17, 12, 6, 3]


def has_demo(db) -> bool:
    return db.scalar(select(User.id).where(User.id >= DEMO_ID).limit(1)) is not None


def clear(db) -> None:
    demo_jobs = select(Job.id).where(Job.request_key.like("demo:%"))
    db.execute(delete(Usage).where(Usage.job_id.in_(demo_jobs)))
    db.execute(delete(Job).where(Job.request_key.like("demo:%")))
    db.execute(delete(BotUser).where(BotUser.user_id >= DEMO_ID))
    db.execute(delete(User).where(User.id >= DEMO_ID))
    db.commit()


def fill(db, days: int = 30, users: int = 240, seed: int = 2026) -> int:
    rnd = random.Random(seed)
    today = now()
    people = []
    for n in range(users):
        joined = today - timedelta(days=rnd.uniform(0, days + 20))
        user = User(id=DEMO_ID + n, username=f"demo_user_{n:03d}", first_name="Demo", language_code=rnd.choice(LANGUAGES),
                    created_at=joined, last_seen=today - timedelta(hours=rnd.uniform(0, 24 * 6)))
        db.add(user)
        bots = rnd.sample(["video", "media", "files"], rnd.choice([1, 1, 2, 3]))
        db.add_all(BotUser(user_id=user.id, bot_id=b, created_at=joined) for b in bots)
        people.append((user, bots))
    db.flush()
    count = 0
    for day in range(days, -1, -1):
        trend = 0.55 + 0.45 * (days - day) / days  # growing usage over the month
        weekend = 1.25 if (today - timedelta(days=day)).weekday() >= 5 else 1.0
        for _ in range(int(rnd.gauss(46, 8) * trend * weekend)):
            user, bots = rnd.choice(people)
            bot = rnd.choice(bots)
            created = (today - timedelta(days=day)).replace(hour=rnd.choices(range(24), HOURS)[0], minute=rnd.randrange(60), second=0)
            if created > today:
                continue
            count += 1
            if bot == "files":
                db.add(Job(user_id=user.id, bot_id=bot, request_key=f"demo:{count}", kind="upload", platform="telegram",
                           status="completed", created_at=created, payload={"name": f"demo-file-{count}.pdf"}))
                continue
            platform, url, _ = rnd.choices(SOURCES, [s[2] for s in SOURCES])[0]
            if bot == "video" and platform == "direct":
                platform, url = "archive", SOURCES[0][1]
            link = url.format(n=rnd.randrange(1, 400))
            db.add(Job(user_id=user.id, bot_id=bot, request_key=f"demo:{count}", kind="metadata", platform=platform,
                       source_url=link, status="completed", created_at=created, result={"title": "Demo item"}))
            if rnd.random() < 0.78:  # most people download after seeing the card
                count += 1
                status = "failed" if rnd.random() < 0.07 else "completed"
                job = Job(user_id=user.id, bot_id=bot, request_key=f"demo:{count}", kind="download", platform=platform,
                          source_url=link, status=status, created_at=created + timedelta(seconds=rnd.randrange(5, 90)),
                          error="unavailable" if status == "failed" else None, payload={"title": "Demo item", "label": "MP4 · 720p"})
                db.add(job)
                db.flush()
                db.add(Usage(user_id=user.id, bot_id=bot, job_id=job.id, created_at=job.created_at))
    db.commit()
    return count


def main():
    with Session() as db:
        if "--clear" in sys.argv:
            clear(db)
            print("Demo data removed.")
        elif has_demo(db):
            print("Demo data already present.")
        else:
            print(f"Demo data: {fill(db)} jobs created.")


if __name__ == "__main__":
    main()
