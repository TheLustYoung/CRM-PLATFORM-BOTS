"""Bot appearance managed from the admin panel: name, descriptions, menu commands, profile photo.

Telegram is the source of truth: values are read from and written to the Bot API directly,
per language ("" = default for every language without its own value). The bot @username and
token cannot be changed through the API (only via @BotFather).
"""
import re
from pydantic import BaseModel, Field, field_validator
from backend.config import settings
from backend.services import i18n
from workers.telegram import Telegram

PHOTO_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
PHOTO_LIMIT = 10_000_000


class Command(BaseModel):
    command: str = Field(pattern=r"^[a-z0-9_]{1,32}$")
    description: str = Field(min_length=1, max_length=256)


class Profile(BaseModel):
    """Telegram limits: name 64, short description 120, description 512, up to 100 commands."""
    name: str = Field(default="", max_length=64)
    short_description: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=512)
    commands: list[Command] = Field(default_factory=list, max_length=100)

    @field_validator("commands")
    @classmethod
    def unique(cls, value):
        if len({c.command for c in value}) != len(value):
            raise ValueError("duplicate command")
        return value


def languages() -> list[str]:
    return ["", *i18n.catalogs()]


def check_language(lang: str) -> str:
    if lang not in languages():
        raise ValueError("unknown language")
    return lang


def read(kind: str, lang: str) -> Profile:
    code = lang or None
    with Telegram(kind) as tg:
        return Profile(
            name=tg.call("getMyName", {"language_code": code}).get("name", ""),
            short_description=tg.call("getMyShortDescription", {"language_code": code}).get("short_description", ""),
            description=tg.call("getMyDescription", {"language_code": code}).get("description", ""),
            commands=[Command(**c) for c in tg.call("getMyCommands", {"language_code": code})],
        )


def write(kind: str, lang: str, profile: Profile) -> Profile:
    """Only fields that differ from Telegram's current value are sent: setMyName is strictly rate-limited."""
    code = lang or None
    current = read(kind, lang)
    with Telegram(kind) as tg:
        if profile.name != current.name:
            tg.call("setMyName", {"name": profile.name, "language_code": code})
        if profile.short_description != current.short_description:
            tg.call("setMyShortDescription", {"short_description": profile.short_description, "language_code": code})
        if profile.description != current.description:
            tg.call("setMyDescription", {"description": profile.description, "language_code": code})
        if profile.commands != current.commands:
            if profile.commands:
                tg.call("setMyCommands", {"commands": [c.model_dump() for c in profile.commands], "language_code": code})
            else:
                tg.call("deleteMyCommands", {"language_code": code})
    return read(kind, lang)


def bot_user_id(kind: str) -> int:
    token = settings().bot_token(kind)
    if not re.match(r"^\d+:", token):
        raise ValueError("bot token is not configured")
    return int(token.split(":", 1)[0])


def photo(kind: str) -> bytes | None:
    """Current profile photo (largest size) or None."""
    with Telegram(kind) as tg:
        photos = tg.call("getUserProfilePhotos", {"user_id": bot_user_id(kind), "limit": 1}).get("photos") or []
        if not photos:
            return None
        largest = max(photos[0], key=lambda p: p.get("width", 0) * p.get("height", 0))
        return tg.file_bytes(largest["file_id"], PHOTO_LIMIT)


def set_photo(kind: str, content: bytes, mime: str) -> None:
    ext = PHOTO_TYPES.get(mime)
    if not ext or not content or len(content) > PHOTO_LIMIT:
        raise ValueError("photo must be JPEG or PNG up to 10 MB")
    with Telegram(kind) as tg:
        tg.call("setMyProfilePhoto", {"photo": {"type": "static", "photo": "attach://photo"}},
                files={"photo": (f"photo.{ext}", content, mime)})


def remove_photo(kind: str) -> None:
    with Telegram(kind) as tg:
        tg.call("removeMyProfilePhoto", {})
