from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class Bot(Base):
    """A Telegram bot connected to the central backend. Tokens stay in the environment."""
    __tablename__ = "bots"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=1000)
    welcome_text: Mapped[str | None] = mapped_column(Text)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    platforms: Mapped[list | None] = mapped_column(JSON)  # platforms this bot serves; None = every enabled platform
