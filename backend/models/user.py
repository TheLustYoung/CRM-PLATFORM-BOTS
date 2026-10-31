from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now


class User(Base):
    """One Telegram account shared by every bot of the platform."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    first_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(16))
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    # Monetization: Premium end date, who invited the user, and whether the invite already counted
    # (an invite counts after the new user's first successful download, so empty sign-ups earn nothing).
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    referred_by: Mapped[int | None] = mapped_column(BigInteger, index=True)
    referral_counted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    premium_tier: Mapped[str | None] = mapped_column(String(24))  # the paid tier while premium_until is in the future
    credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # extra downloads beyond the daily limit


class BotUser(Base):
    __tablename__ = "bot_users"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Preference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
