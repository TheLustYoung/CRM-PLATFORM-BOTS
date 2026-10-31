"""Reports: daily, weekly and monthly figures, by bot, service and platform, with error rates, revenue by
payment method and storage use.

Calculation rules:
- a period is a calendar day, an ISO week (Monday–Sunday) or a calendar month, in UTC;
- downloads / uploads: jobs of that kind created in the period; completed and failed by their final status;
- error rate: failed / (completed + failed) of the period's downloads and uploads, in percent;
- active users: distinct users who started at least one job in the period; new users: accounts created in it;
- revenue: paid orders by their payment time, per method and currency (Stars in Stars, cards and crypto in USD cents),
  refunded orders excluded; plus Stars purchases made directly in Telegram;
- storage: the size of all stored files that are not deleted, at the moment of the report.
"""
import csv
import io
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from sqlalchemy import func, select
from backend.models import Job, Order, Payment, UploadedFile, User, aware, now

PERIODS = {"day": 1, "week": 7, "month": 31}


def bucket(moment: datetime, period: str) -> str:
    day = aware(moment).date()
    if period == "week":
        return (day - timedelta(days=day.weekday())).isoformat()
    if period == "month":
        return day.strftime("%Y-%m")
    return day.isoformat()


def start_of(period: str, count: int) -> datetime:
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        first = today.replace(day=1)
        for _ in range(count - 1):
            first = (first - timedelta(days=1)).replace(day=1)
        return first
    if period == "week":
        monday = today - timedelta(days=today.weekday())
        return monday - timedelta(weeks=count - 1)
    return today - timedelta(days=count - 1)


def report(db, period: str = "day", count: int = 30, bot: str | None = None) -> dict:
    if period not in PERIODS:
        raise ValueError("unknown period")
    count = max(1, min(count, 400 if period == "day" else 104 if period == "week" else 36))
    since = start_of(period, count)
    jobs = select(Job.created_at, Job.kind, Job.status, Job.bot_id, Job.platform, Job.user_id, Job.error).where(Job.created_at >= since)
    if bot:
        jobs = jobs.where(Job.bot_id == bot)
    rows = db.execute(jobs).all()
    periods: dict[str, dict] = defaultdict(lambda: {"downloads": 0, "uploads": 0, "metadata": 0, "completed": 0, "failed": 0,
                                                    "users": set(), "new_users": 0, "revenue": Counter()})
    by_bot, by_platform, by_service, errors = Counter(), Counter(), Counter(), Counter()
    failed_by_platform = Counter()
    for created, kind, status, bot_id, platform, user_id, error in rows:
        p = periods[bucket(created, period)]
        p["downloads" if kind == "download" else "uploads" if kind == "upload" else "metadata"] += 1
        p["users"].add(user_id)
        if kind in ("download", "upload") and status in ("completed", "failed"):
            p[status] += 1
            if status == "failed":
                errors[error or "failed"] += 1
                failed_by_platform[platform] += 1
        by_bot[bot_id] += 1
        by_service[kind] += 1
        if kind != "upload":
            by_platform[platform] += 1
    for (created,) in db.execute(select(User.created_at).where(User.created_at >= since)).all():
        periods[bucket(created, period)]["new_users"] += 1
    orders = select(Order.paid_at, Order.method, Order.currency, Order.amount).where(Order.status == "paid", Order.paid_at >= since)
    if bot:
        orders = orders.where(Order.bot_id == bot)
    methods = Counter()
    for paid, method, currency, amount in db.execute(orders).all():
        key = f"{method or 'other'}:{(currency or '').upper()}"
        periods[bucket(paid, period)]["revenue"][key] += amount or 0
        methods[key] += amount or 0
    stars = select(Payment.created_at, Payment.stars).where(Payment.source == "stars", Payment.created_at >= since)
    if bot:
        stars = stars.where(Payment.bot_id == bot)
    for created, amount in db.execute(stars).all():
        periods[bucket(created, period)]["revenue"]["stars:XTR"] += amount or 0
        methods["stars:XTR"] += amount or 0
    keys, cursor = [], since
    while len(keys) < count:  # every period in the range, also the empty ones
        keys.append(bucket(cursor, period))
        cursor = cursor + timedelta(days=PERIODS[period])
        if period == "month":
            cursor = cursor.replace(day=1)
    keys = list(dict.fromkeys(keys))
    series = []
    for key in keys:
        p = periods[key]
        done = p["completed"] + p["failed"]
        series.append({"period": key, "downloads": p["downloads"], "uploads": p["uploads"], "metadata": p["metadata"],
                       "completed": p["completed"], "failed": p["failed"], "error_rate": round(100 * p["failed"] / done, 1) if done else 0.0,
                       "active_users": len(p["users"]), "new_users": p["new_users"], "revenue": dict(p["revenue"])})
    stored = db.execute(select(func.count(), func.coalesce(func.sum(UploadedFile.size), 0)).where(UploadedFile.deleted.is_(False))).one()
    return {"period": period, "since": since.isoformat(), "bot": bot, "series": series,
            "by_bot": dict(by_bot), "by_service": dict(by_service), "by_platform": dict(by_platform.most_common(20)),
            "failed_by_platform": dict(failed_by_platform.most_common(20)), "errors": dict(errors.most_common(10)),
            "revenue_by_method": dict(methods), "storage": {"files": stored[0], "bytes": int(stored[1])}}


def csv_report(data: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    methods = sorted({m for row in data["series"] for m in row["revenue"]} | set(data["revenue_by_method"]))
    writer.writerow(["period", "downloads", "uploads", "completed", "failed", "error_rate_%", "active_users", "new_users",
                     *[f"revenue_{m}" for m in methods]])
    for row in data["series"]:
        writer.writerow([row["period"], row["downloads"], row["uploads"], row["completed"], row["failed"], row["error_rate"],
                         row["active_users"], row["new_users"], *[row["revenue"].get(m, 0) for m in methods]])
    return out.getvalue()


def today() -> date:
    return now().date()
