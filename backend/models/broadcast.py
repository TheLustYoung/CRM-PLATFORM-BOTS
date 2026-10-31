from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now, uid


class Broadcast(Base):
    """An ad post the administrator sends to the bots' users and can later delete from their chats."""
    __tablename__ = "broadcasts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    text: Mapped[str] = mapped_column(Text)
    button_text: Mapped[str | None] = mapped_column(String(64))
    button_url: Mapped[str | None] = mapped_column(String(300))
    photo: Mapped[bytes | None] = mapped_column(LargeBinary)
    photo_ids: Mapped[dict] = mapped_column(JSON, default=dict)  # Telegram file_id per bot, after the first upload
    bots: Mapped[list] = mapped_column(JSON)  # bot ids in priority order: each person gets the post once
    skip_premium: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="sending")  # sending | sent | deleting | deleted
    audience: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BroadcastMessage(Base):
    """One delivery: which bot sent the post to which user, and the message id needed to delete it."""
    __tablename__ = "broadcast_messages"
    broadcast_id: Mapped[str] = mapped_column(ForeignKey("broadcasts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bot_id: Mapped[str] = mapped_column(String(16))
    message_id: Mapped[int | None] = mapped_column(BigInteger)  # None: not delivered (user blocked the bot etc.)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    delete_failed: Mapped[bool] = mapped_column(Boolean, default=False)  # Telegram refused (older than 48 h, user removed it)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
