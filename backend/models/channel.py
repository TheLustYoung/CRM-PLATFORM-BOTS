from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, JSON, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now, uid


class ChannelPost(Base):
    """A post in the bots' public channel, written in the dashboard: published at once or at a set time,
    then editable, pinnable and removable from the channel."""
    __tablename__ = "channel_posts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    chat: Mapped[str] = mapped_column(String(64))  # @username or -100… id of the channel at publishing time
    bot_id: Mapped[str] = mapped_column(String(16))  # the bot that posts (an administrator of the channel)
    text: Mapped[str] = mapped_column(Text, default="")  # Telegram HTML
    media: Mapped[bytes | None] = mapped_column(LargeBinary)
    media_kind: Mapped[str | None] = mapped_column(String(8))  # photo | video
    media_name: Mapped[str | None] = mapped_column(String(128))
    buttons: Mapped[list] = mapped_column(JSON, default=list)  # [{"text": …, "url": …}], one per row
    status: Mapped[str] = mapped_column(String(12), default="scheduled", index=True)  # scheduled | sending | published | failed | deleted
    publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
