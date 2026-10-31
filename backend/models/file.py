import secrets
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now, uid


class UploadedFile(Base):
    """A file in private object storage: user uploads and downloader results."""
    __tablename__ = "uploaded_files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bot_id: Mapped[str | None] = mapped_column(ForeignKey("bots.id"))
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    object_key: Mapped[str] = mapped_column(String(256), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(BigInteger)
    mime: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    sha256: Mapped[str | None] = mapped_column(String(64))
    downloads: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class PublicLink(Base):
    __tablename__ = "public_file_links"
    token: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: secrets.token_urlsafe(24))
    file_id: Mapped[str] = mapped_column(ForeignKey("uploaded_files.id"), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
