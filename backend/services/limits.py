from functools import lru_cache
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from redis import Redis
from backend.config import settings
from backend.models import SystemSetting
from backend.services import i18n
from backend.services.security import DomainError

PlatformName = Literal["wikimedia", "archive", "direct"]
ALL_PLATFORM_NAMES = ["wikimedia", "archive", "direct"]
# Sources that existed before settings remembered which ones the administrator had seen (see policy()).
FIRST_PLATFORMS = ["wikimedia", "archive", "direct"]


class Policy(BaseModel):
    """System settings editable from the admin dashboard."""
    daily_jobs: int = Field(default=20, ge=1, le=10000)
    max_download_bytes: int = Field(default=2_000_000_000, ge=1024, le=2_000_000_000)
    max_upload_bytes: int = Field(default=19_000_000, ge=1024, le=19_000_000)
    retention_days: int = Field(default=7, ge=1, le=365)  # files uploaded to the File bot
    media_retention_days: int = Field(default=7, ge=1, le=365)  # media downloaded by the Video and Media bots
    enabled_platforms: list[PlatformName] = Field(default_factory=lambda: list(ALL_PLATFORM_NAMES))
    # Platforms the administrator saw when these settings were saved; a platform added in an update starts enabled.
    known_platforms: list[str] = Field(default_factory=lambda: list(ALL_PLATFORM_NAMES))
    default_language: str = "en"

    @field_validator("default_language")
    @classmethod
    def known_language(cls, value):
        if value not in i18n.catalogs():
            raise ValueError("unknown language")
        return value


@lru_cache
def redis_client() -> Redis:
    return Redis.from_url(settings().redis_url, decode_responses=True)


def rate_limit(key: str, limit: int, seconds: int) -> None:
    count = redis_client().eval(
        "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
        1, f"rate:{key}", seconds)
    if count > limit:
        raise DomainError("rate_limit")


def policy(db) -> Policy:
    row = db.get(SystemSetting, "policy")
    if row:
        data = dict(row.value)
        known = data.get("known_platforms") or FIRST_PLATFORMS
        added = [p for p in ALL_PLATFORM_NAMES if p not in known]  # new in an update: on, until switched off
        saved = [p for p in data.get("enabled_platforms", []) if p in ALL_PLATFORM_NAMES]  # sources removed in an update drop out
        data["enabled_platforms"] = [*saved, *(p for p in added if p not in saved)]
        data["known_platforms"] = list(ALL_PLATFORM_NAMES)
        data.setdefault("media_retention_days", data.get("retention_days", 7))  # saved before the two periods were split
        return Policy.model_validate(data)
    s = settings()
    return Policy(daily_jobs=s.daily_jobs, max_download_bytes=s.max_download_bytes, max_upload_bytes=min(s.max_upload_bytes, 19_000_000),
                  retention_days=s.retention_days, media_retention_days=s.retention_days, default_language=i18n.resolve(s.default_language))
