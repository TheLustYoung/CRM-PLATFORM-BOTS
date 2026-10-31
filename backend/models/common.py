import uuid
from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid.uuid4())


def aware(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes; PostgreSQL returns aware ones. Normalize to UTC.
    if value is None or value.tzinfo:
        return value
    return value.replace(tzinfo=timezone.utc)
