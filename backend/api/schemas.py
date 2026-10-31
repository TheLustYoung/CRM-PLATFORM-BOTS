from pydantic import BaseModel, Field, field_validator
from backend.services import i18n


class Identity(BaseModel):
    user_id: int = Field(gt=0, le=9223372036854775807)
    username: str | None = Field(default=None, max_length=64)


class Register(Identity):
    first_name: str | None = Field(default=None, max_length=256)
    language_code: str | None = Field(default=None, max_length=16)
    referrer: int | None = Field(default=None, gt=0, le=9223372036854775807)  # from a /start ref_<id> invite link


class Checkout(Identity):
    payload: str = Field(max_length=128)
    amount: int = Field(gt=0, le=1_000_000)


class Paid(Checkout):
    charge_id: str = Field(min_length=1, max_length=128)


class PremiumGrant(BaseModel):
    days: int = Field(ge=0, le=3650)  # 0 removes Premium
    tier: str = Field(default="premium", pattern=r"^[a-z0-9_-]{1,24}$")


class Submit(Identity):
    request_key: str = Field(min_length=1, max_length=150)
    url: str = Field(max_length=2048)


class SelectFormat(Identity):
    metadata_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    index: int = Field(ge=0, le=200)


class Upload(Identity):
    request_key: str = Field(min_length=1, max_length=150)
    file_id: str = Field(min_length=1, max_length=512)
    name: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)


class Language(Identity):
    language: str = Field(max_length=8)

    @field_validator("language")
    @classmethod
    def known(cls, value):
        if value not in i18n.catalogs():
            raise ValueError("unknown language")
        return value


class Heartbeat(BaseModel):
    username: str = Field(default="", max_length=64)


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserPatch(BaseModel):
    banned: bool
    daily_limit: int | None = Field(default=None, ge=1, le=10000)
    credits: int | None = Field(default=None, ge=0, le=1_000_000)  # extra downloads beyond the daily limit


class BotPatch(BaseModel):
    enabled: bool
    daily_limit: int = Field(ge=1, le=100000)
    welcome_text: str | None = Field(default=None, max_length=2000)
    platforms: list[str] | None = Field(default=None, max_length=20)  # None = every enabled platform
